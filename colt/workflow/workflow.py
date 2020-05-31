import sys
#
from language import generate_nodes
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
        self.levels = {name: 0 for name in self.input_nodes}
        #
        for name, node in self.nodes.items():
            self._set_level(name, node)

    def _set_level(self, name, node):
        if len(node.input_nodes) == 0:
            self.levels[name] = 0
            return
        self.levels[name] = max(self.levels[inp] if inp in self.levels
                                else self._set_level(inp, self.nodes[inp])
                                for inp in node.input_nodes) + 1


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
        self.inp_types = inp_types
        self.nargs = len(inp_types)
        self.out_typ = out_typ

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

    def __init__(self, func, inp_types, out_typ, iterator_id=0, use_progress_bar=False):
        super().__init__(func, inp_types, out_typ)
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

    def register_action(self, input_types=None, output_typ=None, iterator_id=None, need_handle=False, progress_bar=False):
        if input_types == None:
            input_types = tuple()

        def _wrapper(func):
            name = func.__name__
            if iterator_id is None:
                self.actions[name] = Action(func, input_types, output_typ)
            else:
                self.actions[name] = IteratorAction(func, input_types, output_typ,
                                                    iterator_id=iterator_id,
                                                    use_progress_bar=progress_bar)
            return self.actions[name]
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


class Workflow(WorkflowGenerator):
    """Actual workflow object, implements run"""

    __slots__ = ('name', 'nodes', 'string')

    def __init__(self, name, nodes, actions):
        super().__init__()
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
                #try:
                node.visit(self)
                #except:
                #    stop = True
                #    break
            if stop is True:
                break

    def _setup(self, nodes, actions):
        gen = NodeGenerator(nodes)
        types = self._check_types(gen, actions)
        inp = self._setup_input(gen, types)
        return gen.levels, inp

    def _setup_input(self, gen, types):
        """Should be changed to type check etc."""
        return "\n".join(f"{inp} = :: {types[inp]}" for inp in gen.input_nodes)

    def _check_types(self, gen, actions):

        types = {}

        for nodes in gen.levels.values():
            # loop over nodes in level
            print(nodes)
            for node in nodes:
                # select action
                action = actions[node.action]
                # loop over input nodes
                if len(action.inp_types) != len(node.input_nodes):
                    print(action.inp_types, node.input_nodes)
                    raise Exception("arguments not same!")
                #
                for i, inp in enumerate(node.input_nodes):
                    # set the typ
                    typ = action.inp_types[i]
                    # do sanity_check
                    if inp not in gen.input_nodes:
                        # get inp_action
                        inp_action = actions[gen.nodes[inp].action]
                        # sanity check
                        if inp_action.out_typ != typ:
                            raise Exception("Nodes not compatible")
                    types[inp] = typ
        return types
