

class SubquestionsAnswer(object):

    def __init__(self, name, main_answer, subquestion_answers):
        self.name = name
        self._main_answer = main_answer
        self._subquestion_answers = subquestion_answers
        if isinstance(self._subquestion_answers, SubquestionsAnswer):
            self.is_subquestion = True
        else:
            self.is_subquestion = False

    def __getitem__(self, key):
        return self.get(key)

    def get(self, key, default=None):
        if self.is_subquestion is True:
            if key == self._subquestion_answers.name:
                return self.subquestion_answers
        return self._subquestion_answers.get(key, default)

    def __contains__(self, key):
        return key in self._subquestion_answers

    def __iter__(self):
        return iter(self._subquestion_answers)

    def items(self):
        if isinstance(self._subquestion_answers, dict):
            return self._subquestion_answers.items()
        return ((self._main_answer, self._subquestion_answers), )

    @property
    def subquestion_answers(self):
        return self._subquestion_answers

    @property
    def value(self):
        return self._main_answer

    def __str__(self):
        return ('Subquestions('
                + str({f"{self.name} = {self._main_answer}": self._subquestion_answers}) + ')')

    def __repr__(self):
        return ('Subquestions('
                + str({f"{self.name} = {self._main_answer}": self._subquestion_answers}) + ')')
