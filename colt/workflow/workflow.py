from ..validator import Validator
from ..commandline import get_config_from_commandline
#
from .language import Assignment, Parser, Type
from .actions import Action, IteratorAction


class WorkflowGenerator:

    def __init__(self):
        self.actions = {}

    def register_action(self, input_types=None, output_typ=None, iterator_id=None,
                        need_self=False, progress_bar=False):
        if input_types is None:
            input_types = tuple()

        def _wrapper(func):
            name = func.__name__
            if iterator_id is None:
                self.actions[name] = Action(func, input_types, output_typ, need_visitor=need_self)
            else:
                self.actions[name] = IteratorAction(func, input_types, output_typ,
                                                    iterator_id=iterator_id,
                                                    need_visitor=need_self,
                                                    use_progress_bar=progress_bar)
            return func
        return _wrapper

    def create_workflow(self, name, nodes):
        return Workflow(name, nodes, self.actions)

    def generate_workflow_file(self, filename, name, workflow, module, engine):
        with open(filename, 'w') as f:
            f.write(generate_workflow(name, workflow, module, engine))

    def add_subtypes(self, parent, subtypes):
        Type.add_subtypes(parent, subtypes)


def generate_workflow(name, workflow, module, engine):
    workflow = f'"""{workflow}"""'
    return f"""
from {module} import {engine}

workflow = {engine}.create_workflow('{name}', {workflow})

if __name__ == '__main__':
    workflow.run()
"""


class WorkflowExit(Exception):
    pass


class Workflow:

    def __init__(self, name, string, actions):
        self.name = name
        self.parser = Parser(actions)
        self.nodes = self._parse_string(string)
        self.input_nodes = self._check_types()

    def _check_types(self):
        current_types = {}
        input_nodes = {}
        for node in self.nodes:
            node.check_types(current_types, input_nodes)
        for var, typ in input_nodes.items():
            if typ.typ.typ not in Validator.parsers:
                raise Exception(f"cannot get type '{typ}' of variable {var} from commandline")
        return input_nodes

    def _input_questions(self, data):
        txt = ""
        for name, value in self.input_nodes.items():
            if name in data:
                continue
            if value.value is None:
                _value = ''
            else:
                _value = str(value.value)
            if value.comment is not None:
                txt += f"#{value.comment}\n"
            txt += f"{name} = {_value} :: {value.typ.typ}\n"
        return txt

    def _parse_string(self, string):
        out = []
        for inum, line in self.string_itr(string):
            res, _ = self.parser.match_line(line)
            if res is None:
                raise Exception(f"Cannot parse line {inum}:\n{line}")
            out.append(res)
        return out

    def error(self, msg):
        raise WorkflowExit

    def debug(self, msg):
        print("Debug: ", msg)

    def info(self, msg):
        print("Workflow: ", msg)

    @staticmethod
    def string_itr(string, comment='#'):
        for i, line in enumerate(string.splitlines()):
            line = line.partition(comment)[0].strip()
            if line != '':
                yield i, line

    def run(self, data=None, description=None):
        if data is None:
            data = {}
        questions = self._input_questions(data)
        if questions != '':
            data.update(get_config_from_commandline(questions, description=description))
        for node in self.nodes:
            try:
                if isinstance(node, Assignment):
                    data[node.name] = node.call(self, data)
                else:
                    node.call(self, data)
            except WorkflowExit:
                break
        return data


# Primitives
Type('str')
Type('bool')
Type('int')
Type('float')
# Numbers
Type('number')
Type.add_subtypes('number', ['int', 'float'])
# Lists
Type('list')
Type('ilist', alias=['ilist_np'])
Type('flist', alias=['flist_np'])
#
Type.add_subtypes('list', ['ilist', 'flist'])
# Files
Type('file')
Type('existing_file')
Type('non_existing_file')
Type.add_subtypes('file', ['existing_file', 'non_existing_file'])
# Folder
Type('folder')
Type('existing_folder')
Type('non_existing_folder')
Type.add_subtypes('folder', ['existing_folder', 'non_existing_folder'])
