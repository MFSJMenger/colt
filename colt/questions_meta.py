from abc import ABCMeta, abstractmethod
#
from .generator import QuestionGenerator


class _QuestionsHandlerMeta(ABCMeta):
    """Metaclass to handle hierarchical generation of questions"""

    @property
    def _generate_questions(cls):
        """generate questions"""
        questions = QuestionGenerator(cls._questions)
        cls._generate_subquestions(questions)
        return questions.questions

    @property
    def questions(cls):
        return cls._generate_questions()
        
    def _generate_subquestions(cls, questions):
        pass


class Colt(metaclass=_QuestionsHandlerMeta):
    """Basic Class to manage colts question routines"""
    
    @property
    def questions(self):
        return self.__class__.questions
