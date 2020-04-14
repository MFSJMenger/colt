from importlib import import_module
#
from docutils import nodes
#
from sphinx.util.docutils import SphinxDirective
from . import QuestionGenerator, NOT_DEFINED


class ColtDirective(SphinxDirective):

    has_content = False

    required_arguments = 1
    optional_arguments = 0
    option_spec = {
            'name': str,
            'class': str,
    }

    def run(self):
        questions = self._load_questions()

        main_node = nodes.topic('')
        for key, value in questions.block_items():
            # nodes.caption(rawsource='', text='')
            node = self._make_title(key)
#            if key != '':
#                node += nodes.strong(f'[{key}]', f'[{key}]')
            _nodes = [node]
            # print(f"{key}: {type(value)}")
            for key, question in value.concrete_items():
                body, content = self._generate_body_as_literal(question)
                _nodes.append(self._generate_title_line(key, question, content))
                if content:
                    _nodes.append(body)
            for node in _nodes:
                main_node += node

        name = self.options.get('name', None)
        if name is not None:
            node = [self._make_title(f'{name}'), main_node]
        else:
            node = [main_node]

        return node

    def _make_title(self, txt):
        node = nodes.line('', '')
        node += nodes.strong(txt, txt)
        return node

    def _generate_title_line(self, key, question, content):
        node = nodes.line(f'{key}', f"{key}, ")
        node += nodes.strong(f'{question.typ}:',
                             f'{question.typ}:')
        if content:
            node += nodes.raw(':', ':')
        return node

    def _generate_body_as_literal(self, question):
        content = False
        text = ""
        #
        if question.choices is not None:
            choices = ", ".join(question.choices)
#        if question.default is not NOT_DEFINED:
        if question.default is not NOT_DEFINED:
            txt = f' default: {question.default}'
            if question.choices is not None:
                txt += f', from {choices}'
            text += txt + '\n'

        elif question.choices is not None:
            txt = f' choices = {choices}'
            text += txt + '\n'

#        if question.comment is not NOT_DEFINED:
        if question.comment is not NOT_DEFINED:
            text += question.comment
        if text != "":
            content = True
        return nodes.literal_block(text, text), content

    def _load_questions(self):

        try:
            module = import_module(self.arguments[0])
        except ImportError:
            msg = f'Could not find module {self.arguments}'
            raise Exception(msg)

        cls = self.options.get('class', None)

        if hasattr(module, cls):
            obj = getattr(module, cls)
            return obj.questions
        raise Exception('could import module')

class ColtQFileDirective(ColtDirective):
    has_content = False

    required_arguments = 1
    optional_arguments = 0
    option_spec = {
            'name': str,
    }
    
    def _load_questions(self):

        try:
            with open(self.arguments[0], 'r') as f:
                questions = f.read()
        except:
            msg = f'Could not find module {self.arguments}'
            raise Exception(msg)
        #
        return QuestionGenerator(questions)


def setup(app):
    app.add_directive("colt", ColtDirective)
    app.add_directive("colt_qfile", ColtQFileDirective)

    return {
            'version': '0.1',
            'parallel_read_safe': True,
            'parallel_write_safe': True,
    }
