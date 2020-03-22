from functools import wraps
#
from .colt import Colt
from .validator import Validator


class FromCommandline:

    def __init__(self, questions, description=None):

        class Example(Colt):
            _questions = questions

            @classmethod
            def from_config(cls, answers):
                return answers
        
        self._cquest = Example
        self._description = None

    def __call__(self, function):

        @wraps(function)
        def __wrapper():
            answers = self._cquest.from_commandline(self._description)
            return function(**answers)
        
        return __wrapper
