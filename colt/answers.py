"""Storage for Answers in Colts Questions Module"""
from collections.abc import Mapping
from collections import UserDict
#
from .generator import GeneratorNavigator
from .validator import NOT_DEFINED
from .exceptions import Error


class ColtErrorAnswerNotDefined(Error):

    def __init__(self, filename, msg):
        super().__init__()
        self.msg = msg
        self.filename = filename

    def __repr__(self):
        return f"ColtErrorAnswerNotDefined: file = '{self.filename}'\n{self.msg}"

    def __str__(self):
        return f"ColtErrorAnswerNotDefined: file = '{self.filename}'\n{self.msg}"


class Answers(UserDict, GeneratorNavigator):
    """Basis answer class for simple validation!"""

    def __init__(self, answers, blocks, do_check=True, filename=None):
        UserDict.__init__(self, answers)
        self._blocks = blocks
        if filename is None:
            filename = '<NONE>'
        self.filename = filename
        if do_check is True:
            self._check_answers(answers)

    def get_not_defined_answers(self):
        result = self._get_not_defined_answers()
        if result == {}:
            return None
        return result

    def _check_answers(self, answers):
        not_defined = self._get_not_defined_answers()
        errmsg = "".join(self._errmsg(key, items) for key, items in not_defined.items())
        if errmsg != "":
            raise ColtErrorAnswerNotDefined(self.filename, errmsg)

    @staticmethod
    def _errmsg(block, items):
        out = "\n".join(f"{item} = NOT_SET" for item in items)
        if block == "":
            return out + "\n"
        return f"[{block}]\n{out}\n"

    def _get_not_defined_answers(self):

        not_defined = {key: self._get_not_defined_from_block(key, self.data)
                       for key in self._blocks}
        not_defined = {key: value for key, value in not_defined.items()
                       if not (value is None or len(value) == 0)}
        return not_defined

    def _get_not_defined_from_block(self, key, answers):
        answer = self.get_branching(key)
        if answer is None:
            return self._check_block(key, answers)
        return self._check_branching(key, answer.branch, answer.node, answers)

    def _check_block(self, parent, tree):
        node = self.get_node_from_tree(parent, tree)
        if node is None:
            return None
        return self._check_items(node)

    def _check_branching(self, parent, block_name, node_name, tree):
        parent, child = self.rsplit_keys(block_name)
        if child is None:
            child = parent
            parent = ""
        node = self.get_node_from_tree(parent, tree)
        if node is None:
            return None
        node = node[child]
        if node != node_name:
            return None
        return self._check_items(node)

    @staticmethod
    def _check_items(node):
        return tuple(key for key, value in node.items()
                     if value is NOT_DEFINED)


class SubquestionsAnswer(Mapping):
    """Storage elemement for the answers of a subquestion"""

    def __init__(self, name, main_answer, subquestion_answers):
        self.name = name
        self._main_answer = main_answer
        self._subquestion_answers = subquestion_answers
        if isinstance(self._subquestion_answers, SubquestionsAnswer):
            self.is_subquestion = True
        else:
            self.is_subquestion = False

    def __getitem__(self, key, default=None):
        if self.is_subquestion is True:
            if key == self._subquestion_answers.name:
                return self.subquestion_answers
        return self._subquestion_answers.get(key, default)

    def __iter__(self):
        return iter(self._subquestion_answers)

    def __len__(self):
        return len(self._subquestion_answers)

    def __eq__(self, other):
        """set __eq__ for easier comparision

        e.g.

        answer['colt']['case'] == 'case1'

        would be false, as answer['colt']['case'] is SubquestionsAnswer
        """
        if self._main_answer == other:
            return True
        return False

    def __ne__(self, other):
        if self._main_answer != other:
            return True
        return False

    @property
    def subquestion_answers(self):
        """Return answer of subquestions"""
        return self._subquestion_answers

    @property
    def value(self):
        """Return main answer"""
        return self._main_answer

    def __str__(self):
        return ('Subquestions('
                + str({f"{self.name} = {self._main_answer}": self._subquestion_answers}) + ')')

    def __repr__(self):
        return ('Subquestions('
                + str({f"{self.name} = {self._main_answer}": self._subquestion_answers}) + ')')
