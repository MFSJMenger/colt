import sys
from functools import wraps, partial
from collections import namedtuple
import traceback


class _BaseContextDecorator(object):

    def __enter__(self):
        pass

    def __exit__(self, exception_type, exception_value, traceback):
        pass

    def __call__(self, func):

        @wraps(func)
        def _wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)

        return _wrapper


def _pass():
    pass


class DoOnException(_BaseContextDecorator):
    """Performs fallback function, if exception is raised"""

    def __init__(self, fallback=None, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs
        if fallback is None:
            fallback = _pass
        self._fallback = fallback

    def __exit__(self, exception_type, exception_value, traceback):
        if exception_type is not None:
            self._fallback(*self._args, **self._kwargs)
            return True


class TryOnException(_BaseContextDecorator):

    def __init__(self, dct):
        self._tuple = namedtuple("name", (key for key in dct))
        self._defaults = dct
        self._dct = {key: None for key in dct}

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        if exception_type is not None:
            self.result = self._tuple(*(value for value in self._defaults.values()))
            return True
        else:
            self.result = self._tuple(*(value for value in self._dct.values()))

    def set_value(self, key, value):
        self._dct[key] = value


class ConsoleLogger():

    def __init__(self):
        self.write = partial(print, end='')


class ExitOnException(_BaseContextDecorator):

    def __init__(self, logger=None):
        if logger is None:
            self.logger = ConsoleLogger()

    def __exit__(self, exception_type, exception_value, tb):
        if exception_type is not None:
            # traceback.extract_tb(exception_type, exception_value, tb)
            stack = traceback.extract_tb(tb)
            for line in traceback.format_list(stack):
                print(line, end='')
            print(f"Error Termination: {exception_value}")
            self.logger.write(f"Error Termination: {exception_value}\n")
            sys.exit()
