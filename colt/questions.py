"""Definitions of all Question Classes"""
from abc import ABC, abstractmethod
from collections import UserDict, UserString
from collections.abc import Mapping
#
from .answers import SubquestionsAnswer
from .generator import GeneratorBase, BranchingNode
#
from .validator import Validator, NOT_DEFINED, ValidatorErrorNotInChoices
from .slottedcls import slottedcls


# store Questions
Question = slottedcls("Question", {"question": "",
                                   "typ": "str",
                                   "default": NOT_DEFINED,
                                   "choices": None,
                                   "comment": NOT_DEFINED,
                                   })

# identify literal blocks
_LiteralBlock = slottedcls("_LiteralBlock", ("name", ))


class ConditionalQuestion(BranchingNode):  # pylint: disable=too-many-ancestors
    """Conditional Question, is a branching node
       used to store decissions
    """

    def __init__(self, name, main, subquestions):
        super().__init__(name, main, subquestions)
        self.main = self.leaf
        self.subquestions = self.subnodes
        # updatable view!
        self.main.choices = self.subquestions.keys()

    @property
    def main_choices(self):
        return list(self.subquestions.keys())

    def __str__(self):
        return (f"ConditionalQuestion(name = {self.name},"
                f" main = {self.main}, subquestions = {self.subquestions}")

    def __repr__(self):
        return (f"ConditionalQuestion(name = {self.name},"
                f" main = {self.main}, subquestions = {self.subquestions}")


class QuestionContainer(UserDict):

    def __init__(self, data=None):
        if data is None:
            data = {}
        UserDict.__init__(self, data)

    def concrete_items(self):
        types = (ConditionalQuestion, QuestionContainer)
        for key, question in self.items():
            if not isinstance(question, types):
                yield key, question
            if isinstance(question, ConditionalQuestion):
                yield key, question.main


class LiteralBlockString(UserString):

    def __init__(self, string):
        UserString.__init__(self, string)


class LiteralContainer(Mapping):

    def __init__(self):
        self._literals = {}
        self.data = {}

    def add(self, name, literal, value=None): 
        self._literals[name] = literal
        self.data[name] = LiteralBlockString(value)

    def update(self, name, questions, parentnode=None):
        blockname = QuestionGenerator.join_keys(parentnode, name)
        for name, literal, value in questions.literals._all_items():
            name = QuestionGenerator.join_keys(blockname, name)
            literal.name = name
            self.add(name, literal, value)

    def __getitem__(self, key):                
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = LiteralBlockString(value)

    def __len__(self):            
        return len(self.data)

    def __iter__(self):
        return iter(self.data)

    def _all_items(self):
        for key in self.data:
            yield key, self._literals[key], self.data[key]


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
    node_type = QuestionContainer

    LeafString = slottedcls("LeafString", {"default": NOT_DEFINED,
                                           "typ": "str",
                                           "choices": NOT_DEFINED,
                                           "question": NOT_DEFINED})

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
            self.literals = LiteralContainer()
        else:
            raise TypeError("Generator only accepts type string!")
        GeneratorBase.__init__(self, questions)
        #
        self.questions = self.tree

    @classmethod
    def new_branching(cls, name, leaf=None):
        """Create a new empty branching"""
        if leaf is None:
            return ConditionalQuestion(name, Question(name), QuestionContainer())
        return ConditionalQuestion(name, leaf, QuestionContainer())

    @staticmethod
    def new_node():
        return QuestionContainer()

    @staticmethod
    def tree_container():
        return QuestionContainer()

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
            name = self.join_keys(parent, name)
            block = _LiteralBlock(name)
            self.literals.add(name, block)
            return block
        # get default
        default = self._parse_default(value.default)
        # get question
        if value.question is NOT_DEFINED:
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
        #
        subquestions = {name: QuestionGenerator(questions) 
                        for name, questions in subquestions.items()}
        #
        self.add_branching(key, subquestions, parentnode=block)
        #
        for name, questions in subquestions.items():
            name = self.join_case(key, name)
            self.literals.update(name, questions, parentnode=block)

    def add_questions_to_block(self, questions, block=None, overwrite=True):
        """add questions to a particular block """
        questions = QuestionGenerator(questions)
        self.add_elements(questions, parentnode=block, overwrite=overwrite)
        self.literals.update(block, questions)

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
        questions = QuestionGenerator(questions)
        self.add_node(name, questions, parentnode=block)
        self.literals.update(name, questions, parentnode=block)

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
            comment = NOT_DEFINED
        else:
            comment = comment.replace("#n", "\n")
        return line, comment

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
    def _parse_choices(cls, typ, line):
        """Handle choices"""
        if line == "":
            return None
        if line is NOT_DEFINED:
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


