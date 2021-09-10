import sys
from collections import namedtuple, UserList
from contextlib import contextmanager

from .validator import ValidatorErrorNotInChoices
from .qform import QuestionForm, QuestionVisitor, join_keys, split_keys


EmptyQuestion = namedtuple("EmptyQuestion", ("typ", "choices", "comment", "is_hidden"))
Element = namedtuple('Element', ('lines', 'format', 'nlines'))
Description = namedtuple("Description", ("logo", "description", "short_description"))
Spacing = namedtuple("Spacing", ("seperator", "block_seperator"))
Orders = namedtuple("Ordering", ("main", "error", "short", "args"))
Blocks = namedtuple("Blocks", ("opt_args", "pos_args", "subparser"))


class OptionalArgumentsStorage(UserList):

    def __init__(self, lst=None):
        self._keys = set()
        super().__init__()
        if lst is not None:
            for ele in lst:
                self.append(ele)

    def append(self, value):
        if not isinstance(value, Action):
            raise ValueError("Con only add action objects")
        self._check_options(value)
        self.data.append(value)

    def check_answers(self):
        wrong_ones = {}
        for action in self.data:
            if isinstance(action, EventAction):
                continue
            try:
                action.question.get_answer()
            except ValueError as e:
                wrong_ones[action.name] = e
        if len(wrong_ones) == 0:
            return None
        return wrong_ones

    def _check_options(self, action):
        for opt in action.fullname:
            if opt not in self._keys:
                self._keys.add(opt)
            else:
                raise ValueError(f"option {opt} already used defined, no name clashes allowed")


class FullName:

    def __init__(self, value):
        if isinstance(value, str):
            self._value = (value.strip(), )
        elif isinstance(value, (list, tuple)):
            if len(value) > 2:
                raise ValueError("Can maximum have two entries")
            self._value = self._sort(value)
        else:
            raise ValueError("Value can only be set/list/tuple or string")

    @staticmethod
    def _sort(values):
        values = tuple(val.strip() for val in values)
        if len(values[0]) > len(values[1]):
            return (values[1], values[0])
        return values

    def __iter__(self):
        return iter(self._value)

    def __eq__(self, value):
        return value in self._value

    def __str__(self):
        if len(self._value) == 1:
            return f"{self._value[0]}"
        return f"{self._value[0]}/{self._value[1]}"

    @property
    def small(self):
        return self._value[0]


class NumberOfArguments:

    allowed = ("+", )

    def __init__(self, nargs):
        self.is_finite, self.num = self._get_nargs(nargs)

    def __eq__(self, value):
        return self.num == value

    def _get_nargs(self, nargs):
        if nargs is None:
            return True, 1
        #
        if nargs == -1:
            nargs = '+'
        #
        if not isinstance(nargs, (str, int)):
            raise ValueError("nargs can only be str or int")

        if isinstance(nargs, str):
            if nargs not in self.allowed:
                raise ValueError(f"nargs can only be {', '.join(self.allowed)}")

            return False, nargs

        return True, nargs


def check_names(name, metavar):
    if isinstance(name, str):
        return check_string(name, metavar)
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


def check_string(name, metavar):
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


class Action:

    def __init__(self, name, question):
        self.question = question
        if not isinstance(name, FullName):
            name = FullName(name)
        self.fullname = name

    @property
    def choices(self):
        """No choices defined by default"""
        if self.question.choices is None:
            return ''
        return self.question.choices

    @property
    def name(self):
        """Name of the action"""
        return str(self.fullname)

    @property
    def typ(self):
        """Typ of the action"""
        return self.question.typ

    @property
    def comment(self):
        if self.question.comment is None:
            return ""
        return self.question.comment

    @property
    def is_hidden(self):
        return self.question.is_hidden

    def consume(self, args):
        raise NotImplementedError("consume needs to be implemented!")


