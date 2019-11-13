from collections import namedtuple
from .answers import SubquestionsAnswer
from .context_utils import ExitOnException
from .parser import LineParser
from abc import ABC, abstractmethod

Question = namedtuple("Question", ("question", "typ", "default", "choices", "comment"),
                      defaults=("", "str", None, None, None))


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

    def __setitem__(self, key, value):
        self.subquestions[key] = value

    def __contains__(self, key):
        return key in self.subquestions

    def __str__(self):
        return (f"ConditionalQuestion(name = {self.name},"
                f" main = {self.main}, subquestions = {self.subquestions}")

    def __repr__(self):
        return (f"ConditionalQuestion(name = {self.name},"
                f" main = {self.main}, subquestions = {self.subquestions}")


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
            'ilist_np': LineParser.ilist_np_parser,
            'flist': LineParser.flist_parser,
            'flist_np': LineParser.flist_np_parser,
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
        if question.choices is not None:
            txt += ", choices = (%s)" % (", ".join(question.choices))
        return txt + ": "

    def set_choices(self, choices):
        try:
            self._choices = [self._parse(choice) for choice in choices]
        except:
            pass

    def _setup(self, question):
        self._default = None
        self._accept_enter = False
        self._comment = question.comment
        # Try to set choices
        try:
            self._choices = [self._parse(choice) for choice in question.choices]
        except:
            self._choices = None

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

    def _perform_questions(self):
        answer = self._ask_question()
        if any(answer.value == helper for helper in (":help", ":h")):
            print(self._comment)
            # reask
            answer = self._perform_questions()
        return answer

    def _ask_implementation(self):
        """Helper routine that checks if an answer is set,
           else, tries to parse the answer, if that fails
           the question is ask again
        """
        answer = self._perform_questions()

        if answer.is_set is True:
            # if answer is set, return unparsed answer
            return answer.value
        #
        try:
            if answer.value == "":
                raise Exception("No default set, empty string not allowed!")
            result = self._parse(answer.value)
        except Exception:
            print(f"Unknown input '{answer.value}', redo")
            # reask
            result = self._ask_implementation()

        if self._choices is not None:
            if result not in self._choices:
                print(f"answer({result}) has to be ({', '.join(self._choices)})")
                # reask
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
        self.questions = {name: parse_question(question, parent=self.parent)
                          for (name, question) in questions.items()}

    def items(self):
        return self.questions.items()

    def __getitem__(self, key):
        return self.questions.get(key, None)

    def get(self, key, default=None):
        return self.questions.get(key, None)

    def __contains__(self, key):
        return key in self.questions

    def set_answer(self, value):
        raise Exception("For _Questions class no set_answer is possible at the moment!")

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

    def get(self, key, default=None):
        return self.subquestions.get(key, None)

    def __contains__(self, key):
        return key in self.subquestions

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


def parse_question(question, parent=None):

    if isinstance(question, dict):
        result = _Questions(question, parent=parent)
    elif isinstance(question, Question):
        result = _ConcreteQuestion(question, parent=parent)
    elif isinstance(question, ConditionalQuestion):
        result = _Subquestions(question.name, question.main, question.subquestions, parent=parent)
    else:
        raise TypeError("Type of question not known!", question)
    return result
