import sys
#
from .generator import GeneratorBase
from .commandline import get_config_from_commandline


class Node:
    """Basic Node in the workflow"""

    __slots__ = ('action', 'input_nodes', 'id')

    def __init__(self, action, id, input_nodes):
        self.action = action           # what kind of action to perform
        self.input_nodes = input_nodes # names of the input node
        self.id = id                   # id of the node

    def visit(self, visitor):
        inp = self.generate_input(visitor)
        visit = visitor.get_action(self.action)
        output = visit(self, inp)
        if output is not None:
            self._register_output(visitor, output)

    def generate_input(self, visitor):
        return tuple(visitor.get(node) for node in self.input_nodes)

    def _register_output(self, visitor, output):
        visitor.bind_data(self.id, output)


class NodeGenerator(GeneratorBase):
    """Generator to create nodes from string"""

    comment_char = "###"
    default = '__QUESTIONS__'

    leafnode_type = Node

    def __init__(self, string):
        super().__init__(string)
        self.levels = None
        self.input_nodes = self.setup()

    def setup(self):
        input_nodes = self.get_input_nodes()
        self.set_levels(input_nodes)
        levels = {}
        for name, level in self.levels.items():
            if level not in levels:
                levels[level] = []
            if name not in input_nodes:
                levels[level].append(self.tree[name])
        self.levels = levels
        return input_nodes

    def set_levels(self, input_nodes):
        #
        self.levels = {name: 0 for name in input_nodes}
        #
        for name, node in self.tree.items():
            self._set_level(name, node)

    def _set_level(self, name, node):
        if len(node.input_nodes) == 0:
            self.levels[name] = 0
            return
        self.levels[name] = max(self.levels[inp] if inp in self.levels
                                else self._set_level(inp, self.tree[inp])
                                for inp in node.input_nodes) + 1

    def get_input_nodes(self):
        return tuple(inp for node in self.tree.values() for inp in node.input_nodes
                     if inp not in self.tree)

    def leaf_from_string(self, name, value, parent=None):
        """Create a leaf from an entry in the config file

        Args:
            name (str):
                name of the entry

            value (str):
                value of the entry in the config

        Kwargs:
            parent (str):
                identifier of the parent node

        Returns:
            A leaf node

        Raises:
            ValueError:
                If the value cannot be parsed
        """
        action, _, input_nodes = value.partition(self.seperator)
        if input_nodes.strip() == '':
            input_nodes = tuple()
        else:
            input_nodes = tuple(val.strip() for val in input_nodes.split(','))
        return Node(action.strip(), name, input_nodes)

    def new_node(self):
        """Create a new node of the tree"""
        raise Exception("no new nodes available")


class Action:
    """Basic Action object to wrap functions and add types"""

    __slots__ = ('_func', 'inp_types', 'nargs', 'out_typ')

    def __init__(self, func, inp_types, out_typ):
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

    __slots__ = ('iterator_id')

    def __init__(self, func, inp_types, out_typ, iterator_id=0):
        super().__init__(func, inp_types, out_typ)
        self.iterator_id = iterator_id

    def __call__(self, visitor, inp):
        out = {}
        for ele in ProgressBar(inp[self.iterator_id], len(inp[self.iterator_id])):
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

    def register_action(self, inp_types, out_typ, iterator_id=None):
        def _wrapper(func):
            name = func.__name__
            if iterator_id is None:
                self.actions[name] = Action(func, inp_types, out_typ)
            else:
                self.actions[name] = IteratorAction(func, inp_types, out_typ, iterator_id=iterator_id)
            return self.actions[name]
        return _wrapper

    def get_action(self, name):
        action = self.actions.get(name)
        if action is None:
            raise Exception
        return action

    def create_workflow(self, name, nodes):
        return Workflow(name, nodes, self.actions)


class Workflow(EventVisitor):
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
                try:
                    node.visit(self)
                except:
                    stop = True
                    break
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
                        inp_action = actions[gen.tree[inp].action]
                        # sanity check
                        if inp_action.out_typ != typ:
                            raise Exception("Nodes not compatible")
                    types[inp] = typ
        return types
