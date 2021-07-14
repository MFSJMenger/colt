from abc import abstractmethod, ABC
from collections import UserDict, UserString
from collections.abc import Mapping
from contextlib import contextmanager
from io import StringIO
import json
#
from .answers import AnswersBlock, SubquestionsAnswer
from .config import ConfigParser
from .generator import GeneratorNavigator
#
from .questions import QuestionASTGenerator
from .questions import QuestionASTVisitor
from .questions import Component
#
from .presets import PresetGenerator
from .validator import Validator, NOT_DEFINED, file_exists, ListValidator
from .validator import ValidatorErrorNotChoicesSubset, ValidatorErrorNotInChoices
from .validator import Choices, RangeExpression


join_case = GeneratorNavigator.join_case
join_keys = GeneratorNavigator.join_keys
rsplit_keys = GeneratorNavigator.rsplit_keys


def split_keys(name):
    block, key = rsplit_keys(name)
    if key is None:
        key = block
        block = ""
    return block, key


def is_existing_file(config):
    try:
        config = file_exists(config)
        return True
    except ValueError:
        return False


class _QuestionsContainerBase(Component):
    """Base class to contain question containers"""

    __slots__ = ('name', 'parent_name', '_name')

    def __init__(self, name, qform, *, register=True):
        #
        self.name = name
        #
        self.parent_name, self._name = split_keys(name)
        # register block
        if register is True:
            qform.blocks[name] = self

    def __str__(self):
        """Return full name"""
        return self.name

    def __repr__(self):
        """Return full name"""
        return self.name

    @property
    def label(self):
        return self._name


class _ConcreteQuestionBase(Component):
    """Logic of each actual question"""

    __slots__ = ("name", "parent_name", "_name", "is_set")

    def __init__(self, name):
        self.name = name
        self.parent_name, self._name = split_keys(name)
        self.is_set = False

    @property
    def short_name(self):
        return self._name

    @property
    def answer(self):
        """Used to set/get user input, needs to be overwritten"""
        return ""

    @property
    def accept_empty(self):
        return False

    @property
    def label(self):
        return self._name

    @property
    def id(self):
        return self.name

    @abstractmethod
    def get_answer(self):
        """get answer"""

    @abstractmethod
    def get_answer_as_string(self):
        """get string of answer"""

    @abstractmethod
    def preset(self, value, choices):
        """preset new value and choices!"""

    def set(self, answer, on_empty_entry=lambda answer, self: None,
            on_value_error=lambda answer, self: None, on_wrong_choice=lambda answer, self: None):
        """ Handle all set events """
        if answer == "":
            if self.accept_empty is False:
                on_empty_entry(answer, self)
            return self.accept_empty
        #
        try:
            self.answer = answer
            return True
        except ValueError:
            on_value_error(answer, self)
        except ValidatorErrorNotInChoices:
            on_wrong_choice(answer, self)
        return False

    def get(self):
        return self.answer


class LiteralBlockString(UserString):
    """UserString to contain a literalblock, the string can also be empty"""

    def __init__(self, string):
        if string in [None, NOT_DEFINED]:
            self.is_none = True
            string = ''
        elif isinstance(string, LiteralBlockString):
            self.is_none = string.is_none
        else:
            self.is_none = False
        #
        UserString.__init__(self, string)


class LiteralBlock(_ConcreteQuestionBase):
    """LiteralBlock Node"""

    __slots__ = ("_answer", 'comment')

    def __init__(self, name, comment, qform):
        #
        _ConcreteQuestionBase.__init__(self, name)
        # register self
        qform.literals[name] = self
        #
        self._answer = LiteralBlockString(None)
        self.comment = comment
        #

    @property
    def is_optional(self):
        return True

    @property
    def answer(self):
        return LiteralBlockString(self.get_answer())

    @answer.setter
    def answer(self, value):
        self._answer = LiteralBlockString(value)
        self.is_set = True

    @property
    def accept_empty(self):
        return True

    def preset(self, value, choices):
        raise Exception("preset not defined for Literalblock")

    def get_answer(self):
        if self._answer.is_none is True:
            return None
        return self._answer.data

    def get_answer_as_string(self):
        """get string of answer"""
        if self._answer.is_none is True:
            return ''
        return self._answer

    def accept(self, visitor):
        return visitor.visit_literal_block(self)


