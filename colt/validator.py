"""Basic Validator to convert user input into python objects
while automatically checking the type and doing error handling"""
import os
import ast
from collections.abc import KeysView
from collections import namedtuple
#
import numpy as np


__all__ = ["NOT_DEFINED", "Validator", "ValidatorErrorNotInChoices"]


ValidatorType = namedtuple("ValidatorType", ("cls", "cases"))
ValidatorParser = namedtuple("ValidatorParser", ("cls", "func"))
ListInfo = namedtuple('ListInfo', ('is_list', 'nele'))


class NoChoice:
    """Empty object that indicates that no choice are used"""

    __slots__ = ()

    @staticmethod
    def is_subset(rhs):
        """Is subset of itself"""
        if isinstance(rhs, NoChoice):
            return True
        return False

    def __str__(self):
        return ""

    def __repr__(self):
        return ""

    @staticmethod
    def validate(value):
        """Always True"""
        return True


NO_CHOICE = NoChoice()


class Choices:
    """Store possible choices"""

    __slots__ = ('choices',)

    def __init__(self, choices):
        self.choices = choices

    def as_str(self):
        """return choices as a string"""
        txt = ", ".join(str(choice) for choice in self.choices)
        return f"Choices({txt})"

    def __len__(self):
        return len(self.choices)

    def __str__(self):
        return self.as_str()

    def __repr__(self):
        return self.as_str()

    def __getitem__(self, idx):
        return self.choices[idx]

    def __iter__(self):
        return iter(self.choices)

    def as_list(self):
        """return choices as a python list"""
        return list(self.choices)

    def validate(self, value):
        """check if value in choices"""
        return value in self.choices

    def is_subset(self, rhs):
        """check if `rhs` is a subset of `self`"""
        if rhs in (None, NO_CHOICE):
            return True
        if not isinstance(rhs, Choices):
            return False
        return all(choice in rhs.choices for choice in self.choices)


class RangeExpression:
    """Simple class to handle mathematical ranges"""

    __slots__ = ('lower', 'upper', 'expr')

    def __init__(self, expr):
        self.expr = expr
        self.lower, self.upper = self._parse(expr)

    def validate(self, value):
        """check that value fullfills the expression"""
        if self.lower is not None:
            if value < self.lower:
                return False
        if self.upper is not None:
            if value > self.upper:
                return False
        return True

    def __len__(self):
        return 0

    def __str__(self):
        return self.as_str()

    def __repr__(self):
        return self.as_str()

    def as_str(self):
        """Return str of range expression"""
        return f"Range({self.expr})"

    def is_subset(self, rhs):
        """Check if `rhs` is a subset of `self`"""
        if rhs is None:
            return True
        if not isinstance(rhs, RangeExpression):
            return False

        if self._smaller(self.lower, rhs.lower):
            return False
        if self._larger(self.upper, rhs.upper):
            return False
        return True

    def _parse(self, expr):
        if '>' in expr:
            upper, lower = (ele.strip() for ele in expr.split('>'))
        elif '<' in expr:
            lower, upper = (ele.strip() for ele in expr.split('<'))
        else:
            raise ValueError("Could not parse Expr")
        upper = self._parse_value(upper)
        lower = self._parse_value(lower)
        if self._larger(lower, upper):
            raise ValueError("Range is None")
        return lower, upper

    @staticmethod
    def _larger(value1, value2):
        """value1 > value2"""
        if value1 is None:
            return True
        if value2 is None:
            return False
        return value1 > value2

    @staticmethod
    def _smaller(value1, value2):
        """value1 < value2"""
        if value1 is None:
            return False
        if value2 is None:
            return True
        return value1 < value2

    @staticmethod
    def _parse_value(value):
        """convert value to float"""
        if value == "":
            return None
        return float(value)


def abspath(answer):
    """abspath including expanduser"""
    return os.path.abspath(os.path.expanduser(answer))


def file_exists(path):
    """check if file exists"""
    abs_path = abspath(path)
    if not os.path.isfile(abs_path):
        raise ValueError(f"File does not exist '{path}'")
    return abs_path


def folder_exists(path):
    """check if folder exists"""
    abs_path = abspath(path)
    if not os.path.isdir(abs_path):
        raise ValueError(f"Folder does not exist '{path}'")
    return abs_path


def non_existing_path(path):
    """check that there is nothing at the given path"""
    abs_path = abspath(path)
    if os.path.exists(abs_path):
        raise ValueError(f"File/Folder does already exist '{path}'")
    return abs_path


