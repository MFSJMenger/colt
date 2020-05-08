from abc import abstractmethod, ABC
from collections import UserDict
from collections.abc import Mapping
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
from .validator import Validator, NOT_DEFINED, file_exists
from .validator import ValidatorErrorNotChoicesSubset, ValidatorErrorNotInChoices
from .validator import StringList, Choices, RangeExpression
#
from .exceptions import ErrorSettingAnswerFromFile, ErrorSettingAnswerFromDict


def is_existing_file(config):
    try:
        config = file_exists(config)
        return True
    except ValueError:
        return False


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
    """Logic of each actual question

       acts also as a StringVar used in tkinter, as it makes a lot of logic simpler
       it uses therefore callback functions, to perform actions.
    """
    __slots__ = ("name", "parent", "is_set", "accept_empty", "_callbacks")

    def __init__(self, name, parent, accept_empty=False, callbacks=None):
        self.name = name
        self.parent = parent
        self.is_set = False
        self.accept_empty = accept_empty
        self._callbacks = callbacks

    def set(self, answer):
        """ Handle all set events """
        if answer == "":
            if self.accept_empty is False:
                self._callbacks['EmptyEntry'](answer, self.settings)
            return self.accept_empty
        #
        try:
            self.answer = answer
            return True
        except ValueError:
            self._callbacks['ValueError'](answer, self.settings)
        except ValidatorErrorNotInChoices:
            self._callbacks['WrongChoice'](answer, self.settings)
        return False

    def get(self):
        return self.answer

    @property
    def settings(self):
        """settings"""
        settings = self._generate_settings()
        settings.update(self._generate_dynamic_settings())
        if self._callbacks is not None:
            settings.update({"self": self})
        return settings

    @abstractmethod
    def get_answer(self, check=False):
        """get answer"""

    @abstractmethod
    def preset(self, value, choices):
        """preset new value and choices!"""

    @abstractmethod
    def _generate_settings(self):
        """generate core settings"""

    @abstractmethod
    def _generate_dynamic_settings(self):
        """generate additional runtime dependent settings"""

    @staticmethod
    def generate_label(label):
        """generate a label"""
        return f"{label}: "


class LiteralBlock(_ConcreteQuestionBase):

    __slots__ = ("_blockname", "_name", "_answer")

    def __init__(self, name, parent, callbacks=None):
        #
        self._blockname, self._name = GeneratorNavigator.rsplit_keys(name)
        #
        _ConcreteQuestionBase.__init__(self, name, parent, accept_empty=True, callbacks=callbacks)
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

    def _generate_settings(self):
        return {"type": "literal",
                "label": self.generate_label(self._name)}


class ConcreteQuestion(_ConcreteQuestionBase):

    __slots__ = ("_value", "_comment", "name", "question", "typ", "is_optional")

    def __init__(self, name, question, parent, callbacks=None):
        _ConcreteQuestionBase.__init__(self, name, question, parent, callbacks=callbacks)
        #
        self._value = Validator(question.typ, default=question.default, choices=question.choices)
        self.name = name
        #
        if question.comment is NOT_DEFINED:
            self._comment = None
        else:
            self._comment = question.comment
        #
        self.question = question.question
        self.typ = question.typ

        self.is_optional = question.is_optional
        # check if accept_empty is true
        self.accept_empty = (self._value.get() is not NOT_DEFINED or self.is_optional)

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
    def comment(self):
        return self._comment

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

    @property
    def choices(self):
        return self._value.choices

    def set_answer(self, value):
        self._value.set(value)
        self.is_set = True

    def preset(self, value, choices):
        """preset new value, choices:
           important: first update choices to ensure that default in choices!
        """
        if choices is not None:
            self._value.choices = choices
            self._update_settings(choices)
            #
            answer = self._value.get()
            #
            if answer is NOT_DEFINED:
                self.is_set = False
        if value is not None:
            self._value.set(value)

    def _update_settings(self, choices):
        if self.settings['type'] != 'select':
            self._settings = self._select_form_settings(self.name, self._label,
                                                        choices, self.is_optional)
        self._settings['options'] = str(self._value.choices)

    @property
    def choices(self):
        return self._value.choices

    def _generate_dynamic_settings(self):
        return {"value": self.answer,
                "is_set": self.is_set,
                }

    def _generate_settings(self):
        choices = self.choices
        if isinstance(choices, Choices):
            return self._select_form_settings()
        if isinstance(choices, RangeExpression):
            return self._input_form_settings(placeholder=f"{self.typ}, {choices.as_str()}")
        return self._input_form_settings(placeholder=self.typ)

    def _select_form_settings(self):
        return {"type": "select",
                "label": self.question,
                "id": self.name,
                "options": self.choices.as_list(),
                "is_optional": self.is_optional,
                "typ": self.typ,
                "comment": self.comment,
                }

    def _input_form_settings(self, placeholder=''):
        """get settings for input form"""
        return {"type": "input",
                "label": self.question,
                "id": self.name,
                "placeholder": placeholder,
                "is_optional": self.is_optional,
                "typ": self.typ,
                "comment": self.comment,
                }