class ConcreteQuestion(_ConcreteQuestionBase):
    """Concrete question"""

    __slots__ = ("_value", "_comment", "is_subquestion_main",
                 "question", "typ", "is_optional", "alias", "is_hidden", "is_set_to_empty")

    def __init__(self, name, question, is_subquestion=False):
        #
        _ConcreteQuestionBase.__init__(self, name)
        #
        self._value = Validator(question.typ, default=question.default, choices=question.choices)
        #
        if question.comment is NOT_DEFINED:
            self._comment = None
        else:
            self._comment = question.comment
        #
        self.alias = question.alias
        self.question = question.question
        self.typ = question.typ

        self.is_optional = question.is_optional
        self.is_subquestion_main = is_subquestion
        self.is_set_to_empty = False
        #
        if self.short_name.startswith('_'):
            self.is_hidden = True
        else:
            self.is_hidden = False

    @property
    def default(self):
        default = self._value.default
        if default is NOT_DEFINED:
            return None
        return default

    @property
    def is_list_validator(self):
        return isinstance(self._value, ListValidator)

    @property
    def accept_empty(self):
        return self.is_optional or self._value.get() is not NOT_DEFINED

    @property
    def validator(self):
        return self._value

    @property
    def has_only_one_choice(self):
        return len(self.choices) == 1

    @property
    def comment(self):
        return self._comment

    @property
    def placeholder(self):
        choices = self.choices
        if isinstance(choices, RangeExpression):
            return f"{self.typ}, {choices.as_str()}"
        return self.typ

    @property
    def answer(self):
        answer = self._value.get()
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

    def get_answer(self):
        """get answer back, if is optional, return None if NOT_DEFINED"""
        answer = self._value.get()
        if self.is_optional is True:
            if self.is_set_to_empty is True or answer is NOT_DEFINED:
                return None
        return answer

    def get_answer_as_string(self):
        """get answer back, if is optional, return None if NOT_DEFINED"""
        if self.is_set_to_empty is True:
            return ''
        return self._value.answer_as_string()

    def accept(self, visitor):
        if self.is_hidden is True:
            return visitor.visit_concrete_question_hidden(self)
        #
        if isinstance(self.choices, Choices):
            return visitor.visit_concrete_question_select(self)
        return visitor.visit_concrete_question_input(self)

    def set_answer(self, value):
        self._value.set(value)
        self.is_set = True

    def preset(self, default, choices):
        """preset new value, choices:
        important: first update choices to ensure that default in choices!
        """
        if choices is not None:
            self._value.choices = choices
            #
            answer = self._value.get()
            #
            if answer is NOT_DEFINED:
                self.is_set = False
        if default is not None:
            self._value.set_default(default)


class QuestionBlock(_QuestionsContainerBase, UserDict):
    """Store a question block"""

    def __init__(self, name, concrete, blocks, qform, *, comment=None):
        _QuestionsContainerBase.__init__(self, name, qform)
        #
        UserDict.__init__(self)
        #
        self.concrete = concrete
        self.blocks = blocks
        #
        self.data = concrete
        self.comment = comment

    @property
    def is_set(self):
        return all(question.is_set for question in self.concrete.values())

    @property
    def is_set_or_default(self):
        return all(question.accept_empty for question in self.concrete.values())

    @property
    def answer(self):
        raise Exception("Answer not available for QuestionBlock")

    def accept(self, visitor):
        return visitor.visit_question_block(self)

    def get_blocks(self):
        return sum((block.get_blocks() for block in self.blocks.values()),
                   [self.name])


