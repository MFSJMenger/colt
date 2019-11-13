from abc import ABCMeta, abstractmethod
#
from .generator import QuestionGenerator

class _QuestionsHandlerMeta(ABCMeta):

    @property
    def questions(cls):
        questions = QuestionGenerator(cls._questions)
        cls._generate_subquestion(questions)
        return questions.questions
        
    def _generate_subquestion(cls, questions):
        pass

class Colt(metaclass=_QuestionsHandlerMeta):
    pass
