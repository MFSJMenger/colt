"""Automated documentation using sphinx"""
from importlib import import_module
from docutils import nodes
#
from sphinx.util.docutils import SphinxDirective
#
from .questions import QuestionASTGenerator, NOT_DEFINED
from .validator import Validator
from .qform import QuestionVisitor, QuestionForm


class SphinxGeneratorVisitor(QuestionVisitor):

    def visit_qform(self, qform, **kwargs):
        pass

    def visit_question_block(self, block):
        pass

    def visit_concrete_question_select(self, question):
        return self._add_concrete_question(question)

    def visit_concrete_question_hidden(self, question):
        pass

    def visit_concrete_question_input(self, question):
        return self._add_concrete_question(question)

    def visit_literal_block(self, block):
        node = nodes.line(f'{block.name}', f"{block.name}, ")
        node += nodes.strong(f'LiteralBlock',
                             f'LiteralBlock')
        if block.comment is not NOT_DEFINED:
            return [node, nodes.literal_block(block.comment, block.comment)]
        return [node]

    def visit_subquestion_block(self, block):
        pass

    def _add_concrete_question(self, question):
        body, content = self._generate_body_as_literal(question)
        nodes = [self._generate_title_line(question.short_name, question, content)]
        if content:
            nodes.append(body)
        return nodes

    @staticmethod
    def _generate_title_line(key, question, content):
        node = nodes.line(f'{key}', f"{key}, ")
        node += nodes.strong(f'{question.typ}',
                             f'{question.typ}')
        if content:
            node += nodes.raw(':', ':')
        return node

    @staticmethod
    def _generate_body_as_literal(question):
        content = False
        text = ""
        validator = question.validator
        #
        default = validator.get()
        if default is not NOT_DEFINED:
            txt = f' default: {default}'
            if question.choices is not None:
                txt += f', from {validator.choices}'
            text += txt + '\n'
        #
        elif question.choices is not None:
            txt = f' Condition = {validator.choices}'
            text += txt + '\n'
        #
        if question.comment is not None:
            text += question.comment
        #
        if text != "":
            content = True
        return nodes.literal_block(text, text), content


class ColtDirective(SphinxDirective):
    """load questions from a given python module


    .. colt:: path_to_the_file
        :class: name_of_the_class
        :name: name_of_the_questions


    """
    #
    has_content = False
    #
    required_arguments = 1
    optional_arguments = 0
    option_spec = {'name': str,
                   'class': str,
                   }


    def run(self):
        visitor = SphinxGeneratorVisitor()
        qform = QuestionForm(self._load_questions())
        #
        main_node = nodes.topic('')
        #
        for block_name, block in qform.blocks.items():
            #
            node = self._make_title(block_name)
            #
            main_node += node
            #
            for question in block.concrete.values():
                main_node += question.accept(visitor)
        #
        name = self.options.get('name', None)
        #
        if name is not None:
            node = [self._make_title(f'{name}'), main_node]
        else:
            node = [main_node]
        #
        return node

    @staticmethod
    def _make_title(txt):
        node = nodes.line('', '')
        node += nodes.strong(txt, txt)
        return node

    def _load_questions(self):
        module_name = self.arguments[0]

        try:
            module = import_module(module_name)
        except ImportError:
            msg = f'Could not find module {module_name}'
            raise Exception(msg)

        cls = self.options.get('class', None)
        if hasattr(module, cls):
            obj = getattr(module, cls, None)
            #
            return obj.questions
        raise Exception(f"Module '{module_name}' contains no class '{cls}'")


class ColtQuestionsDirective(ColtDirective):
    """load questions from the directive context


    .. colt_questions::
        :name: name_of_the_questions

        question1 =
        question2 =
        question3 =
        ...

    """
    has_content = True

    required_arguments = 0
    optional_arguments = 0
    option_spec = {'name': str}

    def _load_questions(self):
        """read content as single line questions file"""
        #
        return QuestionASTGenerator("\n".join(self.content))


class ColtQFileDirective(ColtDirective):
    """load questions from the directive context

    .. colt_qfile:: path_to_the_file
        :name: name_of_the_questions

    """
    has_content = False

    required_arguments = 1
    optional_arguments = 0
    option_spec = {'name': str}

    def _load_questions(self):
        """load questions from a given file"""
        try:
            with open(self.arguments[0], 'r') as fhandle:
                questions = fhandle.read()
        except IOError:
            msg = f'Could not find file {self.arguments}'
            raise Exception(msg)
        #
        return QuestionASTGenerator(questions)


def setup(app):
    #
    app.add_directive("colt", ColtDirective)
    app.add_directive("colt_qfile", ColtQFileDirective)
    app.add_directive("colt_questions", ColtQuestionsDirective)
    #
    return {'version': '0.1',
            'parallel_read_safe': True,
            'parallel_write_safe': True,
            }
