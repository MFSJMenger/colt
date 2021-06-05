import sys

from collections import namedtuple

from .qform import QuestionForm, QuestionVisitor, join_case

EmptyQuestion = namedtuple("EmptyQuestion", ("typ", "comment", "is_hidden"))


class FullName:

    def __init__(self, value):
        if isinstance(value, str):
            self._value = (value.strip(), )
        elif isinstance(value, (list, tuple)):
            if len(value) > 2:
                raise ValueError("Can maximum have two entries")
            self._value = tuple(val.strip() for val in value)
        else:
            raise ValueError("Value can only be set/list/tuple or string")

    def __eq__(self, value):
        return value in self._value

    def __str__(self):
        if len(self._value) == 1:
            return f"{self._value[0]}"
        else:
            return f"{self._value[0]}/{self._value[1]}"

    @property
    def small(self):
        if len(self._value) == 1:
            return self._value[0]
        if len(self._value[0]) > len(self._value[1]):
            return self._value[1]
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

    def __init__(self, question):
        self.question = question

    @property
    def typ(self):
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

    def __init__(self, name, question, metavar=None):
        super().__init__(question)
        _, self.fullname, self.metavar = check_names(name, metavar)
        if question.is_list is True:
            nargs = question.validator.nele
        else:
            nargs = 1
        self.nargs = NumberOfArguments(nargs)

    def __eq__(self, value):
        return self.fullname == value

    @property
    def is_finite(self):
        return self.nargs.is_finite

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
        if self.question.is_list is True:
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

    @property
    def name(self):
        return self.fullname

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


def format(name, question):
    if question.comment is None:
        comment = [""]
    else:
        comment = question.comment.splitlines()
    out = f"  {name:12s}  {question.typ:12s} {comment[0]}\n"
    space = " " * 28
    for line in comment[1:]:
        out += f"{space} {line}\n"
    return out


def format_help():
    name = "-h/--help"
    typ = ""
    comment = "show this help message and exit"
    return f"  {name:12s}  {typ:12s} {comment}\n"


def position_args_help(args, format=format):
    out = f"  positional arguments:\n {DELIM}\n"
    for arg in args:
        out += format(arg.metavar, arg.question)
    return out


def optional_args_help(args, format=format):
    out = f"  optional arguments:\n {DELIM}\n"
    for arg in args:
        if arg == '-h':
            out += format_help()
        else:
            out += format(str(arg.fullname), arg.question)
    return out


Element = namedtuple('Element', ('lines', 'format', 'nlines'))


class ArgFormatter:

    def __init__(self, format):
        self._formatter = format
        self.shift = self._formatter.pop('shift', '')
        self.space = self._formatter.pop('space', ' ')
        if isinstance(self.space, int):
            self.space = ' ' * self.space
        if isinstance(self.shift, int):
            self.shift = ' ' * self.shift
        #

    def format(self, arg):
        return self._format_arg(arg)

    def _get_lines(self, string, length):
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
            if name == 'space':
                continue
            res, nlines = self._get_lines(str(getattr(arg, name)), length)
            if nlines > nlen:
                nlen = nlines
            out[name] = Element(res, f"%-{length}s", nlines)
        return self._format_string(out, nlen)

    def _format_string(self, data, nlen):
        out = ""
        for i in range(nlen):
            out += f"{self.shift}"
            for value in data.values():
                if i < value.nlines:
                    out += value.format % value.lines[i]
                else:
                    out += value.format % ""
                out += self.space
            out += "\n"
        return out


class HelpStringBlock:

    def __init__(self, block_space, space):
        self._string = None
        self.block_space = block_space
        self.space = space
        self._last_was_space = False

    def add(self, name, block):
        if block is None:
            return
        if self._string is None:
            self._string = block
            return
        if self._last_was_space is False and name != 'space':
            self._string += self.block_space
        self._string += block
        if name == 'space':
            self._last_was_space = True

    def __str__(self):
        return self._string


