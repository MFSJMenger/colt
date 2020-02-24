"""Definitions of all Question Classes"""
from abc import ABC, abstractmethod
from collections import namedtuple
from collections.abc import MutableMapping
#
from .answers import SubquestionsAnswer
from .generator import GeneratorBase, BranchingNode
#
from .parser import Validator, NOT_DEFINED


class WrongChoiceError(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


# store Questions
Question = namedtuple("Question", ("question", "typ", "default", "choices", "comment"),
                      defaults=("", "str", NOT_DEFINED, None, None))


# identify literal blocks
LiteralBlock = namedtuple("LiteralBlock", ("name"))


class ConditionalQuestion(BranchingNode):  # pylint: disable=too-many-ancestors
    """Conditional Question, is a branching node
       used to store decissions
    """

    def __init__(self, name, main, subquestions):
        super().__init__(name, main, subquestions)
        self.main = self.leaf
        self.subquestions = self.subnodes

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
        if isinstance(questions, QuestionGenerator):
            self.literals = questions.literals
        elif isinstance(questions, str):
            self.literals = {}
        else:
            raise TypeError("Generator only accepts type string!")
        GeneratorBase.__init__(self, questions)
        #
        self.questions = self.tree

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

    def leaf_from_string(self, name, value, parent=None):
        """Create a leaf from an entry in the config file

        Args:
            name (str):
                name of the entry

            value (str):
                value of the entry in the config

        Kwargs:
            parent (str):
                identifier of the parent node

        Returns:
            A leaf node

        Raises:
            ValueError:
                If the value cannot be parsed
        """
        original_value = value
        # handle comment
        value, comment = self._parse_comment(value)
        # try to parse line
        try:
            value = self.LeafString(*(ele.strip() for ele in value.split(self.seperator)))
        except TypeError:
            raise ValueError(f"Cannot parse value `{original_value}`") from None
        # check for literal block
        if value.typ == 'literal':
            name = self._join_keys(parent, name)
            self.literals[name] = None
            return LiteralBlock(name)
        # get default
        default = self._parse_default(value.default)
        # get question
        if value.question is None:
            question = name
        else:
            question = value.question
        # get choices
        choices = self._parse_choices(value.typ, value.choices)
        # return leaf node
        return Question(question, value.typ, default, choices, comment)

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
        self.add_branching(key, subquestions, parentnode=block)

    def add_questions_to_block(self, questions, block=None, overwrite=True):
        """add questions to a particular block """
        self.add_elements(questions, parentnode=block, overwrite=overwrite)

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
        self.add_node(name, questions, parentnode=block)

    @classmethod
    def questions_from_file(cls, filename):
        """generate questions from file"""
        with open(filename, "r") as fhandle:
            string = fhandle.read()
        return cls(string)

    @staticmethod
    def _parse_default(default):
        """Handle default value"""
        if default == 'NOT_DEFINED' or default == "":
            return NOT_DEFINED
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
    Validator.register_parser(key, function)


class _QuestionBase(ABC):

    def __init__(self, parent):
        self._set_answer = None
        self.parent = parent

    @abstractmethod
    def set_answer(self, value):
        """set an answer"""

    @abstractmethod
    def _ask(self):
        """Actual ask routine"""

    def ask(self):
        """User interface, returns Answer"""
        return self._ask()


class _LiteralBlock(_QuestionBase):
    """parse literal blocks"""

    def __init__(self, literal, parent):
        _QuestionBase.__init__(self, parent)
        self.name = literal.name

    def set_answer(self, value):
        """answer"""
        raise NotImplementedError("set_answer not supported for literalblock")

    def _ask(self):
        if self.parent is not None:
            return self.parent.literals.get(self.name, None)
        return None


class _ConcreteQuestion(_QuestionBase):

    def __init__(self, question, parent=None):
        # setup
        _QuestionBase.__init__(self, parent)
        #
        self._value = Validator(question.typ, default=question.default,
                                choices=question.choices)
        #
        self._accept_enter = True
        self._answer_set = False
        self._comment = question.comment
        self.question = question.question
        self.typ = question.typ
        #
        self._setup(question)
        # generate the question
        self.question = self._generate_question(question)

    def _ask(self):
        if self.parent is None or self.parent.only_checking is False:
            self._ask_implementation()
        return self._answer

    def _perform_questions(self):
        answer = self._ask_question()
        # return set answer!
        if answer.is_set:
            return answer
        #
        if any(answer.value == helper for helper in (":help", ":h")):
            print(self._comment)
            # re-ask
            answer = self._perform_questions()
        return answer

    def _ask_implementation(self):
        """Helper routine that checks if an answer is set,
           else, tries to parse the answer, if that fails
           the question is ask again
        """
        #
        if self._answer_set is True:
            return self._answer
        #
        answer = self._perform_questions()

        if answer.is_set is True:
            # if answer is set, return unparsed answer
            return answer.value
        #
        try:
            if answer.value == "":
                raise ValueError("No default set, empty string not allowed!")
            self._answer = answer.value
            return self._answer
        except ValueError:
            print(f"Unknown input '{answer.value}', redo")
            # reask
            return self._ask_implementation()

    def set_answer(self, value: str):
        """set the answer to a suitable value, also here parse is called!
           only consistent inputs values are accepted
        """
        self._answer = value
        self._answer_set = True

    def _ask_question(self):
        """Helper routine which asks the actual question"""
        is_set = False
        answer = input(self.question).strip()  # strip is important!
        if answer == "":
            if self._accept_enter:
                answer = self._answer
                is_set = True
        #
        return _Answer(answer, is_set)

    @property
    def _answer(self):
        return self._value.get()

    @_answer.setter
    def _answer(self, value):
        self._value.set(value)

    def __repr__(self):
        return f"{self.question}\n"

    def __str__(self):
        return f"{self.question}\n"

    def _generate_question(self, question):
        """generate actual question"""
        txt = question.question.strip()
        # add default option
        if question.default is not None:
            txt += " [%s]" % (str(question.default))
        if question.choices is not None:
            txt += ", choices = (%s)" % (", ".join(question.choices))
        return txt + ": "

    def _setup(self, question):
        if question.default is NOT_DEFINED:
            self._accept_enter = False

    def print(self):
        return f"{self.question}\n"


# Used to save status of a concrete answer
_Answer = namedtuple("_Answer", ("value", "is_set"))


class _Questions(_QuestionBase, MutableMapping):

    def __init__(self, questions, parent=None):
        _QuestionBase.__init__(self, parent)
        self.questions = {name: parse_question(question, parent=self.parent)
                          for (name, question) in questions.items()}

    def __getitem__(self, key):
        return self.questions.get(key, None)

    def __setitem__(self, key, value):
        self.questions[key] = value

    def __delitem__(self, key):
        del self.questions[key]

    def __iter__(self):
        return iter(self.questions)

    def __len__(self):
        return len(self.questions)

    def set_answer(self, value):
        raise Exception("For _Questions class no set_answer is possible at the moment!")

    def print(self):
        string = ""
        for name, question in self.items():
            string += f"{name}: {question.print()}\n"
        return string

    def _ask(self):
        answers = {}
        for name, question in self.items():
            answers[name] = question.ask()
        return answers


class _Subquestions(_QuestionBase, MutableMapping):

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

    def __setitem__(self, key, value):
        self.subquestions[key] = value

    def __delitem__(self, key):
        del self.subquestions[key]

    def __iter__(self):
        return iter(self.subquestions)

    def __len__(self):
        return len(self.subquestions)

    def set_answer(self, value):
        """set answer for main question"""
        self.main_question.set_answer(value)

    def print(self):
        string = f"{self.main_question}\n"
        for name, question in self.items():
            string += f"{name}: {question.print()}\n"
        return string

    def _ask(self):
        main_answer = self.main_question.ask()
        subquestion = self.get(main_answer, None)
        return SubquestionsAnswer(self.name, main_answer, subquestion.ask())


def parse_question(question, parent=None):

    if isinstance(question, dict):
        result = _Questions(question, parent=parent)
    elif isinstance(question, Question):
        result = _ConcreteQuestion(question, parent=parent)
    elif isinstance(question, LiteralBlock):
        return _LiteralBlock(question, parent=parent)
    elif isinstance(question, ConditionalQuestion):
        result = _Subquestions(question.name, question.main, question.subquestions, parent=parent)
    else:
        raise TypeError("Type of question not known!", question)
    return result
