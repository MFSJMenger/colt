import numpy as np


__all__ = ["LineParser"]


class LineParser:
    """Namespace to store line parsers"""

    @staticmethod
    def bool_parser(answer):
        """convert string into a bool"""

        _positive = ('y', 'yes', 'True', 'true')
        _negative = ('n', 'no', 'False', 'false')
        #
        if answer in _positive:
            return True
        if answer in _negative:
            return False

        raise Exception("Answer can only be [%s] or [%s]"
                        % (", ".join(_positive), ", ".join(_negative)))

    @classmethod
    def list_parser(cls, answer):
        """convert string to list of strings"""
        split_char, answer = cls._prepare_list_parsing(answer)
        return [ele for ele in answer.split(split_char)]

    @classmethod
    def flist_parser(cls, answer):
        """convert string to list of floats"""
        split_char, answer = cls._prepare_list_parsing(answer)
        return [float(ele) for ele in answer.split(split_char)]

    @classmethod
    def flist_np_parser(cls, answer):
        """Transfers a string into a numpy array of floats"""
        return np.array(cls.flist_parser(answer))

    @classmethod
    def ilist_parser(cls, answer):
        """convert string to list of integers"""
        split_char, answer = cls._prepare_list_parsing(answer)
        if '~' not in answer:
            return [int(ele) for ele in answer.split(split_char)]
        numbers = (cls.parse_integer_numbers(number) for number in answer.split(split_char))
        return sum(numbers, [])

    @classmethod
    def ilist_np_parser(cls, answer):
        """convert string to numpy array of integers"""
        return np.array(cls.ilist_parser(answer))

    @staticmethod
    def get_upper_bounds(start, stop):
        """get upper bound for range"""
        start = int(start)
        stop = int(stop)
        if start > stop:
            start, stop = stop, start
        if stop < 0:
            return start, stop+1
        else:
            return start, stop+1

    @classmethod
    def parse_integer_numbers(cls, string):
        """convert integer numbers into ilist liste"""
        # check if tilde in line
        if '~' in string:
            start, _, stop = string.partition('~')
            start, stop = cls.get_upper_bounds(start, stop)
            return list(range(start, stop))
        else:
            return [int(string)]

    @classmethod
    def _prepare_list_parsing(cls, answer):
        """setup string for list parsing"""
        split_char = cls.choose_split_char(answer)
        answer = cls.remove_brackets(answer)
        return split_char, answer

    @staticmethod
    def choose_split_char(answer):
        """get a suitable split character"""
        if ',' in answer:
            split_char = ","
        else:
            split_char = None
        return split_char

    @staticmethod
    def remove_brackets(string):
        """remove brackets from string"""
        return string.replace("[", "").replace("]", "")
