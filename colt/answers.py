

class SubquestionsAnswer(object):

    def __init__(self, name, main_answer, subquestion_answers):
        self.name = name
        self._main_answer = main_answer
        self._subquestion_answers = subquestion_answers

    def __getitem__(self, key):
        return self._subquestion_answers.get(key, None)

    def __contains__(self, key):
        return key in self._subquestion_answers

    def __iter__(self):
        return iter(self._subquestion_answers)

    def items(self):
        if isinstance(self._subquestion_answers, dict):
            return self._subquestion_answers.items()
        return ((self._main_answer, self._subquestion_answers), )

    @property
    def value(self):
        return self._main_answer

    def __str__(self):
        return 'Subquestions(' + str({self._main_answer: self._subquestion_answers}) + ')'

    def __repr__(self):
        return 'Subquestions(' + str({self._main_answer: self._subquestion_answers}) + ')'
