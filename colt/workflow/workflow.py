import sys
from functools import wraps
#
from ..validator import Validator
from ._types import Type
from .language import generate_nodes
from ..commandline import get_config_from_commandline


class NodeGenerator:
    """Generator to create nodes from string"""

    def __init__(self, string):
        self.levels = None
        self.nodes, self.input_nodes = generate_nodes(string)
        #
        self.setup()

    def setup(self):
        self.set_levels()
        levels = {}
        for name, level in self.levels.items():
            if level not in levels:
                levels[level] = []
            if name not in self.input_nodes:
                levels[level].append(self.nodes[name])
        self.levels = levels

    def set_levels(self):
        #
        self.levels = {name: 0 
                       for node in self.nodes.values()
                       for name in node.input_nodes
                       if name not in self.nodes}
        self.input_nodes = [name for name in self.levels]
        #
        for name, node in self.nodes.items():
            self._set_level(name, node)

    def _set_level(self, name, node):
        if len(node.input_nodes) == 0:
            self.levels[name] = 0
            return
        try:
            self.levels[name] = max(self.levels[inp] if inp in self.levels
                                    else self._set_level(inp, self.nodes[inp])
                                    for inp in node.input_nodes) + 1
        except ValueError:
            self.levels[name] = 0


def with_self(func):
    def _wrapper(self, *args, **kwargs):
        return func(*args, **kwargs)
    return _wrapper


class Action:
    """Basic Action object to wrap functions and add types"""

    __slots__ = ('_func', 'inp_types', 'nargs', 'out_typ')

    def __init__(self, func, inp_types, out_typ, need_visitor=False):
        #
        if need_visitor is False:
            func = with_self(func)
        #
        self._func = func
        self.inp_types = tuple(Type(typ) for typ in inp_types)
        self.nargs = len(inp_types)
        self.out_typ = Type(out_typ)

    def __call__(self, visitor, inp):
        return self._func(visitor, *inp)


class ProgressBar:
    """Basic Class to handle progress"""

    def __init__(self, iterator, nele, width=80):
        self.iterator = iterator
        self.nele = nele
        self.width = width

    def progress_bar_string(self, i):
        icurrent = int(i/self.nele * self.width)
        bar = "="*icurrent + ' '*(self.width - icurrent)
        return f'Progress: [{bar}] {round(icurrent*100/self.width, 2)}%'

    def __iter__(self):
        try:
            for i, ele in enumerate(self.iterator):
                sys.stdout.write(f'\r{self.progress_bar_string(i)}')
                yield ele
            sys.stdout.write(f'\r{self.progress_bar_string(self.nele)}')
        finally:
            sys.stdout.write('\n')
            sys.stdout.flush()


class IteratorAction(Action):
    """Loop over an iterator"""

    __slots__ = ('iterator_id', 'use_progress_bar')

    def __init__(self, func, inp_types, out_typ, iterator_id=0, need_visitor=False, use_progress_bar=False):
        super().__init__(func, inp_types, out_typ, need_visitor=need_visitor)
        self.use_progress_bar = use_progress_bar
        self.iterator_id = iterator_id

    def __call__(self, visitor, inp):
        out = {}
        #
        if self.use_progress_bar:
            iterator = ProgressBar(inp[self.iterator_id], len(inp[self.iterator_id]))
        else:
            iterator = inp[self.iterator_id]
        #
        for ele in iterator:
            out[ele] = self._func(visitor, *inp[:self.iterator_id], ele, *inp[self.iterator_id+1:])
        return out


class WorkflowGenerator:
    """Basic class to generate worklows"""

    __slots__ = ('data', 'actions')

    def __init__(self):
        self.data = {}
        self.actions = {}

    def get(self, key):
        return self.data.get(key, None)

    def register_action(self, input_types=None, output_typ=None, iterator_id=None, need_self=False, progress_bar=False):
        if input_types == None:
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

    def get_action(self, name):
        action = self.actions.get(name)
        if action is None:
            raise Exception
        return action

    def create_workflow(self, name, nodes):
        return Workflow(name, nodes, self.actions)

    def generate_workflow_file(self, filename, name, workflow, module, engine):
        with open(filename, 'w') as f:
            f.write(generate_workflow(name, workflow, module, engine))


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


class Workflow(WorkflowGenerator):
    """Actual workflow object, implements run"""

    __slots__ = ('name', 'nodes', 'string', 'stop')

    def __init__(self, name, nodes, actions):
        super().__init__()
        self.stop = False
        self.name = name
        self.actions = actions
        self.nodes, self.string = self._setup(nodes, actions)

    def bind_data(self, name, value):
        self.data[name] = value

    def run(self):
        """visit all nodes"""
        stop = False
        self.data = get_config_from_commandline(self.string)
        for nodes in self.nodes.values():
            for node in nodes:
                try:
                    node.visit(self)
                except WorkflowExit:
                    stop = True
                    break
                except Exception as e:
                    print("Untracked exception occured, stop workflow")
                    print(e)
                    stop = True
                    break
            if stop is True:
                break

    def error(self, msg):
        raise WorkflowExit

    def debug(self, msg):
        print("Debug: ", msg)

    def info(self, msg):
        print("Workflow: ", msg)

    def add_subtypes(self, parent, subtypes):
        Type.add_subtypes(parent, subtypes)

    def _setup(self, nodes, actions):
        gen = NodeGenerator(nodes)
        types = self._check_types(gen, actions)
        inp = self._setup_input(gen, types)
        return gen.levels, inp

    def _setup_input(self, gen, types):
        """Should be changed to type check etc."""
        if any(types[inp].typ not in Validator.parsers for inp in gen.input_nodes):
            raise Exception("type not known, cannt create input")
        return "\n".join(f"{inp} = :: {types[inp].typ}" for inp in gen.input_nodes)

    def _check_types(self, gen, actions):

        types = {}

        for nodes in gen.levels.values():
            # loop over nodes in level
            for node in nodes:
                # select action
                action = actions[node.action]
                # loop over input nodes
                if len(action.inp_types) != len(node.input_nodes):
                    print(action.inp_types, node.input_nodes)
                    raise Exception(f"arguments not same!")
                #
                for i, (inp, _) in enumerate(node.input_nodes.items()):
                    # ignore
                    if inp is None:
                        continue
                    # set the typ
                    typ = action.inp_types[i]
                    # do sanity_check
                    if inp not in gen.input_nodes:
                        # get inp_action
                        inp_action = actions[gen.nodes[inp].action]
                        # sanity check
                        if not inp_action.out_typ.is_type(typ):
                            raise Exception(f"Nodes {inp_action.out_typ} not compatible with {typ}")
                    types[inp] = typ
        return types


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