def bool_parser(answer):
    """convert string into a bool"""

    _positive = ('y', 'yes', 'True', 'true')
    _negative = ('n', 'no', 'False', 'false')
    #
    if answer in _positive:
        return True
    if answer in _negative:
        return False

    raise ValueError("Answer can only be [%s] or [%s]"
                     % (", ".join(_positive), ", ".join(_negative)))


def list_parser(answer):
    """convert string to list of strings"""
    split_char, answer = _prepare_list_parsing(answer)
    return [ele.strip() for ele in answer.split(split_char) if ele.strip() != ""]


def flist_parser(answer):
    """convert string to list of floats"""
    return [float(ele) for ele in list_parser(answer)]


def flist_np_parser(answer):
    """Transfers a string into a numpy array of floats"""
    return np.array(flist_parser(answer))


def ilist_parser(answer):
    """convert string to list of integers"""
    if '~' not in answer:
        return [int(ele) for ele in list_parser(answer)]
    #
    split_char, answer = _prepare_list_parsing(answer)
    numbers = (parse_integer_numbers(number) for number in answer.split(split_char))
    return sum(numbers, [])


def ilist_np_parser(answer):
    """convert string to numpy array of integers"""
    return np.array(ilist_parser(answer))


def get_upper_bounds(start, stop):
    """get upper bound for range"""
    start, stop = int(start), int(stop)
    if start > stop:
        start, stop = stop, start
    return start, stop+1


def parse_integer_numbers(string):
    """convert integer numbers into ilist liste"""
    # check if tilde in line
    if '~' in string:
        start, _, stop = string.partition('~')
        start, stop = get_upper_bounds(start, stop)
        return list(range(start, stop))
    if string.strip() == "":
        return []
    return [int(string)]


def _prepare_list_parsing(answer):
    """setup string for list parsing"""
    split_char = choose_split_char(answer)
    answer = remove_brackets_and_quotes(answer)
    return split_char, answer


def choose_split_char(answer):
    """get a suitable split character"""
    if ',' in answer:
        split_char = ","
    else:
        split_char = None
    return split_char


def remove_brackets_and_quotes(string):
    """remove brackets from string"""
    return string.replace("[", "").replace("]", "").replace("'", "").replace('"', "")


def _as_python_object(string, obj, name):
    """convert the string to an python object using ast.literal_eval"""
    result = ast.literal_eval(string)
    if not isinstance(result, obj):
        raise ValueError(f"Value is not a python {name}!")
    return result


def as_python_tuple(string):
    """try to convert string to python tuple"""
    return _as_python_object(string, tuple, "tuple")


def as_python_list(string):
    """try to convert string to python list"""
    return _as_python_object(string, list, "list")


def as_python_dict(string):
    """try to convert string to python list"""
    return _as_python_object(string, dict, "dict")


def as_python_numpy_array(string):
    """try to convert string to python list"""
    return np.array(as_python_list(string))


# empty class
class NotDefined:
    """Empty class to use something analogue to None"""
    __slots__ = ()

    def __repr__(self):
        return "<NOT_DEFINED>"

    def __str__(self):
        return "<NOT_DEFINED>"


NOT_DEFINED = NotDefined()


class ValidatorErrorNotInChoices(Exception):
    """Exception in case value is not in choices"""


class ValidatorErrorNotChoicesSubset(Exception):
    """Exception in case the new choices are not an subset of the old ones"""


