#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `colt` package."""

import pytest
from colt import AskQuestions
from colt import Question


@pytest.fixture
def example_question():
    """generate example single question"""
    q1 = Question("What time is it?", "float", 10)
    return q1


def test_askquestion_single_question(example_question):
    """Test ask question"""
    questions = AskQuestions("q1", example_question)
    questions.ask()