class HelpFormatter:

    blocks = ('usage', 'space', 'opt_args', 'pos_args', 'logo', 'description', 'error')

    def __init__(self, logo=None, description=None, block_space="\n\n\n", space="\n",
                 main_order=None, error_order=None, short_order=None, arg_formater=None):
        if error_order is None:
            error_order = ['usage', 'error']
        if main_order is None:
            main_order = ['logo', 'description', 'pos_args', 'opt_args', 'usage', 'space']
        if short_order is None:
            short_order = ['usage', ]
        if arg_formater is not None:
            if not isinstance(arg_formater, dict):
                raise ValueError("argument format can only be dict")
            arg_formater = ArgFormatter(arg_formater)
        else:
            arg_formater = ArgFormatter({
                    'name': 12,
                    'comment': 40,
                    'typ': 12,     # maximale breite
                    'space': 2,
                    'shift': 4,
                    })
        # normal space
        self.space = space
        # block spaces
        self.block_space = block_space
        # how to format a line
        self.arg_formater = arg_formater
        #
        self.error_order = error_order
        #
        self.main_order = main_order
        #
        self.short_order = short_order
        #
        self.logo = logo
        #
        self.description = description
        #
        self.error = None

    def _logo(self):
        return self.logo

    def _description(self):
        return self.description

    def _error(self):
        return f"error: {self.error}"

    def _opt_args(self, parser):
        out = f"  optional arguments:\n {DELIM}\n"
        out += "".join(self._format_arg(arg)
                       for arg in parser.optional_args
                       if not arg.is_hidden)

        return out

    def _pos_args(self, parser):
        if len(parser.args) == 0 and len(parser.children) == 0:
            return None
        out = f"  positional arguments:\n {DELIM}\n"
        out += "".join(self._format_arg(arg)
                       for arg in parser.args)
        out += "".join(self._format_arg(arg)
                       for arg in parser.children)
        return out

    def _usage(self, parser):
        name = sys.argv[0]

        nargs = len(parser.args)
        #
        out = " ".join(arg.to_commandline_str(i < nargs)
                       for i, arg in enumerate(parser.args, start=1))
        subparser = " ".join(arg.to_commandline_str()
                             for arg in parser.children)
        opts = " ".join(surround(arg.to_commandline_str(False))
                        for arg in parser.optional_args
                        if not arg.is_hidden)

        return f"usage: {name} {opts} {out} {subparser}"

    def _do_task(self, task, parser):
        if task == 'pos_args':
            return self._pos_args(parser)
        if task == 'opt_args':
            return self._opt_args(parser)
        if task == 'usage':
            return self._usage(parser)
        if task == 'logo':
            return self._logo()
        if task == 'description':
            return self._description()
        if task == 'error':
            return self._error()
        if task == 'space':
            return self.space
        raise ValueError(f"Task '{task}' unknown")

    def info(self, parser):
        return self._render(self.main_order, parser)

    def short_info(self, parser):
        return self._render(self.short_order, parser)

    def error_info(self, parser, error):
        self.error = str(error)
        return self._render(self.error_order, parser)

    def _render(self, blocks, parser):
        string = HelpStringBlock(self.block_space, self.space)
        for task in blocks:
            string.add(task, self._do_task(task, parser))
        return str(string)

    def _format_arg(self, arg):
        return self.arg_formater.format(arg)

    def _check(self, order):
        if any(ele not in self.blocks for ele in order):
            raise Exception("Could not understand block")
        return order


class EventAction(Action):

    def __init__(self, name, function, is_hidden=False, comment=None):
        super().__init__(EmptyQuestion('action', comment, is_hidden))
        self._fun = function
        self.fullname = FullName(name)

    @property
    def name(self):
        return str(self.fullname)

    def to_commandline_str(self, *args):
        return str(self.fullname.small)

    def consume(self, args):
        # execute action
        self._fun()

    def __eq__(self, value):
        return self.fullname == value


class SubParser(Action):

    def __init__(self, name, question, parent):
        super().__init__(question)
        self._options = {}
        self.name = name
        self._parent = parent

    def to_commandline_str(self):
        return f"{self.name} ..."

    def consume(self, args):
        value = args.get_arg()  # ignores --, -value
        if value is None:
            raise ValueError("Two few arguments")
        self.question.answer = value
        parser = self._options.get(value, None)
        if parser is None:
            raise ValueError(f"parser needs to be in {', '.join(child for child in self._options)}")
        return parser

    def add_parser(self, name, formatter):
        parser = ArgumentParser(formatter, parent=self._parent)
        self._options[name] = parser
        return parser


def get_help(parser):
    """Closure to get exit to the print_help function of the parser"""

    def _help():
        parser.print_help()
        sys.exit()

    return EventAction(["-h", "--help"], _help, comment="show this help message and exit")