class BaseValidator:
    """Base class to validator"""

    __slots__ = ('_choices', '_default', '_value', '_string', '_parse')
    # overwrite this method

    def __init__(self, parse_function, default=NOT_DEFINED, choices=None):
        # has to be at the top
        self._parse = parse_function
        self._string = NOT_DEFINED
        self._choices = self._set_choices(choices)
        self._value = self._set_value(default)

    @property
    def default(self):
        """means value should not be set, is for documentation and help"""
        return self._value

    @property
    def choices(self):
        """Return choices"""
        if self._choices is NO_CHOICE:
            return None
        return self._choices

    @choices.setter
    def choices(self, choices):
        """  """
        # will raise an value error if choices wrong!
        choices = self._set_choices(choices)
        # check that the new choices are a subset of the old ones
        if not choices.is_subset(self._choices):
            raise ValidatorErrorNotChoicesSubset(("cannot update choices,",
                                                  " needs to be subset of the original ones"))
        # overwrite existing ones
        self._choices = choices
        # validate choice, if existing default is not in choices, reset
        if not self._choices.validate(self._value):
            self._value = NOT_DEFINED

    def validate(self, value):
        """Parse a string and return its value,
        raises ValueError on failure

        Parameters
        ----------
        value: str
            user input to be validated

        Returns
        -------
        Parsed Value

        Raises
        ------
        ValueError
            if value does not fullfill condition
        """
        value = self._parse(str(value))
        if not self._choices.validate(value):
            raise ValidatorErrorNotInChoices(f"Answer is not in {self._choices}")
        return value

    def answer_as_string(self):
        """return the answer as a string"""
        if self._string is NOT_DEFINED:
            return ''
        return self._string

    def get(self):
        """Return self._value if its set or not!"""
        return self._value

    def set(self, value):
        """set the value"""
        self._value = self._get_value(value)

    def set_default(self, value):
        self.set(value)

    def _set_value(self, value):
        if value is not NOT_DEFINED:
            value = self._get_value(value)
        return value

    def _set_choices(self, choices):
        """set choices"""
        if choices is None:
            return NO_CHOICE
        return self.set_choices(choices)

    def set_choices(self, choices):
        """set choices"""
        if isinstance(choices, KeysView):
            return Choices([self._parse(choice) for choice in choices])
        try:
            choices = [self._parse(choice) for choice in list_parser(choices)]
        except ValueError:
            choices = None
        if choices is None:
            raise ValueError(f"Choices '{choices}' cannot be parsed")
        return Choices(choices)

    def _get_value(self, string):
        """Sets the value"""
        value = self.validate(string)
        if not self._choices.validate(value):
            raise ValidatorErrorNotInChoices("Answer is not in choices")
        # should already be stripped
        self._string = string
        return value


class RangeValidator(BaseValidator):
    """Validator that allowes both `Choices` and RangeExpression"""

    def set_choices(self, choices):
        """set choices"""
        if isinstance(choices, KeysView):
            return Choices([self._parse(choice) for choice in choices])
        #
        try:
            return RangeExpression(choices)
        except ValueError:
            pass
        #
        try:
            choices = [self._parse(choice) for choice in list_parser(choices)]
        except ValueError:
            choices = None
        #
        if choices is None:
            raise ValueError(f"Choices '{choices}' cannot be parsed")
        return Choices(choices)


class DelayedDefaultValidator(BaseValidator):

    """Validator to check default correctness only at the end"""

    def __init__(self, parse_function, default=NOT_DEFINED, choices=None):
        super().__init__(parse_function, default=NOT_DEFINED, choices=choices)
        self._default = default

    @property
    def default(self):
        """means value should not be set, is for documentation and help"""
        return self._default

    def set_default(self, value):
        self.set(value)
        self._default = value

    def get(self):
        """Return self._value if its set or not!"""
        if self._value is NOT_DEFINED:
            if self._default is NOT_DEFINED:
                return self._default
            self.set(self._default)
        return self._value


class ListValidator(DelayedDefaultValidator):

    """Validator for list(typ) syntax"""

    def __init__(self, validator, nele, default=NOT_DEFINED):
        self._validator = validator
        self.nele = nele

        def parse(inp):
            return self.list_parse(inp)

        super().__init__(parse, default=default, choices=None)

    def list_parse(self, inp):
        """parse function for list"""
        if isinstance(inp, str):
            lst = list_parser(inp)
        else:
            lst = inp

        error = {'error': None, 'ele': []}

        out = []
        for ele in lst:
            try:
                out.append(self._validator.validate(ele))
            except ValueError as err:
                error['error'] = err
                error['ele'].append(ele)

        if error['error'] is not None:
            raise ValueError(str(error['error']) +
                             f" for elements [{', '.join(error['ele'])}] in [{', '.join(lst)}]")

        if self.nele > 0:
            if len(out) != self.nele:
                raise ValueError(f"Number of elements can only be '{self.nele}'")
        return out


def uint(value, larger=-1):
    val = int(value)
    if val > larger:
        return val
    raise ValueError(f"Value '{val}' smaller than expected '{larger}'")


def flatten_validator_dct(validators):

    out = {}
    for validator_type in validators:
        #
        for typ, parser in validator_type.cases.items():
            if typ in out:
                raise ValueError(f"Validator Type '{typ}' already defined")
            out[typ] = ValidatorParser(validator_type.cls, parser)
    return out


