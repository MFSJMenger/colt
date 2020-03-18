import os
import numpy as np


def abspath(answer):
    return os.path.abspath(os.path.expanduser(answer))


def file_exists(path):
    path = abspath(path)
    if not os.path.isfile(path):
        raise ValueError(f"File does not exisit '{path}'")
    return path

def folder_exists(path):
    path = abspath(path)
    if not os.path.isdir(path):
        raise ValueError(f"Folder does not exisit '{path}'")
    return path

def non_existing_path(path):
    path = abspath(path)
    if os.path.exists(path):
        raise ValueError(f"File/Folder does already exisit '{path}'")
    return path


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


# empty class
class NotDefined:
    __slots__ = ()

    def __repr__(self):
        return "<NOT_DEFINED>"

    def __str__(self):
        return "<NOT_DEFINED>"


NOT_DEFINED = NotDefined()


class Validator:

    _parsers = {
        'str': str,
        'float': float,
        'int': int,
        'bool': bool_parser,
        'list': list_parser,
        'ilist': ilist_parser,
        'ilist_np': ilist_np_parser,
        'flist': flist_parser,
        'flist_np': flist_np_parser,
        'file': abspath,  # return abspath
        'folder': abspath,
        'existing_file': file_exists,
        'existing_folder': folder_exists,
        'non_existing_file': non_existing_path,
        'non_existing_folder': non_existing_path,
    }

    def __init__(self, typ, default=NOT_DEFINED, choices=None):
        #
        self._parse = self._parsers[typ]
        #
        self._value = self._set_value(default)
        self._choices = self._set_choices(choices)

    def _set_value(self, default):
        if default is not NOT_DEFINED:
            default = self.validate(default)
        return default

    def _set_choices(self, choices):
        """set choices"""
        if choices is None:
            return None
        try:
            return [self._parse(choice) for choice in choices]
        except ValueError:
            pass
        raise ValueError("Choises ({' ,'.join(choices)}) cannot be converted")

    def validate(self, value):
        return self._parse(str(value))

    def get(self):
        if self._value is NOT_DEFINED:
            raise ValueError("Value not defined!")
        return self._value

    def set(self, value):
        self._value = self.validate(value)

    @classmethod
    def register_parser(cls, name, parser):
        if not isinstance(name, str):
            raise ValueError("key needs to be a string")
        if not callable(parser):
            raise ValueError("parser needs to be callable with a single argument")
        cls._parsers[name] = parser

    @classmethod
    def get_parsers(cls):
        return cls._parsers
