

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
