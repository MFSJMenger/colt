from collections.abc import Mapping
import configparser
from functools import wraps
import sys
#
from .answers import SubquestionsAnswer
from .config import ConfigParser
from .questions import QuestionGenerator, WrongChoiceError
from .questions import _Subquestions, _Questions, _ConcreteQuestion
from .questions import parse_question


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


class AskQuestions(Mapping):
    """Main Object to handle question request"""

    __slots__ = ("name", "literals", "questions", "answers",
                 "only_checking", "check_failed", '_no_failure_setting_answers')

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
        self.only_checking = False
        self.check_failed = False
        self._no_failure_setting_answers = True

    @classmethod
    def questions_from_file(cls, name, filename, config=None):
        with open(filename, "r") as fhandle:
            txt = fhandle.read()
        return cls(name, txt, config)

    def ask(self, filename=None):
        """ask the actual question"""
        answers = self.questions.ask()
        if filename is not None:
            self.create_config_from_answers(filename, answers)
        self.answers = answers
        return answers

    def create_config_from_answers(self, filename, answers):
        """Create a config from defined answers"""
        if answers is None:
            return
        default_name = '__DEFAULT__ANSWERS__'
        answers = self._unfold_answers(answers, default_name)
        with open(filename, 'w') as f:
            f.write('\n'.join(answer for key, answerdct in answers.items() for answer in answeriter(key, answerdct, default_name)))

    @with_attribute('only_checking', True)
    def check_only(self, filename=None):
        if filename is not None:
            self.set_answers_from_file(filename)
        return self.questions.ask()

    def __getitem__(self, key):
        return self.questions.get(key, None)

    def __len__(self):
        return len(self.questions)

    def __iter__(self):
        return iter(self.questions)

    def set_answers_from_file(self, filename):
        errmsg = self._set_answers_from_file(filename)
        if errmsg is not None:
            print(f'Error parsing file: {filename}')
            print(errmsg)
            sys.exit()

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
            if question.typ == 'existing_file':
                return f"\n{key} = {answer}, File does not exist!"
            return f"\n{key} = {answer}, ValueError expected: '{question.typ}'"
        except WrongChoiceError:
            self._no_failure_setting_answers = False
            return f"\n{key} = {answer}, Wrong Choice: can only be ({', '.join(str(choice) for choice in question.choices)})"

    @with_attribute('_no_failure_setting_answers', True)
    def _set_answers_from_file(self, filename):
        """Set answers from a given file"""
        errstr = ""
        parsed, self.literals = ConfigParser.read(filename, self.literals)
        #
        for section in parsed:
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
                errstr += f"{error}{errmsg}\n"

        if errstr == "":
            return None
        return errstr

    @classmethod
    def _fileparser(cls, filename=None):
        if filename is None:
            return configparser.ConfigParser(allow_no_value=True)
        parser = configparser.ConfigParser(allow_no_value=True)
        parser.read(filename)
        return parser

    @classmethod
    def _unfold_answers(cls, answers, default_name): 

        result = {}
        if isinstance(answers, SubquestionsAnswer):
            result[default_name] = {}
            if isinstance(answers.value, list):
                result[default_name][answers.name] = ", ".join(str(ele) for ele in answers.value)
            else:
                result[default_name][answers.name] = str(answers.value)
            result.update(cls._unfold_answers_helper(f"{answers.name}({answers.value})", answers))
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
                result.update(cls._unfold_answers_helper(f"{name}{key}({answer.value})", answer))
            elif isinstance(answer, dict):
                result.update(cls._unfold_answers_helper(f"{name}{key}", answer))
            elif isinstance(answer, list):
                default[key] = ", ".join(str(ele) for ele in answer)
            else:
                default[key] = str(answer)
        return result


def answeriter(name, dct, default_name):
    if name != default_name:
        yield f'[{name}]'
    else:
        yield f'\n'
    for name, value in dct.items():
        yield f"{name} = {value}"
    yield ''
