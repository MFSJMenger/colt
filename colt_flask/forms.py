from colt import QuestionGenerator, AskQuestions
from colt.ask import ErrorSettingAnswerFromDict
from colt import NOT_DEFINED


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


class SubquestionBlock:

    def __init__(self, name, question, parent):
        self.name = name
        self.question = question
        self.parent = parent
        self.parent.blocks[name] = self
        self.settings = {qname: QuestionBlock(AskQuestions.join_case(name, qname), quest, parent)
                         for qname, quest in question.items()}

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

    def _split_keys(self, name):
        block, key = self.ask.rsplit_keys(name)
        if key is None:
            key = block
            block = ""
        
        if block not in self.blocks:
            raise Exception("block unknown")

        return self.blocks[block], key

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

    def generate_setup(self):
        return self.form.generate_setup()

    def setup_iterator(self):
        return self.form.setup_iterator()
