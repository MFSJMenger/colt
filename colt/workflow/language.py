from collections import UserList
import re
#
from ._types import Type


class List(UserList):

    def __init__(self):
        super().__init__()


class Variable:

    def __init__(self, value, typ, comment=None):
        self.value = value
        self.typ = typ
        self.comment = comment

    def __eq__(self, other):
        return self.typ == other

    def __str__(self):
        return f"Variable({self.typ}, '{self.value}, {self.comment}')"

    def __repr__(self):
        return f"Variable({self.typ}, '{self.value}, {self.comment}')"


class FunctionCall:

    def __init__(self, func_name, arguments, action, comment=None):
        self.name = func_name
        self.args = arguments
        self.variables = self._get_variables(arguments)
        self.action = action
        self.comment = comment

    def _get_variables(self, arguments):
        return {argument.value: i for i, argument in enumerate(arguments)
                if argument.typ == 'variable'}

    def input(self, data):           
        return tuple(data[argument.value] if argument.typ == 'variable' else argument.value
                     for argument in self.args)

    @property
    def typ(self):
        return self.action.out_typ

    @staticmethod
    def _to_input_nodes(arg, typ, input_nodes):
        if arg.value in input_nodes:
            input_nodes[arg.value].typ = typ
        else:
            input_nodes[arg.value] = Variable(None, typ)

    def check_types(self, types, input_nodes):
        for i, arg in enumerate(self.args):
            if arg.typ == 'variable':
                try:
                    self._check(types[arg.value], self.action.inp_types[i])
                except KeyError:
                    types[arg.value] = self.action.inp_types[i]
                    self._to_input_nodes(arg, types[arg.value], input_nodes)
            else:
                if arg.typ == 'not_assigned':
                    types[arg.value] = self.action.inp_types[i]
                    self._to_input_nodes(arg, types[arg.value], input_nodes)
                else:
                    self._check(Type(arg.typ), self.action.inp_types[i])

    def _check(self, typ1, typ2):
        if not typ1.is_type(typ2):
            raise Exception(f"{typ1} not compatible with {typ2}")

    def call(self, workflow, data):
        if self.comment is not None:
            print(self.comment)
        inp = self.input(data)
        return self.action(workflow, inp)

    def __str__(self):
        return f'{self.name}{self.args}'

    def __repr__(self):
        return f'{self.name}{self.args}'


class Assignment:

    def __init__(self, variable_name, value, comment=None):
        self.name = variable_name
        self.value = value
        self.comment = comment
        if isinstance(self.value, FunctionCall):
            if self.comment is not None:
                self.value.comment = self.comment

    def call(self, workflow, data):
        if isinstance(self.value, FunctionCall):
            return self.value.call(workflow, data)
        if self.value.typ == 'not_assigned':
            return data[self.name]
        return self.value.value

    def check_types(self, types, input_nodes):
        if isinstance(self.value, FunctionCall):
            self.value.check_types(types, input_nodes)
            types[self.name] = self.value.typ
        else:
            if self.value.typ == 'not_assigned':
                input_nodes[self.name] = Variable(None, None, self.comment)
            else:
                types[self.name] = Type(self.value.typ)
                input_nodes[self.name] = Variable(self.value.value, Type(self.value.typ), self.comment)

    def __str__(self):
        return f"{self.name} = {self.value}"

    def __repr__(self):
        return f"{self.name} = {self.value}"


def match(string, regex):
    string = string.strip()
    result = regex.match(string)
    if result is not None:
        end = result.end()
        return result, string[end:]
    return None, string