class QuestionBlock(_QuestionsContainerBase, UserDict):

    def __init__(self, name, question, parent, callbacks=None):
        _QuestionsContainerBase.__init__(self, name, parent)
        #
        UserDict.__init__(self)
        self.concrete, self.blocks = create_forms(name, question, parent, callbacks)
        self.data = self.concrete

    @property
    def is_set(self):
        return all(question.is_set for question in self.concrete.values())

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

    def __init__(self, name, main_question, questions, parent, callbacks=None):
        self._blockname, self._name = GeneratorNavigator.rsplit_keys(name)
        if self._name is None:
            self._name = self._blockname
            self._blockname = ""
        _QuestionsContainerBase.__init__(self, name, parent)
        #
        self.main_question = main_question
        #
        self.settings = {qname: QuestionBlock(self.join_case(name, qname),
                                              quest, parent, callbacks=callbacks)
                         for qname, quest in questions.items()}

    @property
    def is_optional(self):
        return self.main_question.is_optional

    def get_answer(self, check=False):
        answer = self.main_question.get_answer(check=check)
        if answer is NOT_DEFINED:
            return SubquestionsAnswer(self._name, answer, {})
        return SubquestionsAnswer(self._name, answer,
                                  self.settings[answer].get_answer(check=check))

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


def create_forms(name, questions, parent, callbacks):
    concrete = {}
    blocks = {}
    for key, question in questions.items():
        qname = GeneratorNavigator.join_keys(name, key)
        if isinstance(question, Question):
            concrete[key] = ConcreteQuestion(qname, question, parent, callbacks=callbacks)
        elif isinstance(question, QuestionContainer):
            blocks[key] = QuestionBlock(qname, question, parent, callbacks=callbacks)
        elif isinstance(question, ConditionalQuestion):
            concrete[key] = ConcreteQuestion(qname, question.main, parent, callbacks=callbacks)
            blocks[key] = SubquestionBlock(qname, concrete[key], question, parent,
                                           callbacks=callbacks)
        elif isinstance(question, LiteralBlockQuestion):
            concrete[key] = LiteralBlock(qname, question, parent, callbacks=callbacks)
        else:
            raise TypeError("Type of question not known!", type(question))
    return concrete, blocks


class QuestionForm(Mapping):

    def __init__(self, questions, config=None, presets=None, callbacks=None):
        #
        callbacks = self._validate_callbacks(callbacks)
        #
        questions = QuestionGenerator(questions).tree
        #
        self.blocks = {}
        # literal blocks
        self.literals = {}
        # not set variables
        self.unset = {}
        # generate QuestionBlock
        self.form = QuestionBlock("", questions, self, callbacks=callbacks)
        #
        self.set_answers_and_presets(config, presets)

    @property
    def is_all_set(self):
        return all(block.is_set for block in self.values())

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

    def generate_setup(self, only_self=False, presets=None):
        if presets is not None:
            self.set_presets(presets)
        return self.form.generate_setup()

    def setup_iterator(self, only_self=False, presets=None):
        if presets is not None:
            self.set_presets(presets)
        return self.form.setup_iterator()

    def get_answers(self, check=True):
        """Get the answers from the forms

            Kwargs:
                check, bool:
                    if True, raise exception in case answers are not answered!
                    if False, dont check, missing answers are given as ""

        """
        if check is False:
            return self.form.get_answer()
        self.unset = {}
        answers = self.form.get_answer(check=True)
        if self.unset != {}:
            raise Exception('answer need to be set..')
        del self.unset
        return answers

    def get_blocks(self):
        return self.form.get_blocks()

    def write_config(self, filename):
        """ get a linear config and write it to the file"""
        config = {}
        for blockname in self.get_blocks():
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

    def set_answers_and_presets(self, config=None, presets=None):
        """set both presets and answers"""
        if presets is not None:
            self.set_presets(presets)

        if config is not None:
            if isinstance(config, Mapping):
                return self.set_answers_from_dct(config)
            if is_existing_file(config):
                self.set_answers_from_file(config)

    def set_presets(self, presets):
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

    def __iter__(self):
        return iter(self.get_blocks())

    def __len__(self):
        return len(self.get_blocks())

    def __getitem__(self, key):
        return self.blocks[key]

    def _set_answers_from_file(self, filename):
        """Set answers from a given file"""
        try:
            parsed, self.literals = ConfigParser.read(filename, self.literals)
        except FileNotFoundError:
            return f"File '{filename}' not found!"
        return self._set_answers_from_dct(parsed)

    def _set_answers_from_dct(self, dct):
        """Set the answers from a dictionary"""
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
            question = block[key]
            if answer == "":
                if question.is_optional:
                    question.is_set = True
                continue
            #
            try:
                question.answer = answer
            except ValueError:
                errmsg += f"\n{key} = {answer}, ValueError"
            except ValidatorErrorNotInChoices as err_choices:
                errmsg += (f"\n{key} = {answer}, Wrong Choice: can only be "
                           f"{err_choices}")
        if errmsg != "":
            return error + errmsg
        return ""

    def _validate_callbacks(self, callbacks):
        """Validate callbacks"""

        if callbacks is None:
            return callbacks

        if not isinstance(callbacks, Mapping):
            raise ValueError("callback needs to be a Mapping!")

        for key in ('ValueError', 'WrongChoice', 'EmptyEntry'):
            if key not in callbacks:
                # enter empty entry
                callbacks[key] = lambda x, y: None
        return callbacks

    def _split_keys(self, name):
        block, key = GeneratorNavigator.rsplit_keys(name)
        if key is None:
            key = block
            block = ""

        if block not in self.blocks:
            raise Exception("block unknown")

        return self.blocks[block], key


def generate_string(name, value):
    if value is None:
        return f"{name} ="
    if isinstance(value, StringList):
        return f"{name} = {', '.join(ele for ele in value)}"
    return f"{name} = {value}"


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
            yield generate_string(_name, _value)
        yield ''
