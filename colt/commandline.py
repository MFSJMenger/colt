from functools import wraps
#
from .colt import Colt


class FromCommandline:

    def __init__(self, questions, description=None):

        class Example(Colt):
            _questions = questions
            _description = description

            def __init__(self, function):
                self._function = function

            @classmethod
            def from_config(cls, answers):
                return answers

            def __call__(self):
                answers = self.from_commandline(self._description)
                return self._function(**answers)

        self._cquest = Example

    def __call__(self, function):
        return self._cquest(function)
