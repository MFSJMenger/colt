import re
from collections import namedtuple
import configparser
#
from .questions import Question, ConditionalQuestion
from .questions import _Subquestions


class QuestionGenerator(object):
    """Contains all tools to automatically generate questions from
       a given file
    """

    seperator = "::"
    comment_char = "###"
    default = '__QUESTIONS__'
    _allowed_choices_types = ['int', 'str', 'float', 'bool']

    parse_conditionals_helper = re.compile(r"(?P<key>.*)\((?P<decission>.*)\)")
    Conditionals = namedtuple("Conditionals", ["key", "decission"])

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
        self.questions = self.string_to_questions(questions)

    def generate_cases(self, key, subquestions, block=""):
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
        subblocks = {name: QuestionGenerator(value).questions
                     for name, value in subquestions.items()}
        questions, _ = self.get_question_block(self.questions, block)

        if questions is None:
            raise KeyError(f"block {block} unknown")

        if questions.get(key, None) is None:
            questions[key] = ConditionalQuestion(key, Question(key), subblocks)
        elif isinstance(questions[key], ConditionalQuestion):
            for name, item in subblocks.items():
                questions[key][name] = item
        elif isinstance(questions[key], Question):
            questions[key] = ConditionalQuestion(key, questions[key], subblocks)
        else:
            raise ValueError(f"Argument {questions[key]} can only be None, Questions, ConditionalQuestion")

    def add_questions_to_block(self, questions, block="", overwrite=True):
        """add questions to a particular block """
        block_questions, _ = self.get_question_block(self.questions, block)
        if questions is None:
            raise KeyError(f"block {block} unknown")

        if not isinstance(block_questions, dict):
            raise ValueError(f"block questions {block} should be a dict!")

        if not self.is_question(questions): # assume is string!
            questions = self.string_to_questions(questions)
        # just update the dict
        if overwrite is True:
            block_questions.update(questions)
            return
        # overwrite it
        for key, item in questions.items():
            if key not in block_questions:
                block_questions[key] = item

    def generate_block(self, key, questions, block=""):
        """Register `questions` at a given `key` in given `block`

        Args:
            key (str): name of the variable that should be overwritten as a subquestion

            questions (dict): Dict of Questions corresponding to the subquestions
                             one wants to register

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

        subblocks = QuestionGenerator(questions).questions

        questions, _ = self.get_question_block(self.questions, block)
        if questions is None:
            raise KeyError(f"block {block} unknown")

        if questions.get(key) is None:
            questions[key] = subblocks
        else:
            raise ValueError(f"{key} in [{block}] should not be given")

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

    @classmethod
    def generate_questions(cls, config):
        """Main Routine to generate questions from a parsed config file

        Args:
            name (str): Name of the questions name, will be added to each block
                        of the corresponding config

        Returns:
            questions: Question Object, containing all questions defined in config!

        """
        # linear parser
        questions = {}
        # parse defaults
        for key, value in config[cls.default].items():
            questions[key] = cls._parse_question_line(key, value)
        # get subsections
        subsections = [section for section in config.sections() if cls.is_subblock(section)]
        # parse main sections
        for section in config.sections():
            if section == cls.default:
                continue
            if cls.is_subblock(section):
                continue
            subquestions = {}
            for key, value in config[section].items():
                subquestions[key] = cls._parse_question_line(key, value)
            questions[section] = subquestions
        # parse and go to specific section!
        for section in subsections:
            subquestions = cls._get_questions_of_block(questions, section)
            if subquestions is None:
                continue
            for key, value in config[section].items():
                subquestions[key] = cls._parse_question_line(key, value)
        #
        return questions

    @classmethod
    def is_subblock(cls, block):
        """Is the block a subquestions block or not"""
        if any(key in block for key in (cls.seperator, '(', ')')):
            return True
        return False

    @classmethod
    def is_decission(cls, key):
        """is the key a decission key"""
        conditions = cls.parse_conditionals_helper.match(key)
        if conditions is None:
            return False
        return cls.Conditionals(conditions.group("key"), conditions.group("decission"))

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

    @classmethod
    def _parse_question_line(cls, name, line):
        """Convert string to Question

        Args:
            name (str): name of the question

            line (str): value of the question

        Returns:
            Question, basic namedtuple which contains all info
                      needed to construct a question
        Raises:
            Exception: If line does not fit standard format, raise exception!
        """
        original_line = line
        # handle comment
        line, comment = cls._parse_comment(line)
        #
        line = [ele.strip() for ele in line.split(cls.seperator)]
        len_line = len(line)
        #
        default = cls._parse_default(line[0])
        # set defaults
        typ = 'str'
        choices = None
        question = name
        #
        if len_line == 1:
            pass
        elif len_line == 2:
            typ = line[1]
        elif len_line == 3:
            typ = line[1]
            choices = line[2]
        elif len_line == 4:
            typ = line[1]
            choices = line[2]
            question = line[3]
        else:
            raise Exception(f"Cannot parse line `{original_line}`")
            
        return Question(question, typ, default, cls._parse_choices(typ, choices), comment)


    def string_to_questions(self, string):
        questions = self._setup(string)
        return self.generate_questions(questions)

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
    def _setup(cls, string):
        """Prepare setup"""
        string = cls._preprocess_string(string)
        # add [DEFAULT] for easier parsing!
        if not string.lstrip().startswith(f'[{cls.default}]'):
            string = f'[{cls.default}]\n' + string
        #
        config = configparser.ConfigParser()
        config.read_string(string)
        return config

    @classmethod
    def _get_next_section(cls, sections, key):
        """Get the next section using the current section and
           the key to the next question!"""
        conditions = cls.is_decission(key)
        if conditions is False:
            return sections.get(key, None)

        key, decission = conditions
        sections = sections.get(key, None)
        if sections is not None:
            return sections.get(decission, None)
        return sections

    @classmethod
    def _get_questions_of_block(cls, sections, block):
        """Get a section from a given block,
           iterative loop over the sections till the last
           section block is reached
        """
        keys = block.split('::')
        #
        final_key = keys[-1]
        # we are not at the end!
        for key in keys[:-1]:
            sections = cls._get_next_section(sections, key)
            if sections is None:
                return
        # do this
        conditions = cls.is_decission(final_key)
        if conditions is False:
            sections[final_key] = {}
            return sections[final_key]

        key, decission = conditions
        argument = sections.get(key, None)
        if argument is None:
            # no default question defined, should also give warning?
            questions = ConditionalQuestion(key, Question(key), {decission: {}})
            sections[key] = questions
            return questions.subquestions[decission]
        if isinstance(argument, Question):
            # default question defined, but first found case
            questions = ConditionalQuestion(key, argument, {decission: {}})
            sections[key] = questions
            return questions.subquestions[decission]
        if isinstance(argument, ConditionalQuestion):
            # another found case
            argument.subquestions[decission] = {}
            return argument.subquestions[decission]
        raise ValueError(f"Argument {argument} has to be Question, ConditionalQuestion, or None")

    @classmethod
    def get_question_block(cls, questions, block):
        """Parse down the abstraction tree to extract
           particular questions based on their
           block name in the config file
        """
        if questions is None:
            return None, None
        old_block, delim, new_block = block.partition(cls.seperator)
        if new_block == "":
            # end of the recursive function
            return questions, old_block
        # Check for conditionals
        block_key, _, _ = new_block.partition(cls.seperator)
        conditionals = cls.is_decission(block_key)
        #
        if conditionals is False:
            return cls.get_question_block(questions[block_key], new_block)
        # Handle conditionals
        key, decission = conditionals
        try:
            if isinstance(questions, _Subquestions):
                questions = questions[decission]
            else:
                questions = questions[key][decission]
            return cls.get_question_block(questions, new_block)
        except Exception:
            return None, None
