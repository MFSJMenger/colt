import sys
from functools import wraps, partial
from .slottedcls import slottedcls
# import traceback


class _BaseContextDecorator:

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

    def __init__(self, *args, fallback=None, **kwargs):
        self._args = args
        self._kwargs = kwargs
        if fallback is None:
            fallback = _pass
        self._fallback = fallback

    def __exit__(self, exception_type, exception_value, traceback):
        if exception_type is not None:
            self._fallback(*self._args, **self._kwargs)
            return True
        return None


class TryOnException(_BaseContextDecorator):

    __slots__ = ('_tuple', '_defaults', '_dct', 'result')

    def __init__(self, dct):
        self._tuple = slottedcls("name", (key for key in dct))
        self._defaults = dct
        self._dct = {key: None for key in dct}
        self.result = None

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        if exception_type is not None:
            self.result = self._tuple(*(value for value in self._defaults.values()))
            return True
        self.result = self._tuple(*(value for value in self._dct.values()))
        return None

    def set_value(self, key, value):
        self._dct[key] = value


class ConsoleLogger:

    __slots__ = ('write', )

    def __init__(self):
        self.write = partial(print, end='')


class ExitOnException(_BaseContextDecorator):

    __slots__ = ('logger', )

    def __init__(self, logger=None):
        if logger is None:
            self.logger = ConsoleLogger()

    def __exit__(self, exception_type, exception_value, tb):
        if exception_type is not None:
            # traceback.extract_tb(exception_type, exception_value, tb)
            # stack = traceback.extract_tb(tb)
            # for line in traceback.format_list(stack):
            #     print(line, end='')
            self.logger.write(f"Error Termination: {exception_value}\n")
            sys.exit()
