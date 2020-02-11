from functools import wraps
import configparser
import sys
#
from .answers import SubquestionsAnswer
from .config import ConfigParser
from .questions import QuestionGenerator
from .questions import _Subquestions, _Questions, _ConcreteQuestion
from .questions import parse_question


def with_attribute(attr, value):
    def _class_function(f):
        @wraps(f)
        def _inner(self, *args, **kwargs):
            if hasattr(self, attr):
                old = getattr(self, attr)
            else:
                delete = True
            setattr(self, attr, value)
            val = f(self, *args, **kwargs)
            if delete is False:
                setattr(self, attr, old)
            return val
        return _inner
    return _class_function

class AskQuestions:
    """Main Object to handle question request"""

    __slots__ = ("name", "literals", "questions", "answers", "only_check", "_check_failed", '_no_failure_setting_answers')

    def __init__(self, name, questions, config=None):
        """Main Object to handle question request

        Args:
            name (str):
                Name of the questions name, will be added to each block
                of the corresponding config

            questions (obj):
                Questions object, can be
                          1) Dict, dictionary object
                          2) ConditionalQuestion, a conditional question
                          3) Question, a concrete question
                          From there the real questions will be generated!

        Kwargs:
            config (str):
                None, a single or multiple configfiles
                from which default answers are set!

        """
        questions = QuestionGenerator(questions)
        self.literals = questions.literals
        #
        self.answers = None
        self.name = name
        # setup
        self.questions = self._setup(questions.questions, config)
        #
        self.only_check = False
        self._check_failed = False

    @classmethod
    def questions_from_string(cls, name, question_string, config=None):
        questions = QuestionGenerator.questions_from_string(question_string)
        return cls(name, questions, config)

    @classmethod
    def questions_from_file(cls, name, filename, config=None):
        questions = QuestionGenerator.questions_from_file(filename)
        return cls(name, questions, config)

    def ask(self, filename=None):
        """ask the actual question"""
        answers = self.questions.ask()
        if filename is not None:
            self._create_config_start(self._fileparser(), self.name, answers)
            self._write(filename)
        self.answers = answers
        return answers

    def create_config_from_answers(self, filename, answers=None):
        """Create a config from defined answers"""
        if answers is not None:
            self._create_config_start(self._fileparser(), self.name, answers)
            self._write(filename)

    def check_only(self, filename):
        self.only_check = True
        answers = self.questions.ask()
        if self._check_failed is True:
            self._create_config_start(self._fileparser(), self.name, answers)
            self._write(filename)
            raise Exception(f"Input not complete, check file '{filename}' for missing values!")
        self.only_check = False
        return answers

    def __getitem__(self, key):
        return self.questions.get(key, None)

    def _setup(self, questions, config):
        """setup questions and read config file in case a default file is give"""
        self.questions = parse_question(questions, parent=self)
        if config is not None:
            self.set_answers_from_file(config)
        return self.questions

    def _set_answer(self, section, key, question, answer):
        try:
            question.set_answer(answer)
            return ""
        except ValueError:
            self._no_failure_setting_answers = False
            return f"\n{key} = {answer}, TypeError"

    @with_attribute('_no_failure_setting_answers', True)
    def set_answers_from_file(self, filename):
        """Set answers from a given file"""
        # self.literals should probably not be updated in this manner...
        parsed, self.literals = ConfigParser.read(filename, self.literals)
        #
        for section, values in parsed.items():
            if section == ConfigParser.base:
                name = ""
                error = ""
            else:
                name = section
                error = f'[{section}]'
            errmsg = ""
            #
            question = QuestionGenerator.get_node_from_tree(name, self.questions)
            #
            if question is None:
                print(f"""Section = {section} unknown, maybe typo?""")
            elif isinstance(question, _ConcreteQuestion):
                print(f"""Section '{section}' is concrete question, maybe typo?""")
            elif isinstance(question, _Subquestions):
                if len(parsed[section].items()) == 1:
                    for key, value in parsed[section].items():
                        if key == question.name:
                            errmsg += self._set_answer(section, key, question, value)
                        else:
                            errmsg += f"\n{key} = UNKNOWN"
                else:
                    for key, value in parsed[section].items():
                        if key == question.name:
                            errmsg += self._set_answer(section, key, question, value)
                        else:
                            errmsg += f"\n{key} = UNKNOWN"
                    print(f"Input Error: question instance is ConditionalQuestion, "
                          f"but multiple values are defined!")
            elif isinstance(question, _Questions):
                for key, value in parsed[section].items():
                    concre_question = question[key]
                    if concre_question is None:
                        errmsg += f"\n{key} = UNKNOWN"
                    else:
                        errmsg += self._set_answer(section, key, concre_question, value)
            else:
                print(f'Unkown type...')

            if errmsg != "":
                print(f"{error}{errmsg}")

        if self._no_failure_setting_answers is False:
            sys.exit()

    def _write(self, filename):
        """write output to file"""
        with open(filename, 'w') as configfile:
            self._fileparser().write(configfile)

    @classmethod
    def _fileparser(cls, filename=None):
        if filename is None:
            return configparser.ConfigParser(allow_no_value=True)
        parser = configparser.ConfigParser(allow_no_value=True)
        parser.read(filename)
        return parser

    @classmethod
    def _create_config_start(cls, config, name, entries):
        """Starting routine to create config file"""
        if isinstance(entries, SubquestionsAnswer):
            config[name] = {}
            config[name][entries.name] = entries.value
            cls._create_config(config, f"{name}::{entries.name}({entries.value})", entries)
        else:
            cls._create_config(config, name, entries)

    @classmethod
    def _create_config(cls, config, name, entries):
        # sanity check!
        if not (isinstance(entries, SubquestionsAnswer) or isinstance(entries, dict)):
            return

        config[name] = {}

        for key, entry in entries.items():
            if isinstance(entry, SubquestionsAnswer):
                config[name][entry.name] = entry.value
                cls._create_config(config, f"{name}::{entry.name}({entry.value})", entry)
            elif isinstance(entry, dict):
                cls._create_config(config, f"{name}::{key}", entry)
            elif isinstance(entry, list):
                config[name][key] = ", ".join(str(ele) for ele in entry)
            else:
                config[name][key] = str(entry)