class Parser:
    """Basic Parser"""

    re_int = re.compile(r'(?P<number>[-+]?\d+)')
    re_float = re.compile(r'(?P<number>[-+]?\d+\.\d*)')
    re_string_double_quotes = re.compile(r'\"(?P<string>.*)\"')
    re_string_single_quotes = re.compile(r'\'(?P<string>.*)\'')
    re_variable = re.compile(r"(?P<string>\w+)")

    re_lpar = re.compile(r'\(')
    re_rpar = re.compile(r'\)')

    re_lpar_square = re.compile(r'\[')
    re_rpar_square = re.compile(r'\]')

    re_equal = re.compile(r'=')
    re_comma = re.compile(r',')
    re_plus = re.compile(r'\+')
    re_minus = re.compile(r'\-')

    def __init__(self, actions):
        self.actions = actions

    def match_line(self, string):
        r"assignment | function_call :: comment"
        string, _, comment = string.partition('::')
        if comment == '':
            comment = None
        res, cutted_string = self.assignment(string, comment)
        if res is not None:
            return res, cutted_string
        return self.function_call(string, comment)

    def assignment(self, string, comment=None):
        r"variable = expression"
        variable, cutted_string = self.variable(string)
        if variable is None:
            return None, string
        res, cutted_string = self.equal(cutted_string)
        if res is None:
            return None, string
        if cutted_string.strip() == '':
            return Assignment(variable.value, Variable('', 'not_assigned'), comment), cutted_string
        res, cutted_string = self.expression(cutted_string)
        if res is None:
            return None, string
        return Assignment(variable.value, res, comment), cutted_string

    def equal(self, string):
        res, cutted_string = match(string, self.re_equal)
        if res is not None:
            return True, cutted_string
        return None, string

    def expression(self, string):
        r"func_call | value"
        res, cutted_string = self.value(string)
        if res is not None:
            return res, cutted_string
        return self.function_call(string)

    def argument(self, string):
        r"value | literal"
        res, string_cutted = self.value(string)
        if res is not None:
            return res, string_cutted
        return self.literal(string)

    def value(self, string):
        r"list | number | string | bool | None "
        res, string_cutted = self.list(string)
        if res is not None:
            return res, string_cutted
        res, string_cutted = self.number(string)
        if res is not None:
            return res, string_cutted
        res, string_cutted = self.string(string)
        if res is not None:
            return res, string_cutted
        return self.bool_or_none(string)

    def function_call(self, string, comment=None):
        r"variable lpar arguments rpar"
        func_name, string_cutted = self.variable(string)
        if func_name is None or self.is_reserved(func_name):
            return None, string
        else:
            func_name = func_name.value
        res, string_cutted = self.lpar(string_cutted)
        if res is None:
            return None, string
        arguments, string_cutted = self._function_arguments(string_cutted, List())
        if arguments is None:
            return None, string
        if func_name not in self.actions:
            return None, string
        return FunctionCall(func_name, arguments, self.actions[func_name], comment), string_cutted

    def is_reserved(self, variable):
        "check if variable is equal to reserved keyword"
        return variable.value in ('True', 'False', 'None')

    def list(self, string):
        r" lpar_square list_values rpar_square "
        res, string_cutted = self.lpar_square(string)
        if res is None:
            return None, string
        res, string_cutted = self._list_values(string_cutted, List())
        if res is None:
            return None, string
        return Variable(res, 'list'), string_cutted

    def _function_arguments(self, string, arguments):
        r"arguments [,] ...)"
        string = string.strip()
        if string.startswith(')'):
            return arguments, string[1:]
        #
        res, cutted_string = self.argument(string)
        if res is None:
            return None, string
        arguments.append(res)
        #
        cutted_string = cutted_string.strip()
        #
        if cutted_string.startswith(')'):
            return self._function_arguments(cutted_string, arguments)
        #
        res, cutted_string = self.comma(cutted_string)
        #
        if res is None:
            return None, string
        #
        return self._function_arguments(cutted_string, arguments)

    def _list_values(self, string, liste):
        r"value [,] ... " 
        string = string.strip()
        if string.startswith(']'):
            return liste, string[1:]
        res, cutted_string = self.value(string)
        if res is None:
            return None, string
        liste.append(res.value)
        cutted_string = cutted_string.strip()
        if cutted_string.startswith(']'):
            return self._list_values(cutted_string, liste)
        res, cutted_string = self.comma(cutted_string)
        if res is None:
            return None, string
        return self._list_values(cutted_string, liste)

    def comma(self, string):
        res, string_cutted = match(string, self.re_comma)
        if res is not None:
            return True, string_cutted
        return None, string

    def lpar(self, string):
        r" lpar "
        res, cutted_string = match(string, self.re_lpar)
        if res is not None:
            return True, cutted_string
        return None, string

    def lpar_square(self, string):
        r" lpar "
        res, string_cutted = match(string, self.re_lpar_square)
        if res is not None:
            return True, string_cutted
        return None, string

    def bool_or_none(self, string):
        r"bool | None"
        res, string_cutted = self.literal(string)
        if res is None or res.typ == 'variable':
            return None, string
        return res, string_cutted

    def rpar(self, string):
        r" rpar "
        res, string_cutted = match(string, self.re_rpar)
        if res is not None:
            return True, string_cutted
        return None, string

    def variable(self, string):
        r"variable"
        res, string_cutted = match(string, self.re_variable)
        if res is not None:
            return Variable(res.group('string'), 'variable'), string_cutted
        return None, string

    def literal(self, string):
        r"bool | None | variable"
        res, string_cutted = self.variable(string)
        if res is None:
            return None, string
        if res.value in ('True', 'False'):
            return Variable(bool(res.value), 'bool'), string_cutted
        if res.value == 'None':
            return Variable(None, 'None'), string_cutted
        return res, string_cutted

    def string(self, string):
        r"double_quoted | single_quoted"
        res, string_cutted = match(string, self.re_string_double_quotes)
        if res is not None:
            return Variable(res.group('string'), 'str'), string_cutted
        res, string_cutted = match(string, self.re_string_single_quotes)
        if res is not None:
            return Variable(res.group('string'), 'str'), string_cutted
        return None, string

    def number(self, string):
        r"float | integer"
        res, string_cutted = self.float(string)
        if res is not None:
            return res, string_cutted
        #
        res, string_cutted = self.integer(string)
        if res is not None:
            return res, string_cutted
        return None, string

    def integer(self, string):
        r"integer"
        res, string_cutted = match(string, self.re_int)
        if res is not None:
            return Variable(int(res.group()), 'int'), string_cutted
        return None, string

    def float(self, string):
        r"float"
        res, string_cutted = match(string, self.re_float)
        if res is not None:
            return Variable(float(res.group()), 'float'), string_cutted
        return None, string
