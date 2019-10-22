===========================
Command Line Questions Tool
===========================



Command Line Questions for Python


* Free software: MIT license


Features
--------

Simple tool to create command line questions in Python.

The API consists of three classes and one functions:

  1. Question: namedtuple to contain the Question
     Question(question: string, type: string, default_value)
     default types are: str, int, float, ilist (integer list)
     if you want to add new types, register them via the
     register_parser routine

  2. ConditionalQuestion: namedtuple to contain a Question, which ask subquestions 
     depending on the answer. 
     ConditionalQuestion(name: string, main: Question, subquestions: dict)
     subquestions are hereby a dictonary with questions that are only asked, if the
     main question is answered with the corresponding key

  3. AskQuestions: class to ask specific questions and optionally save the answers
     in a config file, or read default from a given config file

  4. register_parser: function, register a new parser to extend the default types for Questions
     **Important:** Currently, **NO DICTONARIES** should be returned from the parser, as it will
     break the other code!
     **TODO**: Change that behaviour e.g. by introducing an own internal dictonary type by using 
     class _MyDict(dict): 


Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
