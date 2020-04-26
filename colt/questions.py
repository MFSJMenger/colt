"""Definitions of all Question Classes"""
from collections import UserDict, UserString
#
from .generator import GeneratorBase, BranchingNode
#
from .validator import NOT_DEFINED
from .slottedcls import slottedcls


# store Questions
Question = slottedcls("Question", {"question": "",
                                   "typ": "str",
                                   "default": NOT_DEFINED,
                                   "choices": None,
                                   "comment": NOT_DEFINED,
                                   })

# identify literal blocks
LiteralBlockQuestion = slottedcls("LiteralBlockQuestion", ("name", ))


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
        #

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
        if string is None:
            self.is_none = True
            string = ''
        elif isinstance(string, LiteralBlockString):
            self.is_none = string.is_none
        else:
            self.is_none = False
        #
        UserString.__init__(self, string)


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
        print(type(questions))
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
            return LiteralBlockQuestion(name)
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

    def add_questions_to_block(self, questions, block=None, overwrite=True):
        """add questions to a particular block """
        questions = QuestionGenerator(questions)
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
        questions = QuestionGenerator(questions)
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
        if default in ('NOT_DEFINED', ""):
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
