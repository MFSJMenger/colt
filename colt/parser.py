import sys

from .qform import QuestionForm, QuestionVisitor, join_case
from .qform import ValidatorErrorNotInChoices


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

    def __init__(self, name, question, nargs=None, metavar=None, typ=None, help=None):
        self.question = question
        self.is_optional, self.fullname, self.metavar = self._check(name, metavar)
        if nargs is None:
            if question.is_list is True:
                nargs = '+'
            else:
                nargs = 1
        self.nargs = NumberOfArguments(nargs, self.is_optional)
        self.typ = typ
        self.help = help

    def __repr__(self):
        return f"Argument({self.fullname}, {self.metavar})"


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
                value = args.get_arg() # ignores --, -value
                if value is None:
                    if len(result) == 0 and self.nargs == '?':
                        raise ValueError(f"Too few arguments for {self.fullname} expected at least one value")
                    break
                result.append(value)
        # set value
        if self.question.is_list is True:
            self.question.answer = result
        else:
            self.question.answer = result[0]

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
    typ = "show this help message and exit"
    return f"  {name:12s}  {typ:12s}\n" 


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


class SubParser:

    def __init__(self, name, question, parent, children=None):
        if children is None:
            children = {}
        self._question = question
        self._options =  {}
        self.name = name
        self._parent = parent

    def consume(self, args):
        value = args.get_arg() # ignores --, -value
        if value is None:
            raise ValueError("Two few arguments")
        self._question.answer = value
        parser = self._options.get(value, None)
        if parser is None:
            raise ValueError(f"parser needs to be in {', '.join(child for child in self._options)}")
        return parser

    def add_parser(self, name):
        parser = ArgumentParser(parent=self._parent)
        self._options[name] = parser
        return parser


class EventArgument(Argument):

    def __init__(self, name, question, event_call, metavar=None, help=None):
        # set nargs 
        super().__init__(name, question, nargs=0, metavar=metavar, help=help)
        self._call = event_call

    def consume(self, args):
        self._call()


def get_help(parser):

    def _help():
        parser.print_help()
        sys.exit()

    return EventArgument(["-h", "--help"], None, _help, metavar="help") 


class ArgumentParser:

    def __init__(self, parent=None):
        self.optional_args = [get_help(self)]
        self.args = []
        self.parent = parent
        self.children = []

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
                self.print_help()
                print(e)
                raise SystemExit from None

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
            if ele == '--': # just ignore '--' steps 
                args.inc
                continue 
            if ele.startswith('-'): # get optional
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

    def add_argument(self, name, question, nargs=None, metavar=None, typ=None, help=None):
        arg = Argument(name, question, metavar=metavar, nargs=None, typ=typ, help=help)
        if arg.is_optional:
            self.optional_args.append(arg)
        else:
            self.args.append(arg)

    def exit_help(self):
        self.print_help()
        raise SystemExit

    def print_help(self):
        print(get_short_help("parser", self.args, self.optional_args))
        print()
        print(position_args_help(self.args))
        print()
        print(optional_args_help(self.optional_args))


class CommandlineParserVisitor(QuestionVisitor):
    """QuestionVisitor to create Commandline arguments"""

    __slots__ = ('parser', 'block_name')

    def __init__(self):
        """ """
        self.parser = None
        self.block_name = None

    def visit_qform(self, qform, description=None):
        """Create basic argument parser with `description` and RawTextHelpFormatter"""
        parser = ArgumentParser()
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
        if question.has_only_one_choice is True:
            self.set_answer(question, question.choices[0])
        else:
            self.add_concrete_to_parser(question)

    def visit_concrete_question_input(self, question):
        """create a concrete parser and add it to the current parser"""
        self.add_concrete_to_parser(question)

    def visit_concrete_question_hidden(self, question):
        """create a concrete parser and add it to the current parser"""
        self.add_concrete_to_parser(question, is_hidden=True)

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
            self.parser = subparser.add_parser(case)
            subblock.accept(self)
        # restore old parser 
        self.parser = parser
        # restore blockname
        self.block_name = block_name

    def add_concrete_to_parser(self, question, is_hidden=False):
        """adds a concrete question to the current active parser"""
        default, name = self._get_default_and_name(question)
        #
        if is_hidden is True:
            comment = ''
        else:
            comment = self.get_comment(question)
        #
        self.parser.add_argument(name, question, metavar=question.label, help=comment)

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
            name = f"-{id_name}"
        #
        return default, name

    @staticmethod
    def get_comment(question):
        """get the comment string"""
        choices = question.choices
        if choices is None:
            choices = ''
        #
        comment = f"{question.typ}, {choices}"
        if question.comment is not None:
            comment += f"\n{question.comment}"
        #
        return comment


def get_config_from_commandline(questions, description=None, presets=None):
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
    visitor = CommandlineParserVisitor()
    #
    qform = QuestionForm(questions, presets=presets)
    #
    parser = visitor.visit(qform, description=description)
    # parse commandline args
    parser.parse()
    #
    return qform.get_answers()
