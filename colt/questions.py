import configparser
#
from .answers import SubquestionsAnswer
from .generator import QuestionGenerator
from .base_questions import _Subquestions, _Questions, _ConcreteQuestion
from .base_questions import parse_question


# __all__ = ["_Subquestions", "Question", "ConditionalQuestion", "AskQuestions", "register_parser"]


def register_parser(key, function):
    """register a parser for the Questions class

       The parser function needs to take  a single
       argument which is a string and return a
       single python object, which should not be a
       **dict**!
    """
    _ConcreteQuestion.register_parser(key, function)


class AskQuestions(object):

    def __init__(self, name, questions, config=None):
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
        old_block, delim, new_block = block.partition(QuestionGenerator.seperator)
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
            question, se = self._get_question_block(self.questions, section)
            if question is None:
                print(f"""Section = {section} unkown, maybe typo?""")
                continue
            if isinstance(question, _Subquestions):
                if len(parsed[section].items()) == 1:
                    for key, value in parsed[section].items():
                        if key == question.name:
                            question.set_answer(value)
                        else:
                            print(f"""In Section({section}) key({key}) unkown, maybe typo?""")
                else:
                    for key, value in parsed[section].items():
                        if key == question.name:
                            question.set_answer(value)
                        else:
                            print(f"""In Section({section}) key({key}) unkown, maybe typo?""")
                    print(f"""question instance is ConditionalQuestion, but multiple values are defined? input error?""")
                continue
            for key, value in parsed[section].items():
                try:
                    question[key].set_answer(value)
                except:
                    print(f"""In Section({section}) key({key}) unkown, maybe typo?""")

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
                self._modify_questions(
                        f"{name}::{questions.name}({config[name][questions.name]})",
                        config, questions.subquestions)
        else:
            self._modify_questions(name, config, questions)

    def _modify_questions(self, name, config, questions):
        """ recusive function to set answer depending on the config file!"""
        # check that config[name] is defined!
        try:
            config[name]
        except Exception:
            return questions
        #
        for key, question in questions.items():
            if isinstance(question, _Questions):
                self._modify_questions(f"{name}", config, question.questions)
            elif isinstance(question, _ConcreteQuestion):
                if config[name].get(key, None) is not None:
                    question.set_answer(config[name][key])
            elif isinstance(question, _Subquestions):
                if config[name].get(question.name, None) is not None:
                    question.set_answer(config[name][question.name])
                    self._modify_questions(
                            f"{name}::{question.name}({config[name][question.name]})",
                            config, question.subquestions)
            else:
                raise TypeError(f"Type of question not known! {type(question)}")

    @classmethod
    def _fileparser(cls, filename=None):
        if filename is None:
            return configparser.ConfigParser(allow_no_value=True)
        parser = configparser.ConfigParser(allow_no_value=True)
        parser.read(filename)
        return parser

    @staticmethod
    def _create_config_start(config, name, entries):
        """Starting routine to create config file"""
        if isinstance(entries, SubquestionsAnswer):
            config[name] = {}
            config[name][entries.name] = entries.value
            AskQuestions._create_config(config, f"{name}::{entries.name}({entries.value})", entries)
        else:
            AskQuestions._create_config(config, name, entries)

    @staticmethod
    def _create_config(config, name, entries):
        # sanity check!
        if not (isinstance(entries, SubquestionsAnswer) or isinstance(entries, dict)):
            return

        config[name] = {}

        for key, entry in entries.items():
            if isinstance(entry, SubquestionsAnswer):
                config[name][entry.name] = entry.value
                AskQuestions._create_config(config, f"{name}::{entry.name}({entry.value})", entry)
            elif isinstance(entry, dict):
                AskQuestions._create_config(config, f"{name}::{key}", entry)
            elif isinstance(entry, list):
                config[name][key] = ", ".join(str(ele) for ele in entry)
            else:
                config[name][key] = str(entry)
