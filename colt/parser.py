import sys


class FullName:

    def __init__(self, value):
        if isinstance(value, str):
            self._value = (value, )
        elif isinstance(value, (list, tuple, set)):
            if len(value) > 2:
                raise ValueError("Can maximum have two entries")
            self._value = value
        else:
            raise ValueError("Value can only be set/list/tuple or string")

    def __eq__(self, value):
        return value in self._value

    def __str__(self):
        if len(self._value) == 1:
            return f"{self._value[0]}"
        else:
            return f"{self._value[0]}/{self._value[1]}"


class NumberOfArguments:

    allowed = ("+", "?")

    def __init__(self, nargs, is_optional):
        self.is_finite, self.num = self._get_nargs(nargs, is_optional)

    def __eq__(self, value): 
        return self.num == value

    def _get_nargs(self, nargs, is_optional):
        if nargs is None:
            return True, 1
        #
        if not isinstance(nargs, (str, int)):
            raise ValueError("nargs can only be str or int")

        if isinstance(nargs, str):
            self.allowed = ("+", "?")
            if nargs not in self.allowed:
                raise ValueError(f"nargs can only be {', '.join(self.allowed)}")

            if nargs in ('?', ) and not is_optional:
                raise ValueError(f"sepecial nargs '{nargs}' can only be used if optional")

            return False, nargs

        return True, nargs



class Argument:

    def __init__(self, name, metavar=None, nargs=None, typ=None, help=None):
        self.is_optional, self.fullname, self.metavar = self._check(name, metavar)
        self.nargs = NumberOfArguments(nargs, self.is_optional)
        self.typ = typ
        self.help = help

    def consume(self, args):
        result = []
        if self.nargs.is_finite:
            for _ in range(self.nargs.num):
                value = args.get_arg() # ignores --, -value
                if value is None:
                    raise ValueError(f"Too few arguments for {self.fullname} expected {self.nargs} got {len(result)}")
                result.append(value)
        else:
            while True:
                print(f"{self.fullname}: value = ", args.peek())
                value = args.get_arg() # ignores --, -value
                if value is None:
                    print(result)
                    if len(result) == 0 and self.nargs == '?':
                        raise ValueError(f"Too few arguments for {self.fullname} expected at least one value")
                    break
                result.append(value)
        print(self.fullname, ": ", result)

    @property
    def is_finite(self):
        return self.nargs.is_finite

    def __eq__(self, value):
        return value == self.fullname

    def to_commandline_str(self, is_not_last):
        if self.is_finite:
            output = " ".join(self.metavar for _ in range(self.nargs.num))
        else:
            if self.nargs == '+':
                output = f"{self.metavar} [{self.metavar} ...]"
            elif self.nargs == '?':
                output = f"[{self.metavar} ...]"
            if is_not_last is True:
                output += " --"
        
        if self.is_optional is True:
            return f"{self.fullname} {output}"
        return f"{output}"

    def _check(self, name, metavar):
        if isinstance(name, str):
            return self._check_string(name, metavar)
        # try to convert to tuple
        names = tuple(name)
        if len(names) != 2:
            raise ValueError("Can only have two alternatives")
        #
        for ele in names:
            if not ele.startswith('-'):
                raise ValueError("In case of multiple, has to be option!")
            if ele.startswith('---'):
                raise ValueError("can only start with '--'")
        #
        if metavar is None:
            for ele in names:
                if ele.startswith('--'):
                    metavar = ele[2:]
            # take the first one
            if metavar is None:
                metavar = names[0][1:]
        return True, FullName(names), metavar

    def _check_string(self, name, metavar):
        is_optional = False
        if name.startswith('-'):
            if name.startswith('---'):
                raise Exception("args can only start with one, or two dashes")
            is_optional = True
            if metavar is None:
                if name.startswith('--'):
                    metavar = name[2:]
                else:
                    metavar = name[1:]
        else:
            if metavar is None:
                metavar = name
        return is_optional, FullName(name), metavar


class SysIterator:

    def __init__(self, args=None):
        if args is None:
            args = sys.argv[1:]
        self.args = args
        self.nele = len(self.args)
        self.idx = -1

    @property
    def inc(self):
        self.idx += 1

    def __iter__(self):
        return self

    def __next__(self):
        value = self.get_next()
        if value is not None:
            return value
        raise StopIteration

    def peek(self):
        idx = self.idx + 1
        if idx < self.nele:
            return self.args[idx]
        return None

    def get_arg(self):
        arg = self.peek()
        if arg is None or arg.startswith('-'):
            return None
        self.idx += 1
        return arg

    def get_next(self):
        self.idx += 1
        if self.idx < self.nele:
            return self.args[self.idx]
        return None

def surround(string):
    return f"[{string}]"


def get_short_help(name, args, opt_args):
    
    nargs = len(args)
    out = " ".join(arg.to_commandline_str(i < nargs)
                   for i, arg in enumerate(args, start=1))
    opts = " ".join(surround(arg.to_commandline_str(False))
                    for arg in opt_args)

    return f"usage: {name} {opts} {out}"
    

class ArgumentParser:

    def __init__(self):
        self.optional_args = []
        self.args = []
        self.child = None

    def parse(self):
        index = 0
        iterator = SysIterator()
        while True:
            ele = iterator.peek()
            if ele is None:
                break
            if ele == '--': # just ignore '--' steps 
                iterator.inc
                continue 
            if ele.startswith('-'): # get optional
                for arg in self.optional_args:
                    if arg == ele:
                        iterator.inc
                        arg.consume(iterator)
            else:
                if index < len(self.args):
                    arg = self.args[index]
                    arg.consume(iterator)
                    index += 1
                else:
                    break
        #
        if self.child is None:
            self._check_final(index, iterator)

    def _check_final(self, index, iterator):
        if index != len(self.args):
            raise Exception("Too few arguments")
        if iterator.get_next() is not None:
            raise Exception("Too many arguments")

    def add_argument(self, name, nargs=None, metavar=None, typ=None, help=None):
        arg = Argument(name, metavar=metavar, nargs=nargs, typ=typ, help=help)
        if arg.is_optional:
            self.optional_args.append(arg)
        else:
            self.args.append(arg)

    def print_help(self):
        print(get_short_help("parser", self.args, self.optional_args))
