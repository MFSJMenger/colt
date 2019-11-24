from collections import namedtuple
from .answers import SubquestionsAnswer
from .context_utils import ExitOnException
from .parser import LineParser
from .generator import GeneratorBase
from abc import ABC, abstractmethod


Question = namedtuple("Question", ("question", "typ", "default", "choices", "comment"),
                      defaults=("", "str", None, None, None))


class ConditionalQuestion:

    def __init__(self, name, main, subquestions):
        self.name = name
        self.main = main
        self.subquestions = subquestions

    def get(self, key, default=None):
        return self.subquestions.get(key, default)

    def items(self):
        return self.subquestions.items()

    def keys(self):
        return self.subquestions.keys()

    def __getitem__(self, key):
        return self.subquestions[key]

    def __setitem__(self, key, value):
        self.subquestions[key] = value

    def __contains__(self, key):
        return key in self.subquestions

    def __str__(self):
        return (f"ConditionalQuestion(name = {self.name},"
                f" main = {self.main}, subquestions = {self.subquestions}")

    def __repr__(self):
        return (f"ConditionalQuestion(name = {self.name},"
                f" main = {self.main}, subquestions = {self.subquestions}")


class QuestionGenerator(GeneratorBase):
    """Contains all tools to automatically generate questions from
       a given file
    """

    comment_char = "###"
    default = '__QUESTIONS__'
    _allowed_choices_types = ['int', 'str', 'float', 'bool']
    # for tree generator
    leafnode_type = Question
    branching_type = ConditionalQuestion
    node_type = dict

    LeafString = namedtuple("LeafString", ("default", "typ", "choices", "question"),
                            defaults=(None, "str", None, None))

    def __init__(self, questions):
        """Main Object to generate questions from string

        Args:
            questions:  Questions object, can
                        1) Question Object, just save questions
                        2) file, read file and parse input

        Kwargs:
            isfile (bool): True, `questions` is a file
                           False, `questions` is a string

        """
        # if is questions
        if self.is_question(questions):
            self.questions = questions
            return
        #
        self.questions = self.configstring_to_tree(questions)

    @classmethod
    def new_branching(cls, name, leaf=None):
        """Create a new empty branching"""
        if leaf is None:
            return ConditionalQuestion(name, Question(name), {})
        return ConditionalQuestion(name, leaf, {})

    @staticmethod
    def _preprocess_string(string):
        """Basic Preprocessor to handle in file comments!"""

        parsed_string = []
        comment_lines = []
        for line in string.splitlines():
            line = line.strip()
            if line == "":
                continue
            if line.startswith('#'):
                comment_lines.append(line[1:])
                continue
            if comment_lines != []:
                line += "###" + "#n".join(comment_lines)
                comment_lines = []
            parsed_string.append(line)
        return "\n".join(parsed_string)

    @classmethod
    def leaf_from_string(cls, name, value):
        """Create a leaf from an entry in the config file

        Args:
            name (str):
                name of the entry

            value (str):
                value of the entry in the config

        Returns:
            A leaf node

        Raises:
            ValueError:
                If the value cannot be parsed
        """
        original_value = value
        # handle comment
        value, comment = cls._parse_comment(value)
        # try to parse line
        try:
            value = cls.LeafString(*(ele.strip() for ele in value.split(cls.seperator)))
        except TypeError:
            raise Exception(f"Cannot parse value `{original_value}`")
        # get default
        default = cls._parse_default(value.default)
        # get question
        if value.question is None:
            question = name
        else:
            question = value.question
        # get choices
        choices = cls._parse_choices(value.typ, value.choices)
        # return leaf node
        return Question(question, value.typ, default, choices, comment)

    def get_block(self, block=None):
        if block is not None:
            return self.get_node(self.questions, block)
        else:
            return self.questions

    def generate_cases(self, key, subquestions, block=None):
        """Register `subquestions` at a given `key` in given `block`

        Args:
            key (str): name of the variable that should be overwritten as a subquestion

            subquestions (dict): Dict of Questions corresponding to the subquestions
                                 one wants to register

        Kwargs:
            block (str):  The name of the block, the given `key` is in

        Example:
            >>> _question = "sampling = "
            >>> questions.generate_cases("sampling", {name: sampling.questions for name, sampling
                                                      in cls._sampling_methods.items()})
        """
        questions = self.get_block(block)
        #
        subblocks = {name: QuestionGenerator(value).questions
                     for name, value in subquestions.items()}
        #
        if questions is None:
            raise KeyError(f"block '{block}' unknown")

        if questions.get(key, None) is None:
            questions[key] = ConditionalQuestion(key, Question(key), subblocks)
        elif isinstance(questions[key], ConditionalQuestion):
            for name, item in subblocks.items():
                questions[key][name] = item
        elif isinstance(questions[key], Question):
            questions[key] = ConditionalQuestion(key, questions[key], subblocks)
        else:
            raise ValueError(f"Argument {questions[key]} can only be "
                             f"None, Questions, ConditionalQuestion")

    def add_questions_to_block(self, questions, block=None, overwrite=True):
        """add questions to a particular block """
        block_questions = self.get_block(block)
        if block_questions is None:
            raise KeyError(f"block {block} unknown")

        if not isinstance(block_questions, self.node_type):
            raise ValueError(f"block questions {block} should be of type {self.node_type}!")

        if not self.is_question(questions):  # assume is string!
            questions = self.configstring_to_tree(questions)
        # just update the dict
        if overwrite is True:
            block_questions.update(questions)
            return
        # overwrite it
        for key, item in questions.items():
            if key not in block_questions:
                block_questions[key] = item

    def generate_block(self, name, questions, block=None):
        """Register `questions` at a given `key` in given `block`

        Args:
            name (str):
                name of the block

            questions (string, tree):
                questions of the block

        Kwargs:
            block (str):  The name of the block, the given `key` is in

        Raises:
            ValueError: If the `key` in `block` already exist it raises an ValueError,
                        blocks can only be new created, and cannot overwrite existing
                        blocks!

        Example:
            >>> _question = "sampling = "
            >>> questions.generate_block("software", {name: software.questions for name, software
                                                      in cls._softwares.items()})
        """

        block_questions = self.get_block(block)
        if block_questions is None:
            raise KeyError(f"block {block} unknown")

        subblocks = QuestionGenerator(questions).questions

        if block_questions.get(name) is None:
            block_questions[name] = subblocks
        else:
            raise ValueError(f"{name} in [{block}] should not be given")

    def is_question(self, questions):
        """Check if a given obj counts as a Question Object

        Args:
            questions: QuestionObject, can be
                    1) dict
                    2) Question
                    3) ConditionalQuestion

        Returns:
            True: if quesition is QuestionObject
            False: otherwise

        """
        if isinstance(questions, dict):
            return True
        if isinstance(questions, Question):
            return True
        if isinstance(questions, ConditionalQuestion):
            return True
        return False

    @classmethod
    def questions_from_file(cls, filename):
        with open(filename, "r") as f:
            string = f.read()
        return cls(string)

    @staticmethod
    def _parse_default(default):
        """Handle default value"""
        if default.lower() == 'none' or default == "":
            return None
        return default

    @classmethod
    def _parse_comment(cls, line):
        """Handle Comment section"""
        line, _, comment = line.partition(cls.comment_char)
        if comment == "":
            comment = None
        else:
            comment = comment.replace("#n", "\n")
        return line, comment

    @classmethod
    def _parse_choices(cls, typ, line):
        """Handle choices"""
        if line == "":
            return None
        if line is None:
            return None
        if typ not in cls._allowed_choices_types:
            return None
        line = line.replace("[", "").replace("]", "")
        return [choice.strip() for choice in line.split(",")]


