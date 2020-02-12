import numpy as np
import os


def abspath(answer):
    return os.path.abspath(os.path.expanduser(answer))


def file_exists(cls, path):
    path = cls.abspath(path)
    if not os.path.isfile(path):
        raise ValueError("File does not exist")
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
    return [ele.strip() for ele in answer.split(split_char)]


def flist_parser(answer):
    """convert string to list of floats"""
    split_char, answer = _prepare_list_parsing(answer)
    return [float(ele) for ele in answer.split(split_char)]


def flist_np_parser(answer):
    """Transfers a string into a numpy array of floats"""
    return np.array(flist_parser(answer))


def ilist_parser(answer):
    """convert string to list of integers"""
    split_char, answer = _prepare_list_parsing(answer)
    if '~' not in answer:
        return [int(ele) for ele in answer.split(split_char)]
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
