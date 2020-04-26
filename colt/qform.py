from abc import abstractmethod, ABC
from collections import UserDict
#
from .answers import SubquestionsAnswer
from .config import ConfigParser
from .generator import GeneratorNavigator
#
from .questions import QuestionGenerator
from .questions import Question, ConditionalQuestion, QuestionContainer
from .questions import LiteralBlockQuestion, LiteralBlockString
#
from .presets import PresetGenerator
from .validator import Validator, NOT_DEFINED
from .validator import ValidatorErrorNotChoicesSubset, ValidatorErrorNotInChoices
#
from .exceptions import ErrorSettingAnswerFromFile, ErrorSettingAnswerFromDict


class _QuestionsContainerBase(GeneratorNavigator):

    def __init__(self, name, parent):
        #
        self.name = name
        self.parent = parent
        # register block
        self.parent.blocks[name] = self

    @abstractmethod
    def get_answer(self, check=False):
        """get answer dict"""


class _ConcreteQuestionBase(ABC):

    def __init__(self, name, question, parent):
        self.name = name
        self._settings = self._generate_settings(name, question)
        self.parent = parent
        self.is_set = False

    @property
    def settings(self):
        self._settings.update(self._generate_dynamic_settings())
        return self._settings

    @abstractmethod
    def get_answer(self, check=False):
        """get answer"""

    @abstractmethod
    def preset(self, value, choices):
        """preset new value and choices!"""

    @abstractmethod
    def _generate_settings(self, name, question):
        """generate core settings"""

    @abstractmethod
    def _generate_dynamic_settings(self):
        """generate additional runtime dependent settings"""

    @staticmethod
    def generate_label(label):
        """generate a label"""
        return f"{label}: "


class LiteralBlock(_ConcreteQuestionBase):

    def __init__(self, name, question, parent):
        #
        self._blockname, self._name = GeneratorNavigator.rsplit_keys(name)
        #
        _ConcreteQuestionBase.__init__(self, name, question, parent)
        # register self
        self.parent.literals[name] = self
        self._answer = LiteralBlockString(None)

    @property
    def answer(self):
        answer = self.get_answer()
        if answer is NOT_DEFINED:
            return ""
        return LiteralBlockString(answer)

    @answer.setter
    def answer(self, value):
        self._answer = LiteralBlockString(value)
        self.is_set = True

    def preset(self, value, choices):
        raise Exception(f"preset not defined for Literalblock")

    def get_answer(self, check=False):
        if self._answer.is_none is True:
            return None
        return self._answer

    def _generate_dynamic_settings(self):
        if self._answer.is_none is True:
            return {"value": ""}
        return {"value": self._answer}

    def _generate_settings(self, name, question):
        return {"type": "literal",
                "label": self.generate_label(self._name)}


class ConcreteQuestion(_ConcreteQuestionBase):

    def __init__(self, name, question, parent):
        _ConcreteQuestionBase.__init__(self, name, question, parent)
        #
        self._value = Validator(question.typ, default=question.default, choices=question.choices)
        self._comment = question.comment
        self._label = question.question
        self.is_optional = question.is_optional

    def get_answer(self, check=False):
        """get answer back, if is optional, return None if NOT_DEFINED"""
        answer = self._value.get()
        if check is False:
            if answer is NOT_DEFINED and self.is_optional:
                return None
            return answer
        #
        if answer is NOT_DEFINED:
            if self.is_optional is False:
                self.parent.unset[self.name] = True
            return None
        return answer

    @property
    def answer(self):
        answer = self.get_answer()
        if answer is NOT_DEFINED:
            return ""
        return answer

    @answer.setter
    def answer(self, value):
        self._value.set(value)
        self.is_set = True

    def preset(self, value, choices):
        """preset new value, choices:
           important: first update choices to ensure that default in choices!
        """
        if choices is not None:
            self._value.choices = choices
            self._update_settings(choices)
        if value is not None:
            self._value.set(value)

    def _update_settings(self, choices):
        if self.settings['type'] != 'select':
            self._settings = self._select_form_settings(self.name, self._label,
                                                        choices, self.is_optional)
            return
        self._settings['options'] = choices

    @property
    def choices(self):
        return self._value.choices

    def _generate_dynamic_settings(self):
        return {"value": self.answer,
                "is_set": self.is_set}

    def _generate_settings(self, name, question):
        if question.choices is None:
            return self._input_form_settings(name, question.question,
                                             question.typ, question.is_optional)
        return self._select_form_settings(name, question.question,
                                          question.choices, question.is_optional)

    @staticmethod
    def _select_form_settings(name, label, options, is_optional):
        options = list(options)
        return {"type": "select",
                "label": label,
                "id": name,
                "options": options,
                'is_optional': is_optional,
                }

    @staticmethod
    def _input_form_settings(name, label, typ, is_optional):
        """get settings for input form"""
        return {"type": "input",
                "label": label,
                "id": name,
                "placeholder": typ,
                'is_optional': is_optional,
                }


