"""Storage for Answers in Colts Questions Module"""
from collections.abc import Mapping


class SubquestionsAnswer(Mapping):
    """Storage elemement for the answers of a subquestion"""

    def __init__(self, name, main_answer, subquestion_answers):
        self.name = name
        self._main_answer = main_answer
        self._subquestion_answers = subquestion_answers
        if isinstance(self._subquestion_answers, SubquestionsAnswer):
            self.is_subquestion = True
        else:
            self.is_subquestion = False

    def __getitem__(self, key, default=None):
        if self.is_subquestion is True:
            if key == self._subquestion_answers.name:
                return self.subquestion_answers
        return self._subquestion_answers.get(key, default)

    def __iter__(self):
        return iter(self._subquestion_answers)

    def __len__(self):
        return len(self._subquestion_answers)

    def __eq__(self, other):
        """set __eq__ for easier comparision

        e.g.

        answer['colt']['case'] == 'case1'

        would be false, as answer['colt']['case'] is SubquestionsAnswer
        """
        if self._main_answer == other:
            return True
        return False

    def __ne__(self, other):
        if self._main_answer != other:
            return True
        return False

    @property
    def subquestion_answers(self):
        """Return answer of subquestions"""
        return self._subquestion_answers

    @property
    def value(self):
        """Return main answer"""
        return self._main_answer

    def __str__(self):
        return ('Subquestions('
                + str({f"{self.name} = {self._main_answer}": self._subquestion_answers}) + ')')

    def __repr__(self):
        return ('Subquestions('
                + str({f"{self.name} = {self._main_answer}": self._subquestion_answers}) + ')')
