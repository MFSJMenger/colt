from ._types import Type


class Action:
    """Basic Action object to wrap functions and add types"""

    __slots__ = ('_func', 'inp_types', 'nargs', 'out_typ')

    def __init__(self, func, inp_types, out_typ, need_visitor=False):
        #
        if need_visitor is False:
            func = with_self(func)
        self._func = func
        self.inp_types = tuple(Type(typ) for typ in inp_types)
        self.nargs = len(inp_types)
        self.out_typ = Type(out_typ)

    def __call__(self, workflow, inp):
        return self._func(workflow, *inp)


class IteratorAction(Action):
    """Loop over an iterator"""

    __slots__ = ('iterator_id', 'use_progress_bar')

    def __init__(self, func, inp_types, out_typ, iterator_id=0, need_visitor=False, use_progress_bar=False):
        super().__init__(func, inp_types, out_typ, need_visitor=need_visitor)
        self.use_progress_bar = use_progress_bar
        self.iterator_id = iterator_id

    def __call__(self, workflow, inp):
        out = {}
        #
        if self.use_progress_bar:
            iterator = ProgressBar(inp[self.iterator_id], len(inp[self.iterator_id]))
        else:
            iterator = inp[self.iterator_id]
        #
        for ele in iterator:
            out[ele] = self._func(workflow, *inp[:self.iterator_id], ele, *inp[self.iterator_id+1:])
        return out


class ProgressBar:
    """Basic Class to handle progress"""

    def __init__(self, iterator, nele, width=80):
        self.iterator = iterator
        self.nele = nele
        self.width = width

    def progress_bar_string(self, i):
        icurrent = int(i/self.nele * self.width)
        bar = "="*icurrent + ' '*(self.width - icurrent)
        return f'Progress: [{bar}] {round(icurrent*100/self.width, 2)}%'

    def __iter__(self):
        try:
            for i, ele in enumerate(self.iterator):
                print(f'\r{self.progress_bar_string(i)}', end='')
                yield ele
            print(f'\r{self.progress_bar_string(self.nele)}', end='')
        finally:
            print()


def with_self(func):
    def _wrapper(self, *args, **kwargs):
        return func(*args, **kwargs)
    return _wrapper
