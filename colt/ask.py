import configparser
#
from .answers import SubquestionsAnswer
from .config import ConfigParser
from .questions import QuestionGenerator
from .questions import _Subquestions, _Questions, _ConcreteQuestion
from .questions import parse_question


class AskQuestions:
    """Main Object to handle question request"""

    __slots__ = ("name", "literals", "questions", "answers", "only_check", "_check_failed")

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
        questions = questions.questions
        #
        self.answers = None
        self.name = name
        self.questions = self._setup(questions, config)
        #
        self.only_check = False
        self._check_failed = False

    @classmethod
    def questions_from_file(cls, name, filename, config=None):
        with open(filename, "r") as f:
            txt = f.read()
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

    def check_only(self, filename):
        self.only_check = True
        answers = self.questions.ask()
        if self._check_failed is True:
            filename = filename + "__check"
            self.create_config_from_answers(filename, answers)
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

    def set_answers_from_file(self, filename):
        """Set answers from a given file"""
        parsed, self.literals = ConfigParser.read(filename, self.literals)
        for section, values in parsed.items():
            if section == ConfigParser.base:
                name = ""
            else:
                name = section
            question = QuestionGenerator.get_node_from_tree(name, self.questions)
            if question is None:
                print(f"""Section = {section} unknown, maybe typo?""")
                continue
            if isinstance(question, _ConcreteQuestion):
                print(f"""Section '{section}' is concrete question, maybe typo?""")
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
                except SystemExit:
                    print(f"""In Section({section}) key({key}) unknown, maybe typo?""")

    def _actual_modifyer(self, question, answer):
        question.set_answer(question, answer)

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
