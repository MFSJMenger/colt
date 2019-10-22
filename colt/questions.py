from abc import ABC, abstractmethod
from collections import namedtuple

from .parser import LineParser
from .answers import SubquestionsAnswer
import configparser


__all__ = ["Question", "ConditionalQuestion", "AskQuestions", "register_parser"]


Question = namedtuple("Question", ("question", "typ", "default"),
                      defaults=("", "str", None))
ConditionalQuestion = namedtuple("ConcreteQuestion", ("name", "main", "subquestions"))


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
        self.name = name
        self.questions = self._setup(questions, config)
        self.configparser = configparser.ConfigParser(allow_no_value=True)

    def ask(self, filename=None):
        answers = self.questions.ask()
        if filename is not None:
            self.create_config(self.configparser, self.name, answers)
            self._write(filename)
        self.answers = answers
        return answers

    def _setup(self, questions, config):
        """setup questions and read config file in case a default file is give"""
        questions = _parse_question(questions)

        if config is not None:
            cparser = configparser.ConfigParser(allow_no_value=True)
            cparser.read(config)
            #
            self._modify(self.name, cparser, questions)
        return questions

    def _write(self, filename):
        """write output to file"""
        with open(filename, 'w') as configfile:
            self.configparser.write(configfile)

    @staticmethod
    def _modify(name, config, questions):
        """set answers depending on the config file!"""
        if isinstance(questions, _Subquestions):
            if config[name].get(questions.name, None) is not None:
                questions.set_answer(config[name][questions.name])
                AskQuestions._modify_questions(
                        f"{name}::{questions.name}({config[name][questions.name]})",
                        config, questions.subquestions)
        else:
            AskQuestions._modify_questions(name, config, questions)

    @staticmethod
    def _modify_questions(name, config, questions):
        """ recusive function to set answer depending on the config file!"""
        # check that config[name] is defined!
        try:
            config[name]
        except Exception:
            return questions
        #
        for key, question in questions.items():
            if isinstance(question, _Questions):
                AskQuestions._modify_questions(f"{name}", config, question.questions)
            elif isinstance(question, _ConcreteQuestion):
                if config[name].get(key, None) is not None:
                    question.set_answer(config[name][key])
            elif isinstance(question, _Subquestions):
                if config[name].get(question.name, None) is not None:
                    question.set_answer(config[name][question.name])
                    AskQuestions._modify_questions(
                            f"{name}::{question.name}({config[name][question.name]})",
                            config, question.subquestions)
            else:
                raise TypeError("Type of question not known!", question)

    @staticmethod
    def create_config(config, name, entries):
        """create config file"""
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
                config[name][key] = entry


class _QuestionBase(ABC):

    def __init__(self):
        self._set_answer = None

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
            'ilist': LineParser.ilist_parser,
            'bool': LineParser.bool_parser,
    }

    def __init__(self, question):
        # setup
        _QuestionBase.__init__(self)
        self._setup(question)
        self._parser = self._select_parser(question.typ)
        # generate the question
        self.question = self._generate_question(question)

    def __repr__(self):
        return f"{self.question}\n"

    def __str__(self):
        return f"{self.question}\n"

    def set_answer(self, value):
        self._set_answer = value

    def _generate_question(self, question):
        txt = question.question.strip()
        # add default option
        if question.default is not None:
            txt += " [%s]" % (str(self.default))
        return txt + ": "

    def _setup(self, question):
        self.default = None
        self._accept_enter = False
        if question.default is not None:
            self._accept_enter = True
            self.default = question.default

    def _print(self):
        return f"{self.question}\n"

    def _ask_question(self):
        #
        default = False
        if self._set_answer is not None:
            answer = self._set_answer
        else:
            answer = input(self.question).strip()
            if answer == "":
                if self._accept_enter:
                    answer = self.default
                    default = True
        #
        return answer, default

    def _ask(self):
        answer, default = self._ask_question()
        if default is True:
            return answer
        #
        try:
            if answer == "":
                raise Exception("No default set, empty string not allowed!")
            result = self._parser(answer)
        except Exception:
            print(f"Unkown input '{answer}', redo")
            result = self._ask()
        return result

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


class _Questions(_QuestionBase):

    def __init__(self, questions):
        _QuestionBase.__init__(self)
        self.questions = {name: _parse_question(question) for (name, question) in questions.items()}

    def items(self):
        return self.questions.items()

    def set_answer(self, value):
        raise Exception("For _Questions class no set_answer possible at the moment!")

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

    def __init__(self, name, main_question, questions):
        _QuestionBase.__init__(self)
        # main question
        self.name = name
        self.main_question = _ConcreteQuestion(main_question)
        # subquestions
        self.subquestions = {name: _parse_question(question) for name, question in questions.items()}

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


def _parse_question(question):

    if isinstance(question, dict):
        result = _Questions(question)
    elif isinstance(question, Question):
        result = _ConcreteQuestion(question)
    elif isinstance(question, ConditionalQuestion):
        result = _Subquestions(question.name, question.main, question.subquestions)
    else:
        raise TypeError("Type of question not known!", question)
    return result
