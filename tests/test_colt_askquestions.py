import pytest
#
from colt import AskQuestions
from colt.questions import _Questions
#


@pytest.fixture
def questions():
    return """
      value = 2 :: int :: [1, 2, 3]
      # hallo ihr
      # ihr auch
      name = :: str :: [hallo, du]
      ilist = :: ilist
      flist = 1.2 3.8 :: flist

      [qm]
      nqm = 100 :: int
      nmm = 200 :: int

      [examplecase(yes)]
      a = 10
      [examplecase(no)]
      a = 666

      [examplecase(no)::further]
      a = 666

      [examplecase(no)::further::andmore]
      a = 666
      select = :: str

      [examplecase(no)::further::andmore::select(yes)]
      a = yes

      [examplecase(no)::further::andmore::select(no)]
      a = no

      [examplecase(no)::further::andmore::select(maybe)]
      a = maybe :: str :: :: What was the question?
    """


def test_basic_ask_questions(questions):

    questions = AskQuestions("name", questions)
    assert type(questions.questions) == _Questions