class SubquestionBlock(_QuestionsContainerBase):
    """Container for the cases spliting"""

    def __init__(self, name, main_question, cases, parent):
        _QuestionsContainerBase.__init__(self, name, parent, register=False)
        #
        self.main_question = main_question
        #
        self.cases = cases

    @property
    def is_optional(self):
        return self.main_question.is_optional

    def generate_setup(self):
        answer = self.answer
        if answer in ("", None):
            return {}
        return self.cases[answer].generate_setup()

    def accept(self, visitor):
        return visitor.visit_subquestion_block(self)

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
        return self.cases[answer].get_blocks()

    def get_delete_blocks(self):
        return {block: None for block in self.get_blocks()}

    @property
    def concrete(self):
        answer = self.answer
        if answer in ("", None):
            return {}
        return self.cases[answer].concrete


class QuestionVisitor(ABC):
    """Base class to define visitors for the question form
    the entry point is always the `QuestionForm`"""

    __slots__ = ()

    def visit(self, qform, **kwargs):
        """Visit a question form"""
        return qform.accept(self, **kwargs)

    @abstractmethod
    def visit_qform(self, qform, **kwargs):
        pass

    @abstractmethod
    def visit_question_block(self, block):
        pass

    @abstractmethod
    def visit_concrete_question_select(self, question):
        pass

    @abstractmethod
    def visit_concrete_question_hidden(self, question):
        pass

    @abstractmethod
    def visit_concrete_question_input(self, question):
        pass

    @abstractmethod
    def visit_literal_block(self, block):
        pass

    def visit_subquestion_block(self, block):
        """visit subquestion blocks"""
        answer = block.answer
        if answer in ("", None):
            return {}
        #
        return block.cases[answer].accept(self)

    def on_empty_entry(self, answer, question):
        pass

    def on_value_error(self, answer, question):
        pass

    def on_wrong_choice(self, answer, question):
        pass

    def set_answer(self, question, answer):
        return question.set(answer, on_empty_entry=self.on_empty_entry,
                            on_value_error=self.on_value_error,
                            on_wrong_choice=self.on_wrong_choice)

    def _visit_block(self, block):
        """visit a block, first only concrete questions, then the subblocks"""
        for question in block.concrete.values():
            question.accept(self)
        #
        for subblock in block.blocks.values():
            subblock.accept(self)


def block_error(block_name, errors):
    if block_name == '':
        txt = '\n'
    else:
        txt = f"\n[{block_name}]\n"
    for key, error in errors.items():
        txt += f"{key} = {error}\n"
    return txt


class ColtErrorAnswerNotDefined(SystemExit):
    """Error if answer is not defined"""

    __slots__ = ()

    def __init__(self, msg):
        super().__init__(f"ColtErrorAnswerNotDefined:\n{msg}")


class AnswerVisitor(QuestionVisitor):
    """Visitor to collect answers from a given qform"""

    __slots__ = ('check', 'error')

    def __init__(self):
        self.error = None
        self.check = False

    def visit_qform(self, qform, check=False):
        """Visit the qform

        Raises
        ------
        ColtErrorAnswerNotDefined
            in case an answer is not defined
        """
        self.error = {}
        self.check = check
        answer = qform.form.accept(self)
        if check is True:
            if len(self.error) != 0:
                raise ColtErrorAnswerNotDefined(self._create_exception(self.error))
        self.error = None
        return answer

    def visit_question_block(self, block):
        """Visit the question block and store all results in a Mapping"""
        error = {}
        results = {}
        for question in block.concrete.values():
            try:
                res = question.accept(self)
                results[question.label] = res
                if res is NOT_DEFINED:
                    error[question.label] = "NotSet"
            except ValueError as e:
                error[question.label] = e
        out = AnswersBlock(results)
        #
        if self.check is True:
            if len(error) != 0:
                self.error[block.name] = error
        # update blocks
        out.update({name: block.accept(self) for name, block in block.blocks.items()})
        #
        return out

    def visit_subquestion_block(self, block):
        """visit subquestion blocks"""
        answer = block.main_question.get_answer()
        if answer is NOT_DEFINED:
            return SubquestionsAnswer(block.label, None, {})
        #
        return SubquestionsAnswer(block.label, answer, block.cases[answer].accept(self))

    def visit_concrete_question_select(self, question):
        return question.get_answer()

    def visit_concrete_question_input(self, question):
        return question.get_answer()

    def visit_concrete_question_hidden(self, question):
        return question.get_answer()

    def visit_literal_block(self, block):
        return block.get_answer()

    @staticmethod
    def _create_exception(errors):
        return "\n".join(block_error(block, berrors) for block, berrors in errors.items())