class SetArgumentAction(Action):

    def __init__(self, name, question, *, metavar=None):
        _, fullname, self.metavar = check_names(name, metavar)
        super().__init__(fullname, question)
        if question.is_list_validator is True:
            nargs = question.validator.nele
        else:
            nargs = 1
        self.nargs = NumberOfArguments(nargs)

    def __eq__(self, value):
        return self.fullname == value

    @property
    def is_finite(self):
        return self.nargs.is_finite

    @property
    def answer(self):
        return self.question.get_answer()

    def consume(self, args):
        result = []
        if self.nargs.is_finite:
            for _ in range(self.nargs.num):
                value = args.get_arg()  # ignores --, -value
                if value is None:
                    raise ValueError(f"Too few arguments for {self.fullname} "
                                     f"expected {self.nargs} got {len(result)}")
                result.append(value)
        else:
            while True:
                value = args.get_arg()  # ignores --, -value
                if value is None:
                    if len(result) == 0:
                        raise ValueError(f"Too few arguments for {self.fullname} "
                                         f"expected at least one value")
                    break
                result.append(value)
        # set value
        if self.question.is_list_validator is True:
            self.question.answer = result
        else:
            self.question.answer = result[0]

    def to_commandline_str(self, is_not_last):
        return self._commandline_str(is_not_last)

    def _commandline_str(self, is_not_last):
        if self.is_finite:
            output = " ".join(self.metavar for _ in range(self.nargs.num))
        else:
            if self.nargs == '+':
                output = f"{self.metavar} [{self.metavar} ...]"
            if is_not_last is True:
                output += " --"
        return output


class OptionalArgument(SetArgumentAction):

    def __repr__(self):
        return f"OptionalArgument({self.fullname}, {self.metavar})"

    def to_commandline_str(self, is_not_last):
        return f"{self.fullname.small} {self._commandline_str(is_not_last)}"


class PositionalArgument(SetArgumentAction):

    @property
    def name(self):
        return self.metavar

    def __repr__(self):
        return f"PositionalArgument({self.fullname}, {self.metavar})"


class EventAction(Action):

    def __init__(self, name, function, *, is_hidden=False, comment=None):
        super().__init__(name, EmptyQuestion('action', None, comment, is_hidden))
        self._fun = function

    def to_commandline_str(self, *args):
        return str(self.fullname.small)

    def consume(self, args):
        # execute action
        self._fun()

    def __eq__(self, value):
        return self.fullname == value


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


DELIM = "---------------------------------------------------"


class ArgFormatter:

    def __init__(self, format):
        # get rid of empty entries
        self._formatter = {key: value for key, value in format.items() if value is not None}
        self.space = self._formatter.pop('seperator', ' ')
        if isinstance(self.space, int):
            self.space = ' ' * self.space

    def format(self, arg):
        return self._format_arg(arg)

    def _get_lines(self, arg, name, length):
        string = getattr(arg, name)
        if string is None:
            string = ""
        else:
            string = str(string)
        out = []
        for line in string.splitlines():
            if len(line) < length:
                out.append(line)
            else:
                while len(line) > length:
                    out.append(line[:length])
                    line = line[length:]
                # do not forget the last part
                out.append(line)
        return out, len(out)

    def _format_arg(self, arg):
        out = {}
        #
        nlen = 0
        for name, length in self._formatter.items():
            res, nlines = self._get_lines(arg, name, length)
            if nlines > nlen:
                nlen = nlines
            out[name] = Element(res, f"%-{length}s", nlines)
        return self._format_string(out, nlen)

    def _format_string(self, data, nlen):
        out = ""
        nvalues = len(data)
        for i in range(nlen):
            for icount, value in enumerate(data.values(), start=1):
                if i < value.nlines:
                    out += value.format % value.lines[i]
                else:
                    out += value.format % ""
                if icount != nvalues:
                    out += self.space
            out += "\n"
        return out


