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
    def flist_parser(cls, answer):
        """Transfers a string into a list of float"""
        if ',' in answer:
            split_char = ","
        else:
            split_char = None
        answer = cls.remove_brackets(answer)
        return [float(ele) for ele in answer.split(split_char)]

    @classmethod
    def flist_np_parser(cls, answer):
        """Transfers a string into a numpy array of floats"""
        return np.array(cls.flist_parser(answer))

    @classmethod
    def ilist_parser(cls, answer):
        """Transfers a string into a list of integers"""
        if ',' in answer:
            split_char = ","
        else:
            split_char = None

        answer = cls.remove_brackets(answer)
        if '~' not in answer:
            return [int(ele) for ele in answer.split(split_char)]

        numbers = []
        for number in answer.split(split_char):
            numbers += cls.parse_integer_numbers(number)
        return numbers

    @classmethod
    def ilist_np_parser(cls, answer):
        """returns a numpy list of integers"""
        return np.array(cls.ilist_parser(answer))

    @staticmethod
    def remove_brackets(string):
        """remove brackets from string"""
        return string.replace("[", "").replace("]", "")

    @staticmethod
    def parse_integer_numbers(number):
        """transforms a string into a list of integer numbers"""
        # check if tilde in line
        if '~' in number:
            number = number.partition('~')
            return list(range(int(number[0]), int(number[2])+1))
        return [int(number)]