class QuestionGeneratorVisitor(QuestionASTVisitor):
    """QuestionASTVisitor, to fill a qform"""

    __slots__ = ('question_id', 'qname', 'qform', 'concrete', 'blocks')

    def __init__(self):
        """Set basic defaults to None"""
        # current question id, id is blockname::qname
        self.question_id = None
        # current question name within that block
        self.qname = None
        # qform the questions get saved in
        self.qform = None
        # current concrete question container
        self.concrete = None
        # current block container
        self.blocks = None

    def reset(self):
        """set data to initial form"""
        # current question id, id is blockname::qname
        self.question_id = None
        # current question name within that block
        self.qname = None
        # qform the questions get saved in
        self.qform = None
        # current concrete question container
        self.concrete = None
        # current block container
        self.blocks = None

    def visit_question_ast_generator(self, qgen, qform=None):
        """When visiting an ast generator"""
        # save qform in self.qform
        self.qform = qform
        # set block_name and block_id
        self.question_id = ''
        # set concrete and blocks to None
        self.concrete = None
        self.blocks = None
        # start visiting the blocks
        output = qgen.tree.accept(self)
        # reset
        self.reset()
        #
        return output

    def visit_question_container(self, block):
        """when visiting a question container"""
        # save qname
        qname = self.qname
        #
        with self.question_block() as qid:
            for key, question in block.items():
                # set qname to current key
                self.qname = key
                # set question_id
                self.question_id = join_keys(qid, key)
                # visit next item
                question.accept(self)
            # create block
            block = QuestionBlock(qid, self.concrete, self.blocks,
                                  self.qform, comment=block.comment)
        # if in main form, or within subquestions block, return the block
        if self.blocks is None:
            return block
        # else set the block
        self.blocks[qname] = block

    def visit_conditional_question(self, question):
        """visit conditional question form"""
        # create concrete_question and save it in the concrete_question block
        concrete_question = ConcreteQuestion(self.question_id, question.main, is_subquestion=True)
        self.concrete[self.qname] = concrete_question
        # enter the subquestion_block mode
        with self.subquestion_block() as (qid, block_name):
            # create empty cases dictionary
            cases = {}
            #
            for qname, quest in question.items():
                # set question_id
                self.question_id = join_case(qid, qname)
                # there are no ids for these, so question.id does not need
                # to be set, here only subblocks can be inside!
                cases[qname] = quest.accept(self)
        # save subquestion block
        self.blocks[block_name] = SubquestionBlock(qid, concrete_question, cases, self.qform)

    def visit_literal_block(self, question):
        """block needs to be in a concrete section"""
        self.concrete[self.qname] = LiteralBlock(self.question_id, question.comment, self.qform)

    def visit_question(self, question):
        """question needs to be in concrete section"""
        self.concrete[self.qname] = ConcreteQuestion(self.question_id, question)

    @contextmanager
    def subquestion_block(self):
        """helper function to set defaults and reset them
        for SubquestionBlock"""
        blocks = self.blocks
        #
        self.blocks = None
        #
        yield self.question_id, self.qname
        #
        self.blocks = blocks

    @contextmanager
    def question_block(self):
        """helper function to set defaults and reset them
        for QuestionBlock"""
        # save old concrete, and blocks
        concrete = self.concrete
        blocks = self.blocks
        # create empty new ones
        self.concrete = {}
        self.blocks = {}
        #
        yield self.question_id
        # restore the old ones
        self.concrete = concrete
        self.blocks = blocks


class ErrorSettingAnswerFromFile(SystemExit):
    """errors setting answers from file"""

    __slots__ = ()

    def __init__(self, filename, msg):
        super().__init__(f"ErrorSettingAnswerFromFile: file = '{filename}'\n{msg}")


