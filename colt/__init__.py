# -*- coding: utf-8 -*-

"""Top-level package for Command Line Questions Tool."""

__author__ = """Maximilian Menger"""
__email__ = 'm.f.s.j.menger@rug.nl'
__version__ = '0.1.0'

# Helper class to handle easily questions with classes
from .colt import Colt
from .plugins import PluginBase
#
from .commandline import FromCommandline
# If Questions should be asked without Colt use AskQuestions
from .ask import AskQuestions
# Generate questions from a reference config file
from .questions import QuestionGenerator
# base classes to store the meta info for questions
from .questions import Question, ConditionalQuestion, register_parser
# Validator
from .validator import Validator
