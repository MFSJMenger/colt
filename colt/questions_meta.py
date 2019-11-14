from abc import ABCMeta, abstractmethod
#
from .generator import QuestionGenerator


class _QuestionsHandlerMeta(ABCMeta):

    @property
    def _generate_questions(cls):
        questions = QuestionGenerator(cls._questions)
        cls._generate_subquestion(questions)
        return questions.questions

    @property
    def questions(cls):
        return cls._generate_questions
        
    def _generate_subquestion(cls, questions):
        pass


class Colt(metaclass=_QuestionsHandlerMeta):
    
    @classmethod
    def questions(cls):
        return cls._generate_questions
