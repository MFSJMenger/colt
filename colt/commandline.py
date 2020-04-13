from .colt import Colt


class FromCommandline:

    def __init__(self, questions, description=None):

        class Example(Colt):
            _questions = questions
            _description = description

            def __init__(self, function):
                self._function = function
                self.__doc__ = self._function.__doc__

            @classmethod
            def from_config(cls, answers):
                return answers

            def __call__(self, *args, **kwargs):
                # call with arguments
                if any(len(value) != 0 for value in (args, kwargs)):
                    return self._function(*args, **kwargs)
                # call from commandline
                answers = self.from_commandline(self._description)
                return self._function(**answers)

        self._cquest = Example

    def __call__(self, function):
        return self._cquest(function)