class HelpStringBlock:

    def __init__(self, block_space, line_start, line_end, start, end):
        if start is not None:
            self._lines = [None]  # placeholder for start
        else:
            self._lines = []
        #
        self._block_space = block_space.splitlines()
        if line_end is None and line_start is None:
            self._format_str = None
        elif line_start is None:
            self._format_str = f"{line_start}%s"
            line_end = False
        elif line_end is None:
            self._format_str = f"%s{line_end}"
            line_end = True
        else:
            self._format_str = f"{line_start}%s{line_end}"
            line_end = True
        self._line_end = line_end
        self._last_was_space = False
        self._start = start
        self._end = end
        self._longest_length = 0
        self._is_first = True

    def _format(self, line):
        if self._line_end is True:
            line = line + ' '*(self._longest_length - len(line))
        return self._format_str % line

    @property
    def start(self):
        return self._start * self._longest_length

    @property
    def end(self):
        return self._end * self._longest_length

    def add(self, block, is_space=False):
        if block is None:
            return
        # set block spaces correct
        if not (self._last_was_space is True or is_space is True) and self._is_first is False:
            self._lines += self._block_space
        if self._is_first is True:
            self._is_first = False
        #
        for line in block.splitlines():
            if len(line) > self._longest_length:
                self._longest_length = len(line)
            self._lines.append(line)
        self._last_was_space = is_space

    def render(self):
        if len(self._lines) == 0:
            return ""
        if self._start is not None:
            self._lines[0] = self.start
        if self._end is not None:
            self._lines.append(self.end)
        if self._format_str is None:
            return "\n".join(self._lines)
        return "\n".join(self._format(line) for line in self._lines)


class Block:

    def __init__(self, title, *, indent=None, body_indent=None, delim=None):
        self.title = title
        if isinstance(indent, int):
            indent = ' '*indent
        if isinstance(body_indent, int):
            body_indent = ' '*body_indent
        self._indent = indent
        self._body_indent = body_indent
        self._delim = delim

    @classmethod
    def from_dct(cls, dct):
        return cls(dct['title'], indent=dct.get('indent'),
                   body_indent=dct.get('body_indent'), delim=dct.get('delim'))

    @staticmethod
    def _add_spacing(text, spacing):
        if spacing is None:
            return text
        return "\n".join(spacing + line for line in text.splitlines())

    def render(self, body, *, show_if_empty=False, title=None):
        if title is None:
            title = self.title

        if show_if_empty is False and (body is None or body == ""):
            return None
        if self._delim is not None:
            out = f"{title}\n{self._delim}\n"
        else:
            out = f"{title}\n"
        out += self._add_spacing(body, self._body_indent)
        return self._add_spacing(out, self._indent)