class QuestionBlock(_QuestionsContainerBase, UserDict):

    def __init__(self, name, question, parent):
        _QuestionsContainerBase.__init__(self, name, parent)
        #
        UserDict.__init__(self)
        self.concrete, self.blocks = create_forms(name, question, parent)
        self.data = self.concrete

    def generate_setup(self):
        out = {self.name: {
            'fields': {quest.name: quest.settings for quest in self.concrete.values()},
            'previous': None}}
        #
        for blocks in self.blocks.values():
            out.update(blocks.generate_setup())
        #
        return out

    @property
    def answer(self):
        raise Exception("Answer not available for QuestionBlock")

    def get_answer(self, check=False):
        dct = {name: quest.get_answer(check=check) for name, quest in self.concrete.items()}
        dct.update({name: quest.get_answer(check=check) for name, quest in self.blocks.items()})
        return dct

    def setup_iterator(self):
        yield self.name, {
            'fields': {quest.name: quest.settings for quest in self.concrete.values()},
            'previous': None}

        for blocks in self.blocks.values():
            for ele in blocks.setup_iterator():
                yield ele

    def get_blocks(self):
        return sum((block.get_blocks() for block in self.blocks.values()),
                   [self.name])


class SubquestionBlock(_QuestionsContainerBase):

    def __init__(self, name, main_question, questions, parent):
        self._blockname, self._name = GeneratorNavigator.rsplit_keys(name)
        if self._name is None:
            self._name = self._blockname
            self._blockname = ""
        _QuestionsContainerBase.__init__(self, name, parent)
        #
        self.main_question = main_question
        #
        self.settings = {qname: QuestionBlock(self.join_case(name, qname), quest, parent)
                         for qname, quest in questions.items()}

    @property
    def is_optional(self):
        return self.main_question.is_optional

    def get_answer(self, check=False):
        answer = self.main_question.get_answer(check=check)
        if answer is NOT_DEFINED:
            return SubquestionsAnswer(self._name, answer, {})
        return SubquestionsAnswer(self._name, answer, self.settings[answer].get_answer(check=check))

    def setup_iterator(self):
        answer = self.answer
        if answer == "":
            return
        for ele in self.settings[answer].setup_iterator():
            yield ele

    def generate_setup(self):
        answer = self.answer
        if answer in ("", None):
            return {}
        return self.settings[answer].generate_setup()

    @property
    def answer(self):
        return self.main_question.answer

    @answer.setter
    def answer(self, value):
        self.main_question.answer = value

    def get_blocks(self):
        answer = self.answer
        if answer in ("", None):
            return []
        return self.settings[answer].get_blocks()

    def get_delete_blocks(self):
        return {block: None for block in self.get_blocks()}


def create_forms(name, questions, parent):
    concrete = {}
    blocks = {}
    for key, question in questions.items():
        qname = GeneratorNavigator.join_keys(name, key)
        if isinstance(question, Question):
            concrete[key] = ConcreteQuestion(qname, question, parent)
        elif isinstance(question, QuestionContainer):
            blocks[key] = QuestionBlock(qname, question, parent)
        elif isinstance(question, ConditionalQuestion):
            concrete[key] = ConcreteQuestion(qname, question.main, parent)
            blocks[key] = SubquestionBlock(qname, concrete[key], question, parent)
        elif isinstance(question, LiteralBlockQuestion):
            concrete[key] = LiteralBlock(qname, question, parent)
        else:
            raise TypeError("Type of question not known!", type(question))
    return concrete, blocks


