

__all__ = ["LineParser"]


class LineParser(object):
    """Namespace to store line parsers"""

    @staticmethod
    def bool_parser(answer):
        #
        _positive = ('y', 'yes')
        _negative = ('n', 'no')
        #
        if answer in _positive:
            return True
        elif answer in _negative:
            return False
        else:
            raise Exception("Answer can only be [%s] or [%s]"
                            % (", ".join(_positive), ", ".join(_negative)))

    @staticmethod
    def ilist_parser(answer):
        if '~' not in answer:
            return list(map(int, answer.split(',')))

        numbers = []
        for number in answer.split(','):
            numbers += LineParser.parse_integer_numbers(number)
        return numbers

    @staticmethod
    def parse_integer_numbers(number):
        # check if tilde in line
        if '~' in number:
            number = number.partition('~')
            return list(range(int(number[0]), int(number[2])+1))
        else:
            return [int(number)]
