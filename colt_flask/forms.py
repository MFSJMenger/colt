from colt import QuestionGenerator, AskQuestions
from colt.ask import ErrorSettingAnswerFromDict
from colt import NOT_DEFINED
#
#
def get_answer(question):
    if question.answer is NOT_DEFINED:
        value = ""
    else:
        value = question.answer
    return value


class ConcreteQuestion:

    def __init__(self, name, question):
        self.name = name
        self.question = question
        self._settings = self._generate_settings(name, question)

    @property
    def answer(self):
        return get_answer(self.question)

    @answer.setter
    def answer(self, value):
        self.question.answer = value

    @property
    def settings(self):
        self._settings["value"] = get_answer(self.question)
        return self._settings

    def _generate_settings(self, name, question):
        if question.choices is None:
            return self._input_form_settings(name, question)
        return self._select_form_settings(name, question)

    def _generate_label(self, label):
        return f"{label}: "
    
    def _select_form_settings(self, name, question):
        return {"type": "select",
                "label": self._generate_label(question.raw_question),
                "id": name,
                "options": question.choices,
                }

    def _input_form_settings(self, name, question):
        """get settings for input form"""
        return {"type": "input",
                "label": self._generate_label(question.raw_question),
                "id": name,
                "placeholder": question.typ,
                }


class QuestionBlock:

    def __init__(self, name, question, parent):
        self.name = name
        self.question = question
        self.parent = parent
        self.parent.blocks[name] = self
        self.concrete, self.blocks = create_forms(name, question, parent)

    def generate_setup(self):
        out = {self.name: {
            'fields': {quest.name: quest.settings for quest in self.concrete.values()},
            'previous': None}}
        #
        for blocks in self.blocks.values():
            out.update(blocks.generate_setup());
        #
        return out

    def get_blocks(self):
        return sum((block.get_blocks() for block in self.blocks.values()), 
                   [self.name])


class SubquestionBlock:

    def __init__(self, name, question, parent):
        self.name = name
        self.question = question
        self.parent = parent
        self.parent.blocks[name] = self
        self.settings = {qname: QuestionBlock(AskQuestions.join_case(name, qname), quest, parent)
                         for qname, quest in question.items()}

    def generate_setup(self):
        answer = self.answer
        if answer == "":
            return {}
        else:
            return self.settings[answer].generate_setup()

    @property
    def answer(self):
        return get_answer(self.question.main_question)

    @answer.setter
    def answer(self, value):
        self.question.main_question.answer = value

    def get_blocks(self):
        answer = self.answer
        if answer == "":
            return []
        else:
            return self.settings[answer].get_blocks()

    def get_delete_blocks(self):
        return {block: None for block in self.get_blocks()}

def create_forms(name, questions, parent):
    concrete = {}
    blocks = {}

    for key, value in questions.items():
        qname = AskQuestions.join_keys(name, key)
        if AskQuestions.is_concrete_question(value):
            concrete[key] = ConcreteQuestion(qname, value)
            continue
        if AskQuestions.is_question_block(value):
            blocks[key] = QuestionBlock(qname, value, parent)
            continue
        if AskQuestions.is_subquestion_block(value):
            concrete[key] = ConcreteQuestion(qname, value.main_question)
            blocks[key] = SubquestionBlock(qname, value, parent)
            continue
    return concrete, blocks


class QuestionForm:

    def __init__(self, questions):
        questions = QuestionGenerator(questions)
        #self._blocks = list(questions.key())
        self.ask = AskQuestions(questions)
        self.blocks = {}
        self.form = QuestionBlock("", self.ask.questions, self)

    def split_keys(self, name):
        block, key = self.ask.rsplit_keys(name)
        if key is None:
            key = block
            block = ""
        return block, key

    def generate_setup(self):
        return self.form.generate_setup()

