from abc import ABC, abstractmethod
from collections import UserDict
from colt.generator import GeneratorNavigator
from colt import QuestionGenerator
from colt.questions import Question, QuestionContainer, ConditionalQuestion
from colt.ask import ErrorSettingAnswerFromDict, ConfigParser
from colt.validator import Validator, NOT_DEFINED, ValidatorErrorNotInChoices


class _QuestionsContainerBase(GeneratorNavigator):

    def __init__(self, name, parent):
        #
        self.name = name
        self.parent = parent
        # register block
        self.parent.blocks[name] = self

    @abstractmethod
    def get_answer(self):
        """get answer dict"""


class _ConcreteQuestionBase(ABC):

    def __init__(self, name, question):
        self.name = name
        self._settings = self._generate_settings(name, question)

    @property
    def settings(self):
        self._settings.update(self._generate_dynamic_settings())
        return self._settings

    @abstractmethod
    def get_answer(self):
        """get answer"""

    @abstractmethod
    def _generate_settings(self, name, question):
        """generate core settings"""

    @abstractmethod
    def _generate_dynamic_settings(self):
        """generate additional runtime dependent settings"""


class LiteralBlock(_ConcreteQuestionBase):

    def __init__(self, name, question, parent):
        _ConcreteQuestionBase.__init__(self, name, question)
        # register self
        self.parent.literals[name] = self
        self._answer = None

    @property
    def answer(self):
        answer = self.get_answer()
        if answer is NOT_DEFINED:
            return ""
        return answer

    @answer.setter
    def answer(self, value):
        self._answer = value

    def get_answer(self):
        return self._answer

    def _generate_dynamic_settings(self):
        if self._answer is None:
            return {"value": ""}
        return {"value": self._answer}

    def _generate_settings(self, name, question):
        return {"type": "literal",
                "label": self._generate_label(question.question) }


class ConcreteQuestion(_ConcreteQuestionBase):

    def __init__(self, name, question):
        _ConcreteQuestionBase.__init__(self, name, question)
        self._value = Validator(question.typ, default=question.default, choices=question.choices)
        self._comment = question.comment

    def get_answer(self):
        return self._value.get()

    @property
    def answer(self):
        answer = self.get_answer()
        if answer is NOT_DEFINED:
            return ""
        return answer

    @answer.setter
    def answer(self, value):
        self._value.set(value)

    def _generate_dynamic_settings(self):
        return {"value": self.answer}

    def _generate_settings(self, name, question):
        if question.choices is None:
            return self._input_form_settings(name, question)
        return self._select_form_settings(name, question)

    def _generate_label(self, label):
        return f"{label}: "
    
    def _select_form_settings(self, name, question):
        return {"type": "select",
                "label": self._generate_label(question.question),
                "id": name,
                "options": question.choices,
                }

    def _input_form_settings(self, name, question):
        """get settings for input form"""
        return {"type": "input",
                "label": self._generate_label(question.question),
                "id": name,
                "placeholder": question.typ,
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
            out.update(blocks.generate_setup());
        #
        return out

    @property
    def answer(self):
        raise Exception("Answer not available for QuestionBlock")

    def get_answer(self):
        dct = {name: quest.get_answer() for name, quest in self.concrete.items()}
        dct.update({name: quest.get_answer() for name, quest in self.blocks.items()})
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
        self.main_question = ConcreteQuestion(name, main_question)
        #
        self.settings = {qname: QuestionBlock(self.join_case(name, qname), quest, parent)
                         for qname, quest in questions.items()}

    def get_answer(self):
        answer = self.main_question.get_answer()
        if answer is NOT_DEFINED:
            return SubquestionsAnswer(self._name, answer, {})
        return SubquestionsAnswer(self._name, answer, self[answer].get_answer())

    def setup_iterator(self):
        answer = self.answer
        if answer == "":
            return
        else:
            for ele in self.settings[answer].setup_iterator():
                yield ele
        
    def generate_setup(self):
        answer = self.answer
        if answer == "":
            return {}
        else:
            return self.settings[answer].generate_setup()

    @property
    def answer(self):
        return self.main_question.answer

    @answer.setter
    def answer(self, value):
        self.main_question.answer = value

    def get_blocks(self):
        answer = self.answer
        if answer == "":
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
            concrete[key] = ConcreteQuestion(qname, question)
        elif isinstance(question, QuestionContainer):
            blocks[key] = QuestionBlock(qname, question, parent)
        elif isinstance(question, ConcreteQuestion):
            concrete[key] = ConcreteQuestion(qname, question.main)
            blocks[key] = SubquestionBlock(qname, concrete[key], question, parent)
        elif isinstance(question, _LiteralBlock):
            concrete[key] = LiteralBlock(qname, question, parent)
        else:
            raise TypeError("Type of question not known!", type(question))
    return concrete, blocks


class QuestionForm:

    def __init__(self, questions):
        questions = QuestionGenerator(questions).tree
        #self._blocks = list(questions.key())
        self.blocks = {}
        # literal blocks
        self.literals = {}
        # generate QuestionBlock
        self.form = QuestionBlock("", questions, self)

    def _split_keys(self, name):
        block, key = GeneratorNavigator.rsplit_keys(name)
        if key is None:
            key = block
            block = ""
        
        if block not in self.blocks:
            raise Exception("block unknown")

        return self.blocks[block], key

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
            else:
                out['delete'] = block.get_delete_blocks()
                #
                block.answer = answer
                out['setup'] = block.generate_setup()
        else:
            block.concrete[key].answer = answer
        return out

    def get_answer(self):
        return self.form.get_answer()

    def generate_setup(self):
        return self.form.generate_setup()

    def setup_iterator(self):
        return self.form.setup_iterator()

    def set_answers_from_file(self, filename):
        errmsg = self._set_answers_from_file(filename)
        if errmsg is not None:
            raise ErrorSettingAnswerFromFile(filename, errmsg)

    def set_answers_from_dct(self, dct):
        errmsg = self._set_answers_from_dct(dct)
        if errmsg is not None:
            raise ErrorSettingAnswerFromDict(errmsg)

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
                print(f"""Section = {section} unknown, maybe typo?""")
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
