import sys
import argparse
import configparser
#
from abc import ABCMeta
#
from .answers import SubquestionsAnswer
from .generator import QuestionGenerator
from .questions import _Subquestions, _Questions, _ConcreteQuestion
from .questions import Question, parse_question


__all__ = ["Colt", "AskQuestions"]


class AskQuestions:
    """Main Object to handle question request"""

    def __init__(self, name, questions, config=None):
        """Main Object to handle question request

        Args:
            name (str): Name of the questions name, will be added to each block
                        of the corresponding config

            questions:  Questions object, can be
                          1) Dict, dictionary object
                          2) ConditionalQuestion, a conditional question
                          3) Question, a concrete question
                          From there the real questions will be generated!

        Kwargs:
            config (str): None, a single or multiple configfiles
                          from which default answers are set!

        """
        self.answers = None
        self.name = name
        self._config = config
        self.questions = self._setup(questions, config)
        self.configparser = self._fileparser()
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
            self._create_config_start(self.configparser, self.name, answers)
            self._write(filename)
        self.answers = answers
        return answers

    def create_config_from_answers(self, filename):
        if self.answers is None:
            self.ask(filename)
            return
        self._create_config_start(self.configparser, self.name, self.answers)
        self._write(filename)

    def check_only(self, filename):
        self.only_check = True
        answers = self.questions.ask()
        if self._check_failed is True:
            self._create_config_start(self.configparser, self.name, answers)
            self._write(filename)
            raise Exception(f"Input not complete, check file '{filename}' for missing values!")
        self.only_check = False
        return answers

    def __getitem__(self, key):
        return self.questions.get(key, None)

    def __repr__(self):
        return f"AskQuestions({self.name}, config='{self._config}')"

    def _setup(self, questions, config):
        """setup questions and read config file in case a default file is give"""
        self.questions = parse_question(questions, parent=self)
        if config is not None:
            self.set_answers_from_file(config)
        return self.questions

    @classmethod
    def _get_question_block(cls, questions, block):
        """Parse down the abstraction tree to extract
           particular questions based on their
           block name in the config file
        """
        if questions is None:
            return None, None
        old_block, _, new_block = block.partition(QuestionGenerator.seperator)
        if new_block == "":
            # end of the recursive function
            return questions, old_block
        # Check for conditionals
        block_key, _, _ = new_block.partition(QuestionGenerator.seperator)
        conditionals = QuestionGenerator.is_decission(block_key)
        #
        if conditionals is False:
            return cls._get_question_block(questions[block_key], new_block)
        # Handle conditionals
        key, decission = conditionals
        try:
            if isinstance(questions, _Subquestions):
                questions = questions[decission]
            else:
                questions = questions[key][decission]
            return cls._get_question_block(questions, new_block)
        except Exception:
            return None, None

    def set_answers_from_file(self, filename):
        """Set answers from a given file"""
        parsed = self._fileparser(filename)
        for section in parsed.sections():
            question, _ = self._get_question_block(self.questions, section)
            if question is None:
                print(f"""Section = {section} unknown, maybe typo?""")
                continue
            if isinstance(question, _Subquestions):
                if len(parsed[section].items()) == 1:
                    for key, value in parsed[section].items():
                        if key == question.name:
                            question.set_answer(value)
                        else:
                            print(f"""In Section({section}) key({key}) unknown, maybe typo?""")
                else:
                    for key, value in parsed[section].items():
                        if key == question.name:
                            question.set_answer(value)
                        else:
                            print(f"""In Section({section}) key({key}) unknown, maybe typo?""")
                    print(f"question instance is ConditionalQuestion, "
                          f"but multiple values are defined? input error?")
                continue
            for key, value in parsed[section].items():
                try:
                    question[key].set_answer(value)
                except:
                    print(f"""In Section({section}) key({key}) unknown, maybe typo?""")

    def _write(self, filename):
        """write output to file"""
        with open(filename, 'w') as configfile:
            self.configparser.write(configfile)

    def _actual_modifyer(self, question, answer):
        _ConcreteQuestion.set_answer(question, answer)

    def _modify(self, name, config, questions):
        """set answers depending on the config file!"""
        if isinstance(questions, _Subquestions):
            if config[name].get(questions.name, None) is not None:
                self._actual_modifyer(questions, config[name][questions.name])
