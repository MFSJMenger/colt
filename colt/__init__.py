# -*- coding: utf-8 -*-

"""Top-level package for Command Line Questions Tool."""

__author__ = """Maximilian Menger"""
__email__ = 'm.f.s.j.menger@rug.nl'
__version__ = '0.1.0'

__all__ = ["Colt", "PluginBase",
           "FromCommandline",
           "AskQuestions",
           "ColtErrorAnswerNotDefined", "QuestionASTGenerator",
           "Validator", "NOT_DEFINED"]

# Helper class to handle easily questions with classes
from .colt import Colt
from .plugins import PluginBase
from .pluginloader import PluginLoader
#
from .colt import FromCommandline
# If Questions should be asked without Colt use AskQuestions
from .ask import AskQuestions
# If answer is not set!
from .answers import ColtErrorAnswerNotDefined
# Generate questions from a reference config file
from .questions import QuestionASTGenerator
# Validator
from .validator import Validator, NOT_DEFINED