def register_parser(key, function):
    """register a parser for the Questions class

       The parser function needs to take  a single
       argument which is a string and return a
       single python object, which should not be a
       **dict**!
    """
    _ConcreteQuestion.register_parser(key, function)


class _QuestionBase(ABC):

    def __init__(self, parent):
        self._set_answer = None
        self.parent = parent

    @abstractmethod
    def set_answer(self, value):
        pass

    @abstractmethod
    def _ask(self):
        """Actual ask routine"""
        pass

    def ask(self):
        """User interface, returns Answer"""
        return self._ask()


class _ConcreteQuestion(_QuestionBase):

    _known_parsers = {
                      'str': str,
                      'float': float,
                      'int': int,
                      'bool': LineParser.bool_parser,
                      'list': LineParser.list_parser,
                      'ilist': LineParser.ilist_parser,
                      'ilist_np': LineParser.ilist_np_parser,
                      'flist': LineParser.flist_parser,
                      'flist_np': LineParser.flist_np_parser,
    }

    def __init__(self, question, parent=None):
        # setup
        _QuestionBase.__init__(self, parent)
        self._parse = self._select_parser(question.typ)
        self._setup(question)
        # generate the question
        self.question = self._generate_question(question)

    def __repr__(self):
        return f"{self.question}\n"

    def __str__(self):
        return f"{self.question}\n"

    def set_answer(self, value: str):
        """set the answer to a suitable value, also here parse is called!
           only consistent inputs values are accepted
        """

        if value.strip() == "":
            return
        # also kinda useless, as the question is never ask, but conceptionally correct ;)
        self._accept_enter = True
        # this is kinda a hack to ensure that the provided config
        # file is correct,
        with ExitOnException():
            self._set_answer = self._parse(str(value))

    def _generate_question(self, question):
        txt = question.question.strip()
        # add default option
        if question.default is not None:
            txt += " [%s]" % (str(self.default))
        if question.choices is not None:
            txt += ", choices = (%s)" % (", ".join(question.choices))
        return txt + ": "

    def set_choices(self, choices):
        try:
            self._choices = [self._parse(choice) for choice in choices]
        except:
            pass

    def _setup(self, question):
        self._default = None
        self._accept_enter = False
        self._comment = question.comment
        # Try to set choices
        try:
            self._choices = [self._parse(choice) for choice in question.choices]
        except:
            self._choices = None

        if question.default is not None:
            self._accept_enter = True
            try:
                self._default = self._parse(question.default)
                return
            except Exception as e:
                print(e)
            # either already returned, or raise exception!
            raise Exception(f"For parser '{question.typ}' "
                            f"default '{question.default}' cannot be used!")

    def _print(self):
        return f"{self.question}\n"

    @property
    def default(self):
        """if answer is set, return set answer, alse return default"""
        if self._set_answer is not None:
            return self._set_answer
        return self._default

    def _ask_question(self):
        """Helper routine which asks the actual question"""
        is_set = False
        answer = input(self.question).strip()  # strip is important!
        if answer == "":
            if self._accept_enter:
                answer = self.default
                is_set = True
        #
        return _Answer(answer, is_set)

    def _perform_questions(self):
        answer = self._ask_question()
        # pass just default!
        if answer.is_set:
            return answer
        #
        if any(answer.value == helper for helper in (":help", ":h")):
            print(self._comment)
            # reask
            answer = self._perform_questions()
        return answer

    def _ask_implementation(self):
        """Helper routine that checks if an answer is set,
           else, tries to parse the answer, if that fails
           the question is ask again
        """
        #
        if self._set_answer is not None:
            return self._set_answer
        #
        answer = self._perform_questions()

        if answer.is_set is True:
            # if answer is set, return unparsed answer
            return answer.value
        #
        try:
            if answer.value == "":
                raise Exception("No default set, empty string not allowed!")
            result = self._parse(answer.value)
        except Exception:
            print(f"Unknown input '{answer.value}', redo")
            # reask
            result = self._ask_implementation()

        if self._choices is not None:
            if result not in self._choices:
                print(f"answer({result}) has to be ({', '.join(self._choices)})")
                # reask
                result = self._ask_implementation()
        return result

    def _check_only(self):
        """Check if the answer is set, or a default is
           available, if not notify parent and return
           "NEEDS_TO_BE_SET"
        """
        if self._set_answer is not None:
            return self._set_answer
        elif self.default is not None:
            return self.default
        else:
            if self.parent is not None:
                self.parent._check_failed = True
            return "NEEDS_TO_BE_SET"

    def _ask(self):
        if self.parent is not None:
            if self.parent.only_check is True:
                return self._check_only()
        return self._ask_implementation()

    def _select_parser(self, key):
        parser = self._known_parsers.get(key, None)
        if parser is None:
            raise Exception(f"Parser '{key}' is unknown, please register before usage")
        return parser

    @classmethod
    def register_parser(cls, key, value):
        if not callable(value):
            raise TypeError("Parser needs to be a single argument function!")
        cls._known_parsers[key] = value

    @classmethod
    def get_parsers(cls):
        return cls._known_parsers


