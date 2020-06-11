import re
import ast
import random
import string


re_assignment = re.compile(r'^(?P<variable>\w+)\s*=\s*(?P<func_call>.*)$')
re_func_call = re.compile(r'^(?P<func_name>\w*)\((?P<content>.*)\)$')

re_integer = re.compile(r'^(?P<number>[-+]?\d+)$')
re_float_number= re.compile(r'^(?P<number>[-+]?\d+\.\d+)$')
re_string_double_quotes = re.compile(r'^(?P<string>[\"].*[\"])$')
re_string_single_quotes = re.compile(r'^(?P<string>[\'].*[\'])$')
re_variable = re.compile(r"^(?P<string>\w+)$")


class ParseError(Exception):

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg

    def __repr__(self):
        return self.msg


def int_parser(value):
    match = re_integer.match(value)
    if match:
        return Variable(int(match.group('number')), 'int')
    return None


def float_parser(value):
    match = re_float_number.match(value)
    if match:
        return Variable(float(match.group('number')), 'float')
    return None


def string_parser(value):
    for matcher in (re_string_double_quotes, re_string_single_quotes):
        match = matcher.match(value)
        if match:
            return Variable(match.group('string')[1:-1], 'string')
    return None


def variable_parser(value):
    match = re_variable.match(value)
    if match:
        variable = match.group('string')
        # special keywords
        if variable in ('True', 'False'):
            return Variable(bool(variable), 'bool')
        # 
        if variable == 'None':
            return Variable(None, 'None')
        #
        return Variable(variable, 'variable')
    return None


class Variable:

    def __init__(self, value, typ):
        self.value = value
        self.typ = typ

    def __eq__(self, other):
        return self.typ == other

    def __str__(self):
        return f"Variable({self.typ}, '{self.value}')"

    def __repr__(self):
        return f"Variable({self.typ}, '{self.value}')"


def get_variable(element):
    element = element.strip()
    for parser in (int_parser, float_parser, string_parser, variable_parser):
        out = parser(element)
        if out is not None:
            return out
    try:
        out = ast.literal_eval(element)
        if out is not None:
            return Variable(out, 'list')
    except:
        pass
    raise ParseError(f"cannot parse: {element}")


def split_content(in_string, split=','):
    out = []
    string = ''
    inside = 0
    for c in in_string:
        if c == '[':
            inside += 1
        elif c == ']':
            inside -= 1
        elif c == split:
            if inside == 0:
                out.append(string.strip())
                string = ''
                continue
        string += c
    #
    out.append(string.strip())
    if inside != 0:
        raise Exception()
    return out


def get_variables(content):
    if content.strip() == '':
        return Variables([])
    return Variables([get_variable(element) for element in split_content(content)])


class Variables:

    def __init__(self, variables):
        self.vars = variables

    def __len__(self):
        return len(self.vars)

    def __iter__(self):
        for variable in self.vars:
            if variable == 'variable':
                yield variable.value

    def items(self):
        for variable in self.vars:
            if variable == 'variable':
                yield variable.value, None
            else:
                yield None, variable.value



def get_func_name(stringLength=10):
    return ('func_' + ''.join(random.choice(string.ascii_lowercase) for i in range(stringLength)) 
            + ''.join(str(random.randint(0, 100) for _ in range(5))))


def function_parser(value, name=None):
    match = re_func_call.match(value)
    if match is None:
        return match
    variables = get_variables(match.group('content'))
    if name is None:
        name = get_func_name()
    return Node(match.group('func_name'), name, variables)


def parse_assignment_expr(name, value):
    if value.strip() == '':
        return InputNode(name, None)
    for parser in (int_parser, float_parser, string_parser):
        match = parser(value)
        if match is not None:
            return InputNode(name, match.value)
    return function_parser(value, name=name)


def assignement_parser(value):
    match = re_assignment.match(value)
    if match is None:
        return None
    return parse_assignment_expr(match.group('variable'), match.group('func_call'))


class InputNode:
    
    __slots__ = ('id', 'default', 'typ')

    def __init__(self, id, default, typ='not_assigned'):
        self.id = id
        self.default = default
        self.typ = typ


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
        output = visit(visitor, inp)
        if output is not None:
            self._register_output(visitor, output)

    def generate_input(self, visitor):
        return tuple(visitor.get(name) if name is not None else value for name, value in self.input_nodes.items())

    def _register_output(self, visitor, output):
        visitor.bind_data(self.id, output)


def fileitr(string, comment='#'):
    for i, line in enumerate(string.splitlines()):
        line = line.partition(comment)[0].strip()
        if line != '':
            yield i, line


def parse_line(line, number):
    for parse in (assignement_parser, function_parser):
        try:
            out = parse(line)
        except ParseError as e:
            print(e)
            break
        if out is not None:
            return out
    raise ParseError(f"Could not parse line {number}\n{line}")


def generate_nodes(string): 
    nodes = {}
    input_nodes = []
    for i, line in fileitr(string):
        node = parse_line(line, i)
        if isinstance(node, InputNode):
            input_nodes.append(node.id)
        else:
            nodes[node.id] = node
    return nodes, input_nodes