class ErrorSettingAnswerFromDict(SystemExit):
    """Error when trying to read answers from a dict"""

    __slots__ = ()

    def __init__(self, msg):
        super().__init__(f"ErrorSettingAnswerFromDict:\n{msg}")


class WriteJsonVisitor(QuestionVisitor):
    """Visitor to write the answers to a string"""

    __slots__ = ()

    def visit_qform(self, qform, **kwargs):
        data = qform.form.accept(self)
        return json.dumps(data, indent=4)

    def visit_question_block(self, block):
        # first all normal questions
        dct = {}
        for name, question in block.concrete.items():
            res = question.accept(self)
            if res is not None:
                dct[res] = res
        #
        for name, subblock in block.blocks.items():
            dct[name] = subblock.accept(self)
        return dct

    def visit_concrete_question_select(self, question):
        return question.get_answer_as_string()

    def visit_concrete_question_hidden(self, question):
        pass

    def visit_concrete_question_input(self, question):
        return question.get_answer_as_string()

    def visit_literal_block(self, block):
        answer = block.answer
        if answer.is_none is True:
            return
        return answer

    def visit_subquestion_block(self, block):
        """visit subquestion blocks"""
        answer = block.main_question.answer
        dct = {'__answer__': answer}
        if answer is None:
            return {}
        subblock = block.cases.get(answer)
        if subblock is None:
            return {}
        dct[answer] = subblock.accept(self)
        return dct


class WriteConfigVisitor(QuestionVisitor):
    """Visitor to write the answers to a string"""

    __slots__ = ('txt',)

    def __init__(self):
        self.txt = ''

    def visit_qform(self, qform, **kwargs):
        self.txt = ''
        for blockname in qform.get_blocks():
            # normal blocks
            qform[blockname].accept(self)
        txt = self.txt
        self.txt = ''
        return txt

    def visit_question_block(self, block):
        if block.name != '':
            self.txt += f'\n[{block.name}]\n'
        # first all normal questions
        for question in block.concrete.values():
            if not isinstance(question, LiteralBlock):
                question.accept(self)
        # than literal blocks
        for question in block.concrete.values():
            if isinstance(question, LiteralBlock):
                question.accept(self)

    def visit_concrete_question_select(self, question):
        self.txt += f'{question.short_name} = {question.get_answer_as_string()}\n'

    def visit_concrete_question_hidden(self, question):
        pass

    def visit_concrete_question_input(self, question):
        self.txt += f'{question.short_name} = {question.get_answer_as_string()}\n'

    def visit_literal_block(self, block):
        answer = block.answer
        if answer.is_none is True:
            return
        self.txt += f'[{block.id}]\n{answer}\n'

    def visit_subquestion_block(self, block):
        """visit subquestion blocks"""
        raise Exception("should never arrive in subquestion block!")