class QuestionForm:

    def __init__(self, questions):
        questions = QuestionGenerator(questions).tree
        #
        self.blocks = {}
        # literal blocks
        self.literals = {}
        # not set variables
        self.unset = {}
        # generate QuestionBlock
        self.form = QuestionBlock("", questions, self)

    def set_answer_f(self, name, answer):
        if answer == "":
            return False
        block, key = self._split_keys(name)
        #
        block.concrete[key].answer = answer
        return True

    def set_answer(self, name, answer):
        if answer == "":
            return False
        #
        block, key = self._split_keys(name)
        #
        try:
            block.concrete[key].answer = answer
            is_set = True
        except ValueError:
            is_set = False
        except ValidatorErrorNotInChoices:
            is_set = False
        #
        return is_set

    def update_select(self, name, answer):
        out = {'delete': {}, 'setup': {}}
        if answer == "":
            return out
        block, key = self._split_keys(name)
        if key in block.blocks:
            block = block.blocks[key]
            if block.answer == answer:
                return out
            out['delete'] = block.get_delete_blocks()
            #
            block.answer = answer
            out['setup'] = block.generate_setup()
        else:
            block.concrete[key].answer = answer
        return out

    def get_answer(self, check=False):
        return self.form.get_answer(check=check)

    def generate_setup(self, presets=None):
        if presets is not None:
            self._set_presets(presets)
        return self.form.generate_setup()

    def setup_iterator(self, presets=None):
        if presets is not None:
            self._set_presets(presets)
        return self.form.setup_iterator()

    def get_answers(self, check=True):
        if check is False:
            return self.form.get_answer()
        self.unset = {}
        answers = self.form.get_answer(check=True)
        if self.unset != {}:
            raise Exception('answer need to be set..')
        del self.unset
        return answers

    def write_config(self, filename):
        """ get a linear config and write it to the file"""
        config = {}
        for blockname in self.form.get_blocks():
            config[blockname] = {key: question.answer
                                 for key, question in self.blocks[blockname].concrete.items()}

        default_name = ''
        with open(filename, 'w') as fhandle:
            fhandle.write("\n".join(answer for key, answers in config.items()
                                    for answer in answer_iter(key, answers, default_name)))

    def set_answers_from_file(self, filename):
        errmsg = self._set_answers_from_file(filename)
        if errmsg is not None:
            raise ErrorSettingAnswerFromFile(filename, errmsg)

    def set_answers_from_dct(self, dct):
        errmsg = self._set_answers_from_dct(dct)
        if errmsg is not None:
            raise ErrorSettingAnswerFromDict(errmsg)

    def _set_presets(self, presets):
        """reset some of the question possibilites"""
        presets = PresetGenerator(presets).tree
        #
        for blockname, fields in presets.items():
            if blockname not in self.blocks:
                print(f"Unknown block {blockname} in presets, continue")
                continue
            block = self.blocks[blockname]
            for key, preset in fields.items():
                if key not in block:
                    print(f"Unknown key {key} in {blockname} in presets, continue")
                    continue
                try:
                    block[key].preset(preset.default, preset.choices)
                except ValidatorErrorNotChoicesSubset:
                    print((f"Could not update choices in '{blockname}' entry '{key}' as choices ",
                           "not subset of previous choices, continue"))

    def _set_answers_from_file(self, filename):
        """Set answers from a given file"""
        try:
            parsed, self.literals = ConfigParser.read(filename, self.literals)
        except FileNotFoundError:
            return f"File '{filename}' not found!"
        return self._set_answers_from_dct(parsed)

    def _set_answers_from_dct(self, dct):
        #
        errstr = ""
        #
        for blockname, answers in dct.items():
            if blockname == ConfigParser.base:
                blockname = ""

            if blockname not in self.blocks:
                if blockname in self.literals:
                    self.literals[blockname].answer = answers
                    continue
                print(f"""Section = {blockname} unknown, maybe typo?""")
                continue

            errstr += self._set_block_answers(blockname, answers)
        #
        if errstr == "":
            return None
        return errstr

    def _set_block_answers(self, blockname, answers):
        if blockname != "":
            error = f"[{blockname}]"
        else:
            error = ""

        errmsg = ""
        block = self.blocks[blockname]
        for key, answer in answers.items():
            if key not in block:
                print("key not known")
                continue
            try:
                block[key].answer = answer
            except ValueError:
                errmsg += f"\n{key} = {answer}, ValueError expected: '{block[key].typ}'"
            except ValidatorErrorNotInChoices:
                errmsg += (f"\n{key} = {answer}, Wrong Choice: can only be"
                           f"({', '.join(str(choice) for choice in block[key].choices)})")
        if errmsg != "":
            return error + errmsg
        return ""

    def _split_keys(self, name):
        block, key = GeneratorNavigator.rsplit_keys(name)
        if key is None:
            key = block
            block = ""

        if block not in self.blocks:
            raise Exception("block unknown")

        return self.blocks[block], key


def answer_iter(name, dct, default_name):
    if isinstance(dct, LiteralBlockString):
        if dct.is_none is True:
            return

    if name != default_name:
        yield f'[{name}]'
    else:
        yield ''

    if isinstance(dct, LiteralBlockString):
        yield dct.data
    else:
        for _name, _value in dct.items():
            yield f"{_name} = {_value}"
        yield ''