class ArgumentParser:

    def __init__(self, formatter=None, parent=None):
        self.optional_args = [get_help(self)]
        self.args = []
        self.parent = parent
        self.children = []
        self.formatter = formatter

    def add_subparser(self, name, question):
        child = SubParser(name, question, parent=self)
        self.children.append(child)
        return child

    def parse(self, args=None, is_last=True):
        if args is None:
            args = SysIterator()
        try:
            self._parse(args, is_last)
        except ValueError as e:
            if self._recover_help(args):
                self.exit_help()
            else:
                self.error_help(e)

    def add_argument(self, name, question, metavar=None):
        if name.startswith('-'):
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
        print(self.formatter.info(self))

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
        # clean up
        nchildren = len(self.children)
        #
        if nchildren == 0 and is_last:
            self._check_final(index, args)
        else:
            for i, child in enumerate(self.children, start=1):
                parser = child.consume(args)
                parser.parse(args=args, is_last=(i == nchildren))

    def _check_final(self, index, args):
        if index != len(self.args):
            raise Exception("Too few arguments")
        if args.get_next() is not None:
            raise Exception("Too many arguments")


class CommandlineParserVisitor(QuestionVisitor):
    """QuestionVisitor to create Commandline arguments"""

    __slots__ = ('parser', 'block_name', 'formatter')

    def __init__(self, formatter):
        """ """
        self.formatter = formatter
        self.parser = None
        self.block_name = None

    def visit_qform(self, qform):
        """Create basic argument parser with `description` and RawTextHelpFormatter"""
        parser = ArgumentParser(formatter=self.formatter)
        self.parser = parser
        # visit all forms
        qform.form.accept(self)
        # return the parser
        self.parser = None
        #
        return parser

    def visit_question_block(self, block):
        """visit all subquestion blocks"""
        for question in block.concrete.values():
            if question.is_subquestion_main is False:
                question.accept(self)
        #
        for subblock in block.blocks.values():
            subblock.accept(self)

    def visit_concrete_question_select(self, question):
        """create a concrete parser and add it to the current parser"""
        self.select_and_add_concrete_to_parser(question)

    def select_and_add_concrete_to_parser(self, question, is_hidden=False):
        if question.has_only_one_choice is True:
            self.set_answer(question, question.choices[0])
        elif question.typ == 'bool':
            self.add_boolset_to_parser(question, is_hidden=is_hidden)
        else:
            self.add_concrete_to_parser(question, is_hidden=is_hidden)

    def add_boolset_to_parser(self, question, is_hidden=False):
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
        # save ref to current parsser
        parser = self.parser
        block_name = self.block_name
        # create subparser
        subparser = parser.add_subparser(block.main_question.name, block.main_question)
        # add subblocks
        for case, subblock in block.cases.items():
            self.block_name = join_case(block.main_question.name, case)
            self.parser = subparser.add_parser(case, self.formatter)
            subblock.accept(self)
        # restore old parser
        self.parser = parser
        # restore blockname
        self.block_name = block_name

    def add_concrete_to_parser(self, question, is_hidden=False):
        """adds a concrete question to the current active parser"""
        default, name = self._get_default_and_name(question)
        # do something with hidden variables!
        self.parser.add_argument(name, question, metavar=question.label)

    def _get_default_and_name(self, question):
        """get the name and default value for the current question"""
        # get id_name
        id_name = question.id
        #
        if self.block_name is not None:
            # remove block_name from the id
            id_name = id_name.replace(self.block_name, '')
            if id_name[:2] == '::':
                id_name = id_name[2:]
        #
        default = question.answer
        #
        if default in ('', None) and not question.is_optional:
            # default does not exist -> Positional Argument
            name = f"{id_name}"
            default = None
        else:
            # default exists -> Optional Argument
            name = f"--{id_name}"
        #
        return default, name


def get_config_from_commandline(questions, formatter=None,
                                logo=None, description=None, presets=None):
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
        formatter = HelpFormatter(logo=logo, description=description)
    visitor = CommandlineParserVisitor(formatter)
    #
    qform = QuestionForm(questions, presets=presets)
    #
    parser = visitor.visit(qform)
    # parse commandline args
    parser.parse()
    #
    return qform.get_answers()