class QuestionForm(Mapping, Component):
    """Main interface to the question forms"""
    #
    __slots__ = ('blocks', 'literals', 'unset', 'form')
    # visitor to generate answers
    answer_visitor = AnswerVisitor()
    # visitor to write answers to file
    write_visitor = WriteConfigVisitor()
    # visitor to generate question forms
    question_generator_visitor = QuestionGeneratorVisitor()

    def __init__(self, questions, config=None, presets=None):
        #
        self.blocks = {}
        # literal blocks
        self.literals = {}
        # not set variables
        self.unset = {}
        # generate Question Forms
        self.form = self._generate_forms(questions)
        #
        self.set_answers_and_presets(config, presets)

    def _generate_forms(self, questions):
        questions = QuestionASTGenerator(questions)
        return self.question_generator_visitor.visit(questions, qform=self)

    def accept(self, visitor, **kwargs):
        return visitor.visit_qform(self, **kwargs)

    @property
    def is_all_set(self):
        """check if all questions are answered"""
        return all(block.is_set for block in self.values())

    def set_answer(self, name, answer):
        """Set the answer of a question"""
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

    def get_answers(self, check=True):
        """Get the answers from the forms

        Parameter
        ---------

        check: bool
            if False, raise no exception in case answers are not set
                      missing answers are given as empty strings

        Returns
        -------
        AnswersBlock
            dictionary with the parsed and validated userinput

        Raises
        ------
        ColtErrorAnswerNotDefined
            if `check` is True, raises error in case answers are not given
        """
        return self.answer_visitor.visit(self, check=check)

    def get_blocks(self):
        """return blocks"""
        return self.form.get_blocks()

    def write_config(self, filename):
        """ get a linear config and write it to the file"""
        if isinstance(filename, StringIO):
            return
        with open(filename, 'w') as fhandle:
            fhandle.write(self.write_visitor.visit(self))

    def set_answers_from_file(self, filename, raise_error=True):
        error = self._set_answers_from_file(filename)
        if raise_error is True and error.is_none() is False:
            raise ErrorSettingAnswerFromDict(str(error))

    def set_answers_from_dct(self, dct, raise_error=True):
        error = self._set_answers_from_dct(dct)
        if raise_error is True and error.is_none() is False:
            raise ErrorSettingAnswerFromDict(str(error))

    def set_answers_and_presets(self, config=None, presets=None, raise_error=True):
        """set both presets and answers"""
        if presets is not None:
            self.set_presets(presets)

        if config is not None:
            if isinstance(config, Mapping):
                self.set_answers_from_dct(config, raise_error=raise_error)
            elif isinstance(config, StringIO) or is_existing_file(config):
                self.set_answers_from_file(config, raise_error=raise_error)

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

    def _set_literals(self, literals):
        """set literals from literalblock """
        for key, value in literals.items():
            if value in (None, ''):
                continue
            self.literals[key].answer = value

    def _set_answers_from_file(self, filename):
        """Set answers from a given file"""
        #
        try:
            parsed, literals = ConfigParser.read(filename, self.literals)
        except FileNotFoundError:
            return ColtErrorMessage(f"File '{filename}' not found!")
        #
        self._set_literals(literals)
        #
        return self._set_answers_from_dct(parsed)

    def _set_answers_from_dct(self, dct):
        """Set the answers from a dictionary"""
        #
        error = ColtInputError()
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

            error.append(self._set_block_answers(blockname, answers))
        #
        return error

    def _set_block_answers(self, blockname, answers):
        error = ColtBlockError(blockname)

        block = self.blocks[blockname]
        for key, answer in answers.items():
            if key not in block:
                print(f"unknown key '{key}' in '[{block}]'")
                continue
            question = block[key]
            if answer == "":
                if question.is_optional:
                    question.is_set = True
                    question.is_set_to_empty = True
                continue
            #
            try:
                question.answer = answer
            except ValueError as e:
                error[key] = f"{answer}, ValueError: {e}"
            except ValidatorErrorNotInChoices as err_choices:
                error[key] = f"{answer}, Wrong Choice: {err_choices}"
        return error

    def _split_keys(self, name):
        block, key = split_keys(name)

        if block not in self.blocks:
            raise Exception("block unknown")

        return self.blocks[block], key


class ColtBlockError:
    """Class to handle error messages for setting a block"""

    __slots__ = ('_errors', 'name')

    def __init__(self, name):
        self._errors = {}
        self.name = name

    def is_none(self):
        return self._errors == {}

    def __setitem__(self, key, value):
        self._errors[key] = value

    def __str__(self):
        if self.is_none():
            return ""
        #
        if self.name != "":
            msg = f"[{self.name}]"
        else:
            msg = ""
        #
        msg += "\n".join(f"{key} = {err}" for key, err in self._errors.items())
        #
        return msg


class ColtErrorMessage(str):
    """String that behaves like a Colt Error"""

    def is_none(self):
        return self == ""


class ColtInputError:
    """Class to handle error messages for input setting"""

    __slots__ = ('_errors', '_current')

    def __init__(self):
        self._errors = []
        self._current = None

    def __str__(self):
        if self.is_none():
            return ""

        return "\n\n".join(f"{block}" for block in self._errors)

    def is_none(self):
        return len(self._errors) == 0

    def append(self, block_error):
        if block_error.is_none() is False:
            self._errors.append(block_error)
