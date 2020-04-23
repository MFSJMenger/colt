import argparse
#
from abc import ABCMeta
#
from .questions import QuestionGenerator
from .questions import Validator, NOT_DEFINED
from .questions import Question, LiteralBlock, ConditionalQuestion
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
    colt_defaults = {'_generate_subquestions': classmethod(lambda cls, questions: 0),
                     '_questions': "",
                     }
    # rewrite that....it is horrible
    if clsdict.get('__annotations__', None) is not None:
        if clsdict['__annotations__'].get('subquestions', None) == 'inherited':
            if '_generate_subquestions' in clsdict:
                if len(bases) > 0:
                    clsdict['_generate_subquestions'] = join_subquestions(
                        bases[0]._generate_subquestions,
                        clsdict['_generate_subquestions'])
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
        return questions

    def _generate_subquestions(cls, questions):
        """This class will not be inherited"""


class Colt(metaclass=ColtMeta):
    """Basic Class to manage colts question routines"""

    @property
    def questions(self):
        return self.__class__.questions

    @classmethod
    def generate_questions(cls, config=None):
        return AskQuestions(cls.questions, config=config)

    @classmethod
    def from_questions(cls, *args, check_only=False, config=None, savefile=None, **kwargs):
        questions = cls.generate_questions(config=config)
        if check_only is True:
            answers = questions.check_only(savefile)
        else:
            answers = questions.ask(savefile)
        return cls.from_config(answers, *args, **kwargs)

    @classmethod
    def from_config(cls, answer, *args, **kwargs):
        raise Exception("Cannot load from_config, as it is not implemented!, "
                        "also from_questions depend on that!")

    @classmethod
    def from_commandline(cls, *args, description=None, **kwargs):
        """Initialize file from commandline options"""
        answers = cls.get_commandline_args(description=description)
        return cls.from_config(answers, *args, **kwargs)

    @classmethod
    def get_commandline_args(cls, description=None):
        """for the moment we accept only linear trees!"""
        parser, names = commandline_parser_from_questions(cls.questions, description)
        results = parser.parse_args()
        return fold_commandline_answers({key: getattr(results, key) for key in names})

    @classmethod
    def generate_input(cls, filename, config=None):
        questions = cls.generate_questions(config)
        answers = questions.ask()
        questions.create_config_from_answers(filename, answers)


def fold_commandline_answers(answers, separator='::'):
    result = {}
    for key, value in answers.items():
        fold_cline_answers(key, value, result, separator)
    return result


def fold_cline_answers(name, answer, result, separator='::'):
    if separator in name:
        parent, _, name = name.partition(separator)
        if parent not in result:
            result[parent] = {}
        fold_cline_answers(name, answer, result[parent], separator)
    else:
        result[name] = answer


def rpartition_by_separator(string, separator='::'):
    if separator not in string:
        return None, string
    start, _, end = string.rpartition(separator)
    return start, end


def commandline_parser_from_questions(questions, description=None):
    parser = argparse.ArgumentParser(description=description,
                                     formatter_class=argparse.RawTextHelpFormatter)
    #
    type_parser = Validator.get_parsers()
    #
    names = []
    for name, question in questions[""].items():
        add_parser_arguments(name, question, parser, type_parser, names)
    return parser, names


def add_parser_arguments(name, question, parser, type_parser, names):
    if isinstance(question, Question):
        add_parser_argument(name, parser, question, type_parser, names)
    elif isinstance(question, dict):
        for key, question in question.items():
            add_parser_arguments(f"{name}::{key}", question, parser, type_parser, names)
    elif isinstance(question, (LiteralBlock, ConditionalQuestion)):
        raise ValueError("NO commandline args from Literalblocks or ConditionalQuestions")
    else:
        raise ValueError("question needs to be a Question or QuestionBlock")


def add_parser_argument(name, parser, question, type_parser, names):
    """Add a single parser argument"""
    _, metavar_name = rpartition_by_separator(name)
    if question.comment is NOT_DEFINED:
        comment = None
    else:
        comment = question.comment
    if question.default is NOT_DEFINED:
        parser.add_argument(f'{name}', metavar=metavar_name, type=type_parser[question.typ],
                            help=comment)
    else:
        parser.add_argument(f'-{name}', metavar=metavar_name, type=type_parser[question.typ],
                            default=question.default, help=comment)
    names.append(name)