class HelpFormatter:

    _simple_settings = ('description', 'logo', 'short_description',
                        'seperator', 'block_seperator', 'alias',
                        'main_order', 'error_order', 'short_order', 'args_order',
                        'start', 'end', 'line_start', 'line_end')

    settings = {
        'description': None,
        'logo': None,
        'short_description': None,
        'seperator': '\n',
        'block_seperator': '\n\n\n',
        'main_order': ['logo', 'description', 'args', 'usage', 'space', 'comment', 'space'],
        'args_order': ['pos_args', 'opt_args', 'subparser_args'],
        'error_order': ['usage', 'error', 'space'],
        'short_order': ['usage', 'space', 'comment', 'space'],
        'alias': None,
        'line_start': None,
        'line_end': None,
        'start': None,
        'end': None,
        'arg_block': {   # settings for all argument blocks
            'indent': 2,
            'body_indent': 2,
            'delim': DELIM,
        },
        'pos_args': {
            'title': 'positional arguments:',
            'indent': None,
            'body_indent': None,
            'delim': None,
        },
        'opt_args': {
            'title': 'optional arguments:',
            'indent': None,
            'body_indent': None,
            'delim': None,
        },
        'subparser_args': {
            'title': 'Subparser argument: %s',
            'indent': None,
            'body_indent': None,
            'delim': None,
        },
        'arg_format': {
            'name': 20,
            'comment': 50,
            'choices': None,
            'typ': 15,     # maximale breite
            'seperator': 2,
        },
        'subparser_format': {
            'name': 12,
            'comment': 40,
        },
    }

    blocks = ('usage', 'space', 'args', 'opt_args', 'pos_args', 'subparser_args', 'logo',
              'description', 'short_description', 'comment', 'error')

    def __init__(self, settings=None):
        (self._description, self._orders,
         self._spacing, self._arg_formatter, self._subparser_formatter, self._blocks,
         self._info) = self._parse_settings(settings)
        # helper for error storage
        self._error = None

    def update(self, settings):
        """update settings with new ones"""
        (self._description, self._orders,
         self._spacing, self._arg_formatter, self._subparser_formatter, self._blocks,
         self._info) = self._parse_settings(settings)

    def info(self, parser):
        """Main information"""
        return self._render(self._orders.main, parser)

    def short_info(self, parser):
        """short information"""
        return self._render(self._orders.short, parser)

    def error_info(self, parser, error):
        """error information"""
        self._error = str(error)
        return self._render(self._orders.error, parser)

    # definitions
    def args(self, parser):
        return self._render(self._orders.args, parser)

    def space(self, parser):
        """individual block spacing defined by the user"""
        return self._spacing.seperator

    def logo(self, parser):
        """logo: shown everywhere"""
        return self._description.logo

    def description(self, parser):
        """main description of the code"""
        return self._description.description

    def short_description(self, parser):
        """short description of the program"""
        return self._description.short_description

    def comment(self, parser):
        return parser.comment

    def error(self, parser):
        """error message"""
        return f"Error: {self._error}"

    def opt_args(self, parser):
        """opt_args block always shown due to help"""
        return self._blocks.opt_args.render("".join(self._arg_formatter.format(arg)
                                            for arg in parser.optional_args
                                            if not arg.is_hidden))

    def pos_args(self, parser):
        if len(parser.args) == 0:
            return None
        return self._blocks.pos_args.render(
                "".join(self._arg_formatter.format(arg)
                        for arg in parser.args)
        )

    def subparser_args(self, parser):
        if len(parser.children) == 0:
            return None

        block = self._blocks.subparser

        return "\n\n".join(
                block.render("".join(self._subparser_formatter.format(arg)
                             for arg in child.cases.values()),
                             title=block.title % child.name)
                for child in parser.children)

    def usage(self, parser):
        name = self._info.get('alias', sys.argv[0])

        nargs = len(parser.args)
        #
        out = " ".join(arg.to_commandline_str(i < nargs)
                       for i, arg in enumerate(parser.args, start=1))
        subparser = " ".join(arg.to_commandline_str()
                             for arg in parser.children)
        opts = " ".join(surround(arg.to_commandline_str(False))
                        for arg in parser.optional_args
                        if not arg.is_hidden)

        if parser.parent is None:
            return f"usage: {name} {opts} {out} {subparser}"
        return f"usage: {name} ... {parser.name} {opts} {out} {subparser}"

    def format_arg(self, arg):
        """How to format a single line in pos_args, opt_args"""
        return self._arg_formatter.format(arg)

    # helper

    @staticmethod
    def _set_indent(value):
        if isinstance(value, int):
            value = ' '*value
        return value

    def _get_block_info(self, global_default, default, settings):
        if settings is None:
            settings = {}
        self._check_keys(settings, default)
        for key, value in default.items():
            if key == 'title':
                if settings.get(key) is None:
                    settings[key] = value
            elif settings.get(key) is None:
                settings[key] = global_default[key]
        return settings

    def _prepare_settings(self, settings):
        if isinstance(settings, str):
            settings = {'description': settings}
        elif settings is None:
            settings = {}
        self._check_keys(settings, self.settings)
        # set default
        for key in self._simple_settings:
            if settings.get(key) is None:
                settings[key] = self.settings[key]
        #
        if 'arg_block' not in settings:
            block_defaults = self.settings['arg_block']
        else:
            block_defaults = self._update_dct(settings['arg_block'], self.settings['arg_block'])

        for key in ('opt_args', 'pos_args', 'subparser_args'):
            settings[key] = self._get_block_info(block_defaults, self.settings[key],
                                                 settings.get(key))
        #
        arg_format = settings.get('arg_format')
        if arg_format is None:
            settings['arg_format'] = self.settings['arg_format']
        else:
            self._check_keys(settings['arg_format'], self.settings['arg_format'])
        #
        subparser_format = settings.get('subparser_format')
        if subparser_format is None:
            settings['subparser_format'] = self.settings['subparser_format']
        else:
            self._check_keys(settings['subparser_format'], self.settings['subparser_format'])

        return settings

    @staticmethod
    def _check_keys(current, allowed, ignore=[]):
        """ignore is immutable, so putting it to [] is fine"""
        if any(key not in allowed for key in current if key not in ignore):
            unknown = [key for key in current if (key not in ignore and key not in allowed)]
            raise ValueError(f"Key(s) '{unknown}' in Settings unknown")

    def _update_dct(self, settings, default, ignore=[]):
        if settings is None:
            settings = {}
        self._check_keys(settings, default, ignore=ignore)
        self._update_settings(settings, default)
        return settings

    @staticmethod
    def _update_settings(settings, default):
        for key, value in default.items():
            if settings.get(key, None) is None:
                settings[key] = value
        return settings

    def _parse_settings(self, settings):
        try:
            settings = self._prepare_settings(settings)
        except ValueError as e:
            raise SystemExit(f"Error setting commandline setting: {e}") from None
        #
        arg_formatter = ArgFormatter(settings['arg_format'])
        subparser_formatter = ArgFormatter(settings['subparser_format'])

        orders = Orders(settings['main_order'], settings['error_order'], settings['short_order'],
                        settings['args_order'])
        spacing = Spacing(settings['seperator'], settings['block_seperator'])
        description = Description(settings['logo'], settings['description'],
                                  settings['short_description'])
        blocks = Blocks(Block.from_dct(settings['opt_args']),
                        Block.from_dct(settings['pos_args']),
                        Block.from_dct(settings['subparser_args'])
                        )
        if settings['start'] is not None and len(settings['start']) != 1:
            raise ValueError("Start can only be single character")
        if settings['end'] is not None and len(settings['end']) != 1:
            raise ValueError("End can only be single character")

        info = {
            'line_start':  self._set_indent(settings['line_start']),
            'line_end':  self._set_indent(settings['line_end']),
            'start': settings['start'],
            'end': settings['end'],
        }
        if settings['alias'] is not None:
            info['alias'] = settings['alias']

        self._line_end = self._set_indent(settings['line_end'])
        return description, orders, spacing, arg_formatter, subparser_formatter, blocks, info

    def _do_task(self, task, parser):
        taskfunc = getattr(self, task, None)
        if taskfunc is None:
            raise ValueError(f"Task '{task}' unknown")
        return taskfunc(parser)

    def _render(self, blocks, parser):
        string = HelpStringBlock(self._spacing.block_seperator,
                                 self._info['line_start'], self._info['line_end'],
                                 self._info['start'], self._info['end'])
        for task in blocks:
            string.add(self._do_task(task, parser), task == 'space')
        return string.render()

    def _check(self, order):
        if any(ele not in self.blocks for ele in order):
            unknown = [ele for ele in order if ele not in self.blocks]
            raise Exception(f"Could not understand block(s) {unknown}")
        return order