#                questions.set_answer(config[name][questions.name])
                self._modify_questions(f"{name}::{questions.name}({config[name][questions.name]})",
                                       config, questions.subquestions)
        else:
            self._modify_questions(name, config, questions)

    def _modify_selection(self, name, key, question, config):
        if isinstance(question, _Questions):
            self._modify_questions(name, config, question.questions)
        elif isinstance(question, _Subquestions):
            if config[name].get(question.name, None) is not None:
                question.set_answer(config[name][question.name])
                self._modify_questions((f"{name}::{question.name}"
                                        f"({config[name][question.name]})"),
                                       config, question.subquestions)
        elif isinstance(question, dict):
            self._modify_questions(name, config, question)
        elif isinstance(question, _ConcreteQuestion):
            if config[name].get(key, None) is not None:
                question.set_answer(config[name][key])
        else:
            raise TypeError(f"Type of question not known! {type(question)}")

    def _modify_questions(self, name, config, questions):
        """ recusive function to set answer depending on the config file!"""
        # check that config[name] is defined!
        try:
            config[name]
        except Exception:
            return questions
        #
        for key, question in questions.items():
            self._modify_selection(name, key, question, config)
#            if isinstance(question, _Questions):
#                self._modify_questions(f"{name}", config, question.questions)
#            elif isinstance(question, _ConcreteQuestion):
#                if config[name].get(key, None) is not None:
#                    question.set_answer(config[name][key])
#            elif isinstance(question, _Subquestions):
#                if config[name].get(question.name, None) is not None:
#                    question.set_answer(config[name][question.name])
#                    self._modify_questions((f"{name}::{question.name}"
#                                            f"({config[name][question.name]})"),
#                                           config, question.subquestions)
#            else:
#                raise TypeError(f"Type of question not known! {type(question)}")

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


def colt_meta_setup(clsdict):
    """setup the clsdict in colt to avoid inheritance problems"""

    if '_generate_subquestions' not in clsdict:
        clsdict['_generate_subquestions'] = classmethod(lambda cls, questions: 0)
    # also add empty _questions text
    if '_questions' not in clsdict:
        clsdict['_questions'] = "" 
    else:
        if clsdict['_questions'] == "inherited": 
            del clsdict['_questions']


class ColtMeta(ABCMeta):
    """Metaclass to handle hierarchical generation of questions"""

    def __new__(cls, name, bases, clsdict):
        colt_meta_setup(clsdict)
        return ABCMeta.__new__(cls, name, bases, clsdict)

    @property
    def questions(cls):
        return cls._generate_questions()

    def _generate_questions(cls):
        """generate questions"""
        questions = QuestionGenerator(cls._questions)
        cls._generate_subquestions(questions)
        return questions.questions

    def _generate_subquestions(cls, questions):
        """This class will not be inherited"""
        pass


class Colt(metaclass=ColtMeta):
    """Basic Class to manage colts question routines"""

    @property
    def questions(self):
        return self.__class__.questions

    @classmethod
    def generate_questions(cls, name, config=None):
        return AskQuestions(name, cls.questions, config=config)

    @classmethod
    def from_questions(cls, name, check_only=False, config=None, savefile=None):
        questions = cls.generate_questions(name, config=config)
        if check_only is True:
            return questions.check_only(savefile)
        answers = questions.ask(savefile)
        return cls.from_config(answers)

    @classmethod
    def from_config(cls, answer):
        raise Exception("Cannot load from_config, as it is not implemented!, "
                        "also from_questions depend on that!")

    @classmethod
    def from_commandline(cls, description=None):
        """Initialize file from commandline options"""
        answers = cls.get_commandline_args(description=description)
        return cls.from_config(answers)

    @classmethod
    def get_commandline_args(cls, description=None):
        """for the moment we accept only linear trees!"""

        parser = argparse.ArgumentParser(description=description,
                                         formatter_class=argparse.RawTextHelpFormatter)
        #
        type_parser = _ConcreteQuestion.get_parsers()

        for key, question in cls.questions.items():
            if not isinstance(question, Question):
                raise ValueError("Only linear trees allowed!")
            if question.default is not None:
                parser.add_argument(f'--{key}', metavar=key, type=type_parser[question.typ],
                                    default=question.default, help=question.comment)
            else:
                parser.add_argument(f'{key}', metavar=key, type=type_parser[question.typ],
                                    help=question.comment)

        results = parser.parse_args()

        return {key: getattr(results, key) for key in cls.questions.keys()}