class LiteralBlock(_QuestionBase):
    """parse literal blocks"""

    def __init__(self, literal, parent=None):
        _QuestionBase.__init__(self, parent)
        self.name = literal.name

    def set_answer(self, value):
        """answer"""
        if self.parent is not None:
            self.parent.literals[self.name] = value
        raise NotImplementedError("set_answer not supported for literalblock")

    def _ask(self):
        if self.parent is not None:
            return self.parent.literals.get(self.name, None)
        return None


class ConcreteQuestion(_QuestionBase):

    def __init__(self, question, parent=None):
        # setup
        _QuestionBase.__init__(self, parent)
        #
        self._value = Validator(question.typ, default=question.default,
                                choices=question.choices)
        #
        self._accept_enter = True
        self._comment = question.comment
        self.raw_question = question.question
        self.typ = question.typ
        #
        self._setup(question)
        # generate the question
        self.question = self._generate_question(question)
        self.is_set = False

    def _ask(self):
        if self.parent is None or self.parent.is_only_checking is False:
            return self._ask_implementation()
        return self.answer

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
        if self.is_set is True:
            return self.answer
        #
        answer = self._perform_questions()
        #
        if answer.is_set is True:
            # if answer is set, return unparsed answer
            return answer.value
        #
        try:
            if answer.value == "":
                raise ValueError("No default set, empty string not allowed!")
            self.answer = answer.value
            return self.answer
        except ValueError:
            print(f"Unknown input '{answer.value}', redo")
        except ValidatorErrorNotInChoices:
            print(f"Answer '{answer.value}' not in choices!")
        # reask!
        return self._ask_implementation()

    def set_answer(self, value: str):
        """set the answer to a suitable value, also here parse is called!
           only consistent inputs values are accepted
        """
        self.answer = value
        self.is_set = True

    def _ask_question(self):
        """Helper routine which asks the actual question"""
        is_set = False
        answer = input(self.question).strip()  # strip is important!
        if answer == "":
            if self._accept_enter:
                answer = self.answer
                is_set = True
        #
        return _Answer(answer, is_set)

    @property
    def answer(self):
        return self._value.get()

    @answer.setter
    def answer(self, value):
        self._value.set(value)

    @property
    def choices(self):
        return self._value.choices

    def __repr__(self):
        return f"{self.question}\n"

    def __str__(self):
        return f"{self.question}\n"

    def _generate_question(self, question):
        """generate actual question"""
        if question.question is NOT_DEFINED:
            if question.default is NOT_DEFINED:
                txt = ""
            else:
                txt = f"{question.default}"
        else:
            txt = question.question.strip()
        # add default option
        if question.default is not NOT_DEFINED:
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
_Answer = slottedcls("_Answer", ("value", "is_set"))


class _QuestionsContainerBase(_QuestionBase, UserDict):

    def __init__(self, parent, data):
        _QuestionBase.__init__(self, parent)
        UserDict.__init__(self, data)

    def concrete_items(self):
        types = (Subquestions, Questions, LiteralBlock)
        for key, value in self.items():
            if not isinstance(value, types):
                yield key, value


class Questions(_QuestionsContainerBase):

    def __init__(self, questions, parent=None):
        #
        self.questions = {name: parse_question(question, parent=parent)
                          for (name, question) in questions.items()}
        # init super()
        _QuestionsContainerBase.__init__(self, parent, self.questions)

    def set_answer(self, value):
        raise Exception("For Questions class no set_answer is possible at the moment!")

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


class Subquestions(_QuestionsContainerBase):

    def __init__(self, name, main_question, questions, parent=None):
        # main question
        self.name = name
        #
        if main_question.typ != 'str':
            raise ValueError("Cases can only be of type string!")
        # subquestions
        self.subquestions = {name: parse_question(question, parent=parent)
                             for name, question in questions.items()}
        # ensure that choices are only subquestions options!
        main_question = Question(question=main_question.question, typ=main_question.typ,
                                 default=main_question.default,
                                 choices=self.subquestions.keys(),
                                 comment=main_question.comment)
        #
        self.main_question = ConcreteQuestion(main_question, parent=parent)
        # setup data container
        _QuestionsContainerBase.__init__(self, parent, self.subquestions)

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
        return SubquestionsAnswer(self.name, main_answer, self[main_answer].ask())


def parse_question(question, parent=None):

    if isinstance(question, QuestionContainer):
        result = Questions(question, parent=parent)
    elif isinstance(question, Question):
        result = ConcreteQuestion(question, parent=parent)
    elif isinstance(question, _LiteralBlock):
        return LiteralBlock(question, parent=parent)
    elif isinstance(question, ConditionalQuestion):
        result = Subquestions(question.name, question.main, question.subquestions, parent=parent)
    else:
        raise TypeError("Type of question not known!", question)
    return result