class SubParser(Action):

    def __init__(self, name, question, parent):
        _, name = split_keys(name)
        super().__init__(name, question)
        self._options = {}
        self._parent = parent

    @property
    def cases(self):
        return self._options

    def to_commandline_str(self):
        return f"{self.fullname} ..."

    def consume(self, args):
        value = args.get_arg()  # ignores --, -value
        if value is None:
            raise ValueError("Two few arguments")
        #
        error = ValueError(f"'{self.name}' needs to be "
                           f"[{', '.join(child for child in self._options)}] not '{value}'")
        #
        try:
            self.question.answer = value
        except ValidatorErrorNotInChoices:
            raise error from None
        # not necessary anymore
        parser = self._options.get(value, None)
        if parser is None:
            raise error
        return parser

    def add_parser(self, name, formatter, *, comment=None):
        parser = ArgumentParser(formatter=formatter, name=name,
                                comment=comment, parent=self._parent)
        self._options[name] = parser
        return parser


def get_help(parser):
    """Closure to get exit to the print_help function of the parser"""

    def _help():
        parser.print_help()
        sys.exit()

    return EventAction(["-h", "--help"], _help, comment="show this help message and exit")


class ArgumentParser:

    def __init__(self, *, name=None, formatter=None, parent=None, comment=None):
        self.optional_args = OptionalArgumentsStorage([get_help(self)])
        self.args = []
        self.parent = parent
        self.children = []
        self.formatter = formatter
        self.name = name
        self.comment = comment

    @property
    def help(self):
        return self.formatter.info(self)

    def add_subparser(self, name, question):
        child = SubParser(name, question, parent=self)
        self.children.append(child)
        return child

    def parse(self, *, args=None, is_last=True):
        if args is None:
            args = SysIterator()
        try:
            self._parse(args, is_last)
        except ValueError as e:
            if self._recover_help(args):
                self.exit_help()
            else:
                self.error_help(e)

    def add_argument(self, name, question, *, metavar=None):
        if isinstance(name, list) or name.startswith('-'):
            arg = OptionalArgument(name, question, metavar=metavar)
            self.optional_args.append(arg)
        else:
            arg = PositionalArgument(name, question, metavar=metavar)
            self.args.append(arg)

    def add_action(self, action):
        self.optional_args.append(action)

    def exit_help(self):
        print(self.formatter.short_info(self))
        raise SystemExit

    def error_help(self, error):
        print(self.formatter.error_info(self, error))
        raise SystemExit

    def print_help(self):
        print(self.help)

    def _recover_help(self, args):
        for arg in args:
            if arg in ('-h', '--help'):
                return True
        return False

    def _parse(self, args, is_last):
        index = 0
        while True:
            ele = args.peek()
            if ele is None:
                break
            if ele == '--':  # just ignore '--' steps
                args.inc
                continue
            if ele.startswith('-'):  # get optional
                for arg in self.optional_args:
                    if arg == ele:
                        args.inc
                        arg.consume(args)
                        break
                else:
                    raise ValueError(f"Cannot understand option {ele}")
            else:
                if index < len(self.args):
                    arg = self.args[index]
                    arg.consume(args)
                    index += 1
                else:
                    break
        #
        self._check_optionals()
        # clean up
        nchildren = len(self.children)
        #
        if nchildren == 0 and is_last:
            self._check_final(index, args)
        else:
            for i, child in enumerate(self.children, start=1):
                parser = child.consume(args)
                parser.parse(args=args, is_last=(i == nchildren))

    def _check_optionals(self):
        errors = self.optional_args.check_answers()
        if errors is None:
            return
        error = "\n".join(f"option '{name}': {error}"for name, error in errors.items())
        self.error_help(error)

    def _check_final(self, index, args):
        if index != len(self.args):
            self.error_help(Exception("Too few arguments"))
        if args.get_next() is not None:
            self.error_help(Exception("Too many arguments"))


