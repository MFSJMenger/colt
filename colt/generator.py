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

    def __init__(self, questions, isfile=False):
        # if is questions
        if self.is_question(questions):
            self.questions = questions
            return
        # if is file
        if isfile is True:
            # read file
            with open(questions, "r") as f:
                questions = f.read()
        # is string
        questions = self._setup(questions)
        self.questions = self.generate_questions(questions)

    def generate_cases(self, block, key, subblocks):
        subblocks = {name: QuestionGenerator(value).questions
                     for name, value in subblocks.items()}
        questions, _ = self.get_question_block(self.questions, block)

        if questions is None:
            raise Exception(f"block {block} unknown")

        if questions[key] is None:
            questions[key] = ConditionalQuestion(key, Question(key), subblocks)
        elif isinstance(questions[key], ConditionalQuestion):
            for name, item in subblocks.items():
                questions[key][name] = item
        elif isinstance(questions[key], Question):
            questions[key] = ConditionalQuestion(key, questions[key], subblocks)
        else:
            raise Exception("something wronge in generate cases")

    def is_question(self, questions):
        if isinstance(questions, dict):
            return True
        elif isinstance(questions, Question):
            return True
        elif isinstance(questions, ConditionalQuestion):
            return True
        else:
            return False

    @classmethod
    def questions_from_string(cls, string):
        config = cls._setup(string)
        return cls.generate_questions(config)

    @classmethod
    def questions_from_file(cls, filename):
        with open(filename, "r") as f:
            string = f.read()
        return cls.questions_from_string(string)

    @classmethod
    def generate_questions(cls, config):
        # linear parser
        questions = {}

        for key, value in config[cls.default].items():
            questions[key] = cls._parse_question_line(key, value)

        afterwards = [section for section in config.sections() if cls.is_subblock(section)]

        for section in config.sections():
            if section == cls.default:
                continue
            if cls.is_subblock(section):
                continue
            subquestions = {}
            for key, value in config[section].items():
                subquestions[key] = cls._parse_question_line(key, value)
            questions[section] = subquestions

        for section in afterwards:
            subquestions = cls._get_section(questions, section)
            if subquestions is None:
                continue
            for key, value in config[section].items():
                subquestions[key] = cls._parse_question_line(key, value)
        return questions

    @classmethod
    def is_subblock(cls, block):
        if any(key in block for key in (cls.seperator, '(', ')')):
            return True
        return False

    @classmethod
    def is_decission(cls, key):
        conditions = cls.parse_conditionals_helper.match(key)
        if conditions is None:
            return False
        return cls.Conditionals(conditions.group("key"), conditions.group("decission"))

    @staticmethod
    def _parse_default(default):
        """ """
        if default.lower() == 'none' or default == "":
            return None
        return default

    @classmethod
    def _parse_comment(cls, line):
        line, _, comment = line.partition(cls.comment_char)
        if comment == "":
            comment = None
        else:
            comment = comment.replace("#n", "\n")
        return line, comment

    @classmethod
    def _parse_choices(cls, typ, line):
        "replace "
        if typ not in cls._allowed_choices_types:
            return None
        line = line.replace("[", "").replace("]", "")
        return [choice.strip() for choice in line.split(",")]

    @classmethod
    def _parse_question_line(cls, name, line):
        """Convert string to Question"""
        # handle comment
        line, comment = cls._parse_comment(line)

        line = [ele.strip() for ele in line.split(cls.seperator)]
        len_line = len(line)
        default = cls._parse_default(line[0])
        #
        if len_line == 1:
            return Question(question=name, default=default, comment=comment)
        if len_line == 2:
            return Question(question=name, default=default, typ=line[1], comment=comment)
        if len_line == 3:
            return Question(question=name,
                            default=default, typ=line[1],
                            choices=cls._parse_choices(line[1], line[2]),
                            comment=comment)
        if len_line == 4:
            return Question(default=default, typ=line[1],
                            choices=cls._parse_choices(line[1], line[2]),
                            question=line[3], comment=comment)

    @staticmethod
    def _preprocess_string(string):

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
        """ """
        conditions = cls.is_decission(key)
        if conditions is False:
            return sections.get(key, None)

        key, decission = conditions
        sections = sections.get(key, None)
        if sections is not None:
            return sections.get(decission, None)
        return sections

    @classmethod
    def _get_section(cls, sections, block):
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
        raise Exception("cannot handle anything else")

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
        print(key, decission)
        try:
            if isinstance(questions, _Subquestions):
                questions = questions[decission]
            else:
                questions = questions[key][decission]
            return cls.get_question_block(questions, new_block)
        except Exception:
            return None, None