# Used to save status of a concrete answer
_Answer = namedtuple("_Answer", ("value", "is_set"))


class _Questions(_QuestionBase):

    def __init__(self, questions, parent=None):
        _QuestionBase.__init__(self, parent)
        self.questions = {name: parse_question(question, parent=self.parent)
                          for (name, question) in questions.items()}

    def items(self):
        return self.questions.items()

    def __getitem__(self, key):
        return self.questions.get(key, None)

    def get(self, key, default=None):
        return self.questions.get(key, None)

    def __contains__(self, key):
        return key in self.questions

    def set_answer(self, value):
        raise Exception("For _Questions class no set_answer is possible at the moment!")

    def _print(self):
        string = ""
        for name, question in self.questions.items():
            string += f"{name}: {question._print()}\n"
        return string

    def _ask(self):
        answers = {}
        for name, question in self.questions.items():
            answers[name] = question._ask()
        return answers


class _Subquestions(_QuestionBase):

    def __init__(self, name, main_question, questions, parent=None):
        _QuestionBase.__init__(self, parent)
        # main question
        self.name = name
        # subquestions
        self.subquestions = {name: parse_question(question, parent=self.parent)
                             for name, question in questions.items()}
        main_question = Question(question=main_question.question, typ=main_question.typ,
                                 default=main_question.default,
                                 choices=self.subquestions.keys(),
                                 comment=main_question.comment)
        self.main_question = _ConcreteQuestion(main_question, parent=self.parent)

    def __getitem__(self, key):
        return self.subquestions.get(key, None)

    def get(self, key, default=None):
        return self.subquestions.get(key, None)

    def __contains__(self, key):
        return key in self.subquestions

    def set_answer(self, value):
        """set answer for main question"""
        self.main_question.set_answer(value)

    def _print(self):
        string = f"{self.main_question}\n"
        for name, question in self.subquestions.items():
            string += f"{name}: {question._print()}\n"
        return string

    def _ask(self):
        main_answer = self.main_question._ask()
        subquestion = self.subquestions.get(main_answer, None)
        if subquestion is None:
            return main_answer
        else:
            return SubquestionsAnswer(self.name, main_answer, subquestion._ask())


def parse_question(question, parent=None):

    if isinstance(question, dict):
        result = _Questions(question, parent=parent)
    elif isinstance(question, Question):
        result = _ConcreteQuestion(question, parent=parent)
    elif isinstance(question, ConditionalQuestion):
        result = _Subquestions(question.name, question.main, question.subquestions, parent=parent)
    else:
        raise TypeError("Type of question not known!", question)
    return result