class MainArgumentParser(ArgumentParser):

    def __init__(self, qform, *, name=None, formatter=None, parent=None, comment=None):
        super().__init__(name=name, formatter=formatter, parent=parent, comment=comment)
        self._qform = qform

    def get_answers(self, *, args=None, is_last=True):
        self.parse(args=args, is_last=is_last)
        return self._qform.get_answers()


class CommandlineParserVisitor(QuestionVisitor):
    """QuestionVisitor to create Commandline arguments"""

    __slots__ = ('parser', 'block_name', 'formatter', 'is_subblock')

    def __init__(self, formatter):
        """ """
        self.formatter = formatter
        self.parser = None
        self.block_name = None
        self.is_subblock = False

    def visit_qform(self, qform):
        """Create basic argument parser with `description` and RawTextHelpFormatter"""
        self.is_subblock = False
        parser = MainArgumentParser(qform, formatter=self.formatter)
        self.parser = parser
        # visit all forms
        qform.form.accept(self)
        # return the parser
        self.parser = None
        #
        return parser

    def visit_question_block(self, block):
        """visit all subquestion blocks"""
        with self.blockname_and_parser() as (block_name, parser):
            if self.is_subblock is False:
                self.block_name = join_keys(block_name, block.label)
            for question in block.concrete.values():
                if question.is_subquestion_main is False:
                    question.accept(self)
            #
            for subblock in block.blocks.values():
                self.is_subblock = False
                subblock.accept(self)

    def visit_concrete_question_select(self, question):
        """create a concrete parser and add it to the current parser"""
        self.select_and_add_concrete_to_parser(question)

    @contextmanager
    def blockname_and_parser(self):
        parser = self.parser
        block_name = self.block_name
        yield (block_name, parser)
        self.parser = parser
        self.block_name = block_name

    def select_and_add_concrete_to_parser(self, question, *, is_hidden=False):
        if question.has_only_one_choice is True:
            self.set_answer(question, question.choices[0])
        elif question.typ == 'bool':
            self.add_boolset_to_parser(question, is_hidden=is_hidden)
        else:
            self.add_concrete_to_parser(question, is_hidden=is_hidden)

    def add_boolset_to_parser(self, question, *, is_hidden=False):
        default, name = self._get_default_and_name(question)
        # do something with hidden variables!
        original = question.get_answer()
        if original is True:
            original = 'True'
            answer = 'False'
        else:
            answer = 'True'
            original = 'False'

        def change_value():
            question.answer = answer

        comment = f"Default={original}, if set value={answer}"

        if question.comment is not None:
            comment = f"{question.comment}; {comment}"

        action = EventAction(name, change_value, is_hidden=is_hidden, comment=comment)
        self.parser.add_action(action)

    def visit_concrete_question_input(self, question):
        """create a concrete parser and add it to the current parser"""
        self.add_concrete_to_parser(question)

    def visit_concrete_question_hidden(self, question):
        """create a concrete parser and add it to the current parser"""
        self.select_and_add_concrete_to_parser(question, is_hidden=True)

    def visit_literal_block(self, block):
        """do nothing when visiting literal blocks"""

    def visit_subquestion_block(self, block):
        """When visiting subquestion block create subparsers"""
        # create subparser
        # add subblocks
        with self.blockname_and_parser() as (block_name, parser):
            subparser = parser.add_subparser(block.main_question.name, block.main_question)
            for case, subblock in block.cases.items():
                self.block_name = None
                self.parser = subparser.add_parser(case, self.formatter, comment=subblock.comment)
                self.is_subblock = True
                subblock.accept(self)

    def add_concrete_to_parser(self, question, *, is_hidden=False):
        """adds a concrete question to the current active parser"""
        default, name = self._get_default_and_name(question)
        # do something with hidden variables!
        self.parser.add_argument(name, question)

    def _get_default_and_name(self, question):
        """get the name and default value for the current question"""
        # get id_name
        id_name = question.short_name
        #
        if self.block_name is not None:
            # remove block_name from the id
            id_name = join_keys(self.block_name, id_name)
        #
        default = question.default
        #
        if default in ('', None) and not question.is_optional:
            # default does not exist -> Positional Argument
            name = f"{id_name}"
            default = None
        else:
            # default exists -> Optional Argument
            if question.alias is not None:
                name = [f"--{id_name}", f"-{question.alias}"]
            else:
                name = f"--{id_name}"
        #
        return default, name


def get_commandline_parser(questions, *, formatter=None, description=None, presets=None):
    """Create the argparser from a given questions object and return the answers

    Parameters
    ----------
    questions: str or QuestionASTGenerator
        questions object to generate commandline arguments from

    description: str, optional
        description used for the argument parser

    presets: str, optional
        presets used for the questions form

    Returns
    -------
    AnswersBlock
        User input
    """
    # Visitor object
    if formatter is None:
        formatter = HelpFormatter(settings=description)
    visitor = CommandlineParserVisitor(formatter)
    #
    qform = QuestionForm(questions, presets=presets)
    #
    return visitor.visit(qform)


def get_config_from_commandline(questions, *, formatter=None,
                                only_print_help=False,
                                description=None,
                                presets=None):
    """Create the argparser from a given questions object and return the answers

    Parameters
    ----------
    questions: str or QuestionASTGenerator
        questions object to generate commandline arguments from

    description: str, optional
        description used for the argument parser

    presets: str, optional
        presets used for the questions form

    Returns
    -------
    AnswersBlock
        User input
    """
    # Visitor object
    parser = get_commandline_parser(questions, formatter=formatter,
                                    description=description, presets=presets)
    # parse commandline args
    return parser.get_answers()
