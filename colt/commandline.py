from .colt import Colt


def _init(self, function):
    self._function = function
    self.__doc__ = self._function.__doc__


def _call(self, *args, **kwargs):
    # call with arguments
    if any(len(value) != 0 for value in (args, kwargs)):
        return self._function(*args, **kwargs)
    # call from commandline
    answers = self.from_commandline(self._description)
    return self._function(**answers)


def _from_config(cls, answers):
    return answers


class FromCommandline:

    def __init__(self, questions, description=None):

        self._cls = type("CommandlineInterface", (Colt,), {
            '_questions': questions,
            '_description': description,
            '__init__': _init,
            'from_config': classmethod(_from_config),
            '__call__': _call,
            })

    def __call__(self, function):
        return self._cls(function)
