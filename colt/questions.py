import re
from abc import ABC, abstractmethod
from collections import namedtuple

from .parser import LineParser
from .answers import SubquestionsAnswer
from .context_utils import ExitOnException
import configparser


__all__ = ["Question", "ConditionalQuestion", "AskQuestions", "register_parser"]


Question = namedtuple("Question", ("question", "typ", "default"),
                      defaults=("", "str", None))

class ConditionalQuestion(object):

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

    def __contains__(self, key):
        return key in self.subquestions

    def __str__(self):
        return f"ConditionalQuestion(name = {self.name}, main = {self.main}, subquestions = {self.subquestions}"

    def __repr__(self):
        return f"ConditionalQuestion(name = {self.name}, main = {self.main}, subquestions = {self.subquestions}"

# ConditionalQuestion = namedtuple("ConditionalQuestion", ("name", "main", "subquestions"))


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
        self._config = config
        self.questions = self._setup(questions, config)
        self.configparser = self._fileparser()
        #
        self.only_check = False
        self._check_failed = False

    def ask(self, filename=None):
        answers = self.questions.ask()
        if filename is not None:
            self._create_config_start(self.configparser, self.name, answers)
            self._write(filename)
        self.answers = answers
        return answers

    def check_only(self, filename):
        self.only_check = True
        answers = self.questions.ask()
        if self._check_failed is True:
            self._create_config_start(self.configparser, self.name, answers)
            self._write(filename)
            raise Exception(f"Input not complete, check file '{filename}' for missing values!")
        self.only_check = False

    def __getitem__(self, key):
        return self.questions.get(key, None)

    def __repr__(self):
        return f"AskQuestions({self.name}, config='{self._config}')"

    def _setup(self, questions, config):
        """setup questions and read config file in case a default file is give"""
        self.questions = _parse_question(questions, parent=self)
        if config is not None:
            self.set_answers_from_file(config)
        return self.questions

    _parse_conditionals_helper = re.compile(r"(?P<key>.*)\((?P<decission>.*)\)")

    _Conditionals = namedtuple("Conditionals", ["key", "decission"])

    @classmethod
    def _parse_conditionals(cls, block):
        """check if conditional block, else return name of the key and the decission"""
        result = cls._parse_conditionals_helper.match(block)
        if result is None:
            return None
        return cls._Conditionals(result.group("key"), result.group("decission"))

    @classmethod
    def _get_question_block(cls, questions, block):
        """Parse down the abstraction tree to extract
           particular questions based on their
           block name in the config file
        """
        old_block, delim, new_block = block.partition('::')
        if new_block == "":
            # end of the recursive function
            return questions, old_block
        # Check for conditionals
        block_key, _, _ = new_block.partition('::')
        conditionals = cls._parse_conditionals(block_key)
        # 
        if conditionals is None:
            return cls._get_question_block(questions[block_key], new_block)
        # Handle conditionals
        code, decission = conditionals
        return cls._get_question_block(questions[code][decission], new_block)

    def set_answers_from_file(self, filename):
        """Set answers from a given file"""
        parsed = self._fileparser(filename)
        for section in parsed.sections():
            question, se = self._get_question_block(self.questions, section)
            if question is None:
                print(f"""Section = {section} unkown, maybe typo?""")
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
                config[name][key] = entry


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
            'ilist': LineParser.ilist_parser,
            'flist': LineParser.flist_parser,
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

    def set_answer(self, value):
        """set the answer to a suitable value, also here parse is called!
           only consistent inputs values are accepted 
        """

        # also kinda useless, as the question is never ask, but conceptionally correct ;)
        self._accept_enter = True
        # this is kinda a hack to ensure that the provided config 
        # file is correct, 
        with ExitOnException():
            self._set_answer = self._parse(f"{value}")

    def _generate_question(self, question):
        txt = question.question.strip()
        # add default option
        if question.default is not None:
            txt += " [%s]" % (str(self.default))
        return txt + ": "

    def _setup(self, question):
        self._default = None
        self._accept_enter = False
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
        if self._set_answer is not None:
            answer = self._set_answer
            is_set = True
        else:
            answer = input(self.question).strip()  # strip is important!
            if answer == "":
                if self._accept_enter:
                    answer = self.default
                    is_set = True
        #
        return _Answer(answer, is_set)

    def _ask_implementation(self):
        """Helper routine that checks if an answer is set,
           else, tries to parse the answer, if that fails
           the question is ask again
        """
        answer = self._ask_question()
        if answer.is_set is True:
            # if answer is set, return unparsed answer
            return answer.value
        #
        try:
            if answer.value == "":
                raise Exception("No default set, empty string not allowed!")
            result = self._parse(answer.value)
        except Exception:
            print(f"Unkown input '{answer}', redo")
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
        self.questions = {name: _parse_question(question, parent=self.parent) for (name, question) in questions.items()}

    def items(self):
        return self.questions.items()
    
    def __getitem__(self, key):
        return self.questions.get(key, None)

    def get(self, key, default=None):
        return self.questions.get(key, None)

    def __contains__(self, key):
        return key in self.questions

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

    def __init__(self, name, main_question, questions, parent=None):
        _QuestionBase.__init__(self, parent)
        # main question
        self.name = name
        self.main_question = _ConcreteQuestion(main_question, parent=self.parent)
        # subquestions
        self.subquestions = {name: _parse_question(question, parent=self.parent)
                             for name, question in questions.items()}

    def __getitem__(self, key):
        return self.subquestions.get(key, None)

    def get(self, key, default=None):
        return self.subquestions.get(key, None)

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


def _parse_question(question, parent=None):

    if isinstance(question, dict):
        result = _Questions(question, parent=parent)
    elif isinstance(question, Question):
        result = _ConcreteQuestion(question, parent=parent)
    elif isinstance(question, ConditionalQuestion):
        result = _Subquestions(question.name, question.main, question.subquestions, parent=parent)
    else:
        raise TypeError("Type of question not known!", question)
    return result
