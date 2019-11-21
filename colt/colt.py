import argparse
#
from abc import ABCMeta
#
from .generator import QuestionGenerator
from .questions import _ConcreteQuestion
from .questions import Question
from .ask import AskQuestions


__all__ = ["Colt"]


def add_defaults_to_dict(clsdict, defaults):
    """ add defaults to dict """
    for key, default in defaults.items():
        if key not in clsdict:
            clsdict[key] = default


def delete_inherited_keys(keys, clsdict):
    for key in keys:
        if clsdict[key] == 'inherited':
            del clsdict[key]

def join_subquestions(func1, func2):
    if isinstance(func1, classmethod):
        func1 = func1.__func__
    if isinstance(func2, classmethod):
        func2 = func2.__func__


    def _generate_subquestions(cls, questions):
        func1(questions)
        func2(cls, questions)

    return classmethod(_generate_subquestions)


def colt_modify_class_dict(clsdict, bases):
    """setup the clsdict in colt to avoid inheritance problems
    
       it modifies both the clsdict and its annotations! 
    """
    colt_defaults = {
            '_generate_subquestions': classmethod(lambda cls, questions: 0),
            '_questions': "",
    }
    if '__annotations__' in clsdict:
        print(clsdict)
    # rewrite that....it is horrible
    if clsdict.get('__annotations__', None) is not None:
        if clsdict['__annotations__'].get('subquestions', None) == 'inherited':
            if '_generate_subquestions' in clsdict:
                print(clsdict['_generate_subquestions'])
                if len(bases) > 0:
                    clsdict['_generate_subquestions'] = join_subquestions(bases[0]._generate_subquestions, clsdict['_generate_subquestions'])
            else: 
                clsdict['_generate_subquestions'] = bases[0]._generate_subquestions
            # delete task from annotations, and clean unnecessary annotations!    
            del clsdict['__annotations__']['subquestions'] 
            if clsdict['__annotations__'] == {}:
                del clsdict['__annotations__']
    #
    add_defaults_to_dict(clsdict, colt_defaults)
    delete_inherited_keys(["_questions"], clsdict)


class ColtMeta(ABCMeta):
    """Metaclass to handle hierarchical generation of questions"""

    def __new__(cls, name, bases, clsdict):
        colt_modify_class_dict(clsdict, bases)
        return ABCMeta.__new__(cls, name, bases, clsdict)

    @property
    def questions(cls):
        return cls._generate_questions()

    def _generate_questions(cls):
        """generate questions"""
        questions = QuestionGenerator(cls._questions)
        cls._generate_subquestions(questions)
        return questions.questions

    def _generate_subquestions(cls, questions):
        """This class will not be inherited"""
        pass


class Colt(metaclass=ColtMeta):
    """Basic Class to manage colts question routines"""

    @property
    def questions(self):
        return self.__class__.questions

    @classmethod
    def generate_questions(cls, name, config=None):
        return AskQuestions(name, cls.questions, config=config)

    @classmethod
    def from_questions(cls, name, check_only=False, config=None, savefile=None):
        questions = cls.generate_questions(name, config=config)
        if check_only is True:
            return questions.check_only(savefile)
        answers = questions.ask(savefile)
        return cls.from_config(answers)

    @classmethod
    def from_config(cls, answer):
        raise Exception("Cannot load from_config, as it is not implemented!, "
                        "also from_questions depend on that!")

    @classmethod
    def from_commandline(cls, description=None):
        """Initialize file from commandline options"""
        answers = cls.get_commandline_args(description=description)
        return cls.from_config(answers)

    @classmethod
    def get_commandline_args(cls, description=None):
        """for the moment we accept only linear trees!"""

        parser = argparse.ArgumentParser(description=description,
                                         formatter_class=argparse.RawTextHelpFormatter)
        #
        type_parser = _ConcreteQuestion.get_parsers()

        for key, question in cls.questions.items():
            if not isinstance(question, Question):
                raise ValueError("Only linear trees allowed!")
            if question.default is not None:
                parser.add_argument(f'--{key}', metavar=key, type=type_parser[question.typ],
                                    default=question.default, help=question.comment)
            else:
                parser.add_argument(f'{key}', metavar=key, type=type_parser[question.typ],
                                    help=question.comment)

        results = parser.parse_args()

        return {key: getattr(results, key) for key in cls.questions.keys()}
