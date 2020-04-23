import os
#
from functools import wraps
#
from .answers import SubquestionsAnswer, Answers
from .generator import GeneratorNavigator
from .config import ConfigParser
from .questions import QuestionGenerator, ValidatorErrorNotInChoices
from .questions import Subquestions, Questions, ConcreteQuestion, LiteralBlock, LiteralBlockString
from .questions import parse_question
from .exceptions import ErrorSettingAnswerFromFile, ErrorSettingAnswerFromDict


def with_attribute(attr, value):
    def _class_function(func):
        @wraps(func)
        def _inner(self, *args, **kwargs):
            if hasattr(self, attr):
                old = getattr(self, attr)
                delete = False
            else:
                delete = True
            setattr(self, attr, value)
            val = func(self, *args, **kwargs)
            if delete is False:
                setattr(self, attr, old)
            return val
        return _inner
    return _class_function


class AskQuestions(GeneratorNavigator):
    """Main Object to handle question request"""

    __slots__ = ("literals", "questions", "answers",
                 "is_only_checking", "check_failed", '_no_failure_setting_answers')

    def __init__(self, questions, config=None):
        """Main Object to handle question request

        Args:
            questions (obj):
                Questions object, can be
                          1) Dict, dictionary object
                          2) ConditionalQuestion, a conditional question
                          3) Question, a concrete question
                          From there the real questions will be generated!

        Kwargs:
            config (str), optional:
                None, a single or multiple configfiles
                from which default answers are set!
        """
        questions = QuestionGenerator(questions)
        self._blocks = list(questions.keys())
        self.literals = questions.literals
        #
        self.answers = None
        # setup
        self.questions = self._setup(questions, config)
        #
        self.is_only_checking = False
        self.check_failed = False
        self._no_failure_setting_answers = True

    @classmethod
    def questions_from_file(cls, filename, config=None):
        with open(filename, "r") as fhandle:
            txt = fhandle.read()
        return cls(txt, config)

    def ask(self, filename=None):
        """ask the actual question"""
        answers = self.questions.ask()
        if filename is not None:
            self.create_config_from_answers(filename, answers)
        self.answers = answers
        return answers

    def get_node(self, key):
        return self.get_node_from_tree(key, self.questions)

    @with_attribute('is_only_checking', True)
    def get_not_set_answers(self):
        answers = Answers(self.questions.ask(), self._blocks, do_check=False)
        return answers.get_not_defined_answers()

    @with_attribute('is_only_checking', True)
    def get_answers_unchecked(self):
        return Answers(self.questions.ask(), self._blocks, do_check=False)

    @with_attribute('is_only_checking', True)
    def get_answers_and_not_set(self):
        answers = Answers(self.questions.ask(), self._blocks, do_check=False)
        return answers, answers.get_not_defined_answers()

    def create_config_from_answers(self, filename, answers):
        """Create a config from defined answers"""
        if answers is None:
            return
        default_name = '__DEFAULT__ANSWERS__'
        answers = self._unfold_answers(answers, default_name)
        with open(filename, 'w') as f:
            ""
            f.write("\n".join(answer for key, answerdct in answers.items()
                              for answer in answer_iter(key, answerdct, default_name)))
                    

    @with_attribute('is_only_checking', True)
    def check_only(self, filename=None):
        if filename is not None:
            self.set_answers_from_file(filename)
        return Answers(self.questions.ask(), self._blocks, filename=filename)

    def set_answers_from_file(self, filename):
        errmsg = self._set_answers_from_file(filename)
        if errmsg is not None:
            raise ErrorSettingAnswerFromFile(filename, errmsg)

    def set_answers_from_dct(self, dct):
        errmsg = self._set_answers_from_dct(dct)
        if errmsg is not None:
            raise ErrorSettingAnswerFromDict(errmsg)

    @staticmethod
    def is_concrete_question(value):
        return isinstance(value, ConcreteQuestion)

    @staticmethod
    def is_literal_block(value):
        return isinstance(value, LiteralBlock)

    @staticmethod
    def is_question_block(value):
        return isinstance(value, Questions)

    @staticmethod
    def is_subquestion_block(value):
        return isinstance(value, Subquestions)

    def _setup(self, questions, config):
        """setup questions and read config file in case a default file is give"""
        self.questions = parse_question(questions.questions, parent=self)
        #
        if config is not None:
            if os.path.isfile(config):
                self.set_answers_from_file(config)
        return self.questions

    def _set_answer(self, section, key, question, answer):
        try:
            question.set_answer(answer)
            return ""
        except ValueError:
            self._no_failure_setting_answers = False
            if question.typ == 'existing_file':
                return f"\n{key} = {answer}, File does not exist!"
            return f"\n{key} = {answer}, ValueError expected: '{question.typ}'"
        except ValidatorErrorNotInChoices:
            self._no_failure_setting_answers = False
            return (f"\n{key} = {answer}, Wrong Choice: can only be"
                    f"({', '.join(str(choice) for choice in question.choices)})")

    def _set_answers_from_file(self, filename):
        """Set answers from a given file"""
        try:
            parsed, self.literals = ConfigParser.read(filename, self.literals)
        except FileNotFoundError:
            return f"File '{filename}' not found!"
        return self._set_answers_from_dct(parsed)

    @with_attribute('_no_failure_setting_answers', True)
    def _set_answers_from_dct(self, parsed):
        errstr = ""
        for section in parsed:
            if section == ConfigParser.base:
                name = ""
                error = ""
            else:
                name = section
                error = f'[{section}]'
            errmsg = ""
            #
            question = self.get_node_from_tree(name, self.questions)
            #
            if question is None:
                print(f"""Section = {section} unknown, maybe typo?""")
            elif isinstance(question, ConcreteQuestion):
                print(f"""Section '{section}' is concrete question, maybe typo?""")
            elif isinstance(question, Subquestions):
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
            elif isinstance(question, Questions):
                for key, value in parsed[section].items():
                    concre_question = question[key]
                    if concre_question is None:
                        errmsg += f"\n{key} = UNKNOWN"
                    else:
                        errmsg += self._set_answer(section, key, concre_question, value)
            else:
                print(f'Unkown type...')

            if errmsg != "":
                errstr += f"{error}{errmsg}\n"

        if errstr == "":
            return None
        return errstr

    @classmethod
    def _unfold_answers(cls, answers, default_name):
        """unfold answers dct of dcts to a single dct
           with the config header as keys
        """


        result = {}
        if isinstance(answers, SubquestionsAnswer):
            result[default_name] = {}
            if isinstance(answers.value, list):
                result[default_name][answers.name] = ", ".join(str(ele) for ele in answers.value)
            else:
                result[default_name][answers.name] = str(answers.value)
            result.update(cls._unfold_answers_helper(cls.join_keys(answers.name, answers.value), answers))
        else:
            result.update(cls._unfold_answers_helper(default_name, answers, default_name))
        return result

    @classmethod
    def _unfold_answers_helper(cls, name, answers, default_name='__DEFAULT__ANSWERS__'):
        result = {}
        result[name] = {}
        default = result[name]
        if name == default_name:
            name = f""

        for key, answer in answers.items():
            if isinstance(answer, SubquestionsAnswer):
                default[key] = str(answer.value)
                result.update(cls._unfold_answers_helper(cls.join_keys(name, cls.join_case(key, answer.value)), answer))
            elif isinstance(answer, LiteralBlockString):
                result[cls.join_keys(name, key)] = answer
            elif isinstance(answer, dict):
                result.update(cls._unfold_answers_helper(cls.join_keys(name, key), answer))
            elif isinstance(answer, list):
                default[key] = ", ".join(str(ele) for ele in answer)
            else:
                default[key] = str(answer)
        return result


def answer_iter(name, dct, default_name):

    if name != default_name:
        yield f'[{name}]'
    else:
        yield ''

    if isinstance(dct, LiteralBlockString):
        yield dct.data
    else:
        for name, value in dct.items():
            yield f"{name} = {value}"
        yield ''