class ValidatorSelector:

    """Contains the logic how to select a particular validator"""

    validators = flatten_validator_dct([
        ValidatorType(DelayedDefaultValidator, {
            'existing_file': file_exists,
            'existing_folder': folder_exists,
            'non_existing_file': non_existing_path,
            'non_existing_folder': non_existing_path,
        }),
        #
        ValidatorType(BaseValidator, {
            'str': str,
            'bool': bool_parser,
            'list': list_parser,
            'ilist': ilist_parser,
            'ilist_np': ilist_np_parser,
            'flist': flist_parser,
            'flist_np': flist_np_parser,
            'file': abspath,  # return abspath
            'folder': abspath,
            # python objects
            'python(list)': as_python_list,
            'python(dict)': as_python_dict,
            'python(tuple)': as_python_tuple,
            'python(np.array)': as_python_numpy_array,
        }),
        #
        ValidatorType(RangeValidator, {
            'int': int,
            'float': float,
        }),
    ])

    types = {'base': BaseValidator, 'range': RangeValidator,
             'delayed_default': DelayedDefaultValidator}

    def __new__(cls, typ):
        res = cls.validators.get(typ)
        if res is None:
            raise ValueError(f"Typ '{typ}' is unknown, use one of [{' '.join(cls.validators )}]")
        return res

    @classmethod
    def add_validator(cls, name, func, typ='base'):
        """Add a new custom validator.

        Parameters
        ----------
        name: str
            name of the validator typ
        func: function
            validation function, should raise ValueError on fail
        typ: str, optional
            typ of validator, currently: base, range

        Raises
        ------
        ValueError
            In case the typ is unknown
        """
        basetyp = cls.types.get(typ)
        if basetyp is None:
            raise ValueError("ValidatorBaseType  '{typ}' unknown")
        if name in cls.validators:
            raise ValueError(f"Validator type '{typ}' already known")
        cls.validators[name] = ValidatorParser(basetyp, func)

    @classmethod
    def remove_validator(cls, name):
        """Remove validator """
        del cls.validators[name]


class Validator:

    """ Validator Factory class """

    def __new__(cls, typ, default=NOT_DEFINED, choices=None):
        return cls._get_all_validators(typ, default, choices)

    @classmethod
    def add_validator(cls, name, func, *, typ='base'):
        """Add a new custom validator.

        Parameters
        ----------
        name: str
            name of the validator typ
        func: function
            validation function, should raise ValueError on fail
        typ: str, optional
            typ of validator, currently: base, range

        Raises
        ------
        ValueError
            In case the typ is unknown
        """
        ValidatorSelector.add_validator(name, func, typ=typ)

    @classmethod
    def remove_validator(cls, name):
        """Remove validator """
        ValidatorSelector.remove_validator(name)

    @classmethod
    def overwrite_validator(cls, name, func, *, typ='base'):
        """Add a new custom validator.

        Parameters
        ----------
        name: str
            name of the validator typ
        func: function
            validation function, should raise ValueError on fail
        typ: str, optional
            typ of validator, currently: base, range

        Raises
        ------
        ValueError
            In case the typ is unknown
        """
        cls.remove_validator(name)
        cls.add_validator(name, func, typ=typ)

    @classmethod
    def _get_list_info(cls, typ):
        """TODO: improve error messages"""
        if typ[-1] != ')':
            raise ValueError(f"Do not understand type '{typ}'")
        typ = typ[5:-1]
        typ = typ.split(':')
        if len(typ) == 1:
            return typ[0].strip(), ListInfo(True, -1)
        if len(typ) > 2:
            raise ValueError(f"Do not understand type '{typ}'")
        try:
            return typ[0].strip(), ListInfo(True, uint(typ[1], larger=0))
        except ValueError:
            raise ValueError(f"Do not understand type '{typ}'") from None

    @classmethod
    def _get_all_validators(cls, typ, default, choices):
        # list(typ) or list(typ, 10) are special validators
        if typ.startswith('list('):
            typ, list_info = cls._get_list_info(typ)
        else:
            list_info = ListInfo(False, 0)
        #
        if typ == 'bool' and choices is None:
            choices = 'y, n'
        #
        clstyp, func = ValidatorSelector(typ)
        if list_info.is_list is True:
            validator = clstyp(func, default=NOT_DEFINED, choices=choices)
            return ListValidator(validator, list_info.nele, default=default)
        return clstyp(func, default=default, choices=choices)
