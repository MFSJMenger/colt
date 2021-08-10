"""Automated documentation using sphinx"""
from importlib import import_module
from io import StringIO
#
from sphinx.util.docutils import SphinxDirective, nodes
#
from .questions import QuestionASTGenerator, NOT_DEFINED
from .qform import QuestionVisitor, QuestionForm
from .colt import CommandlineInterface
from .parser_settings_generator import HelpFormatterGenerator
from .validator import bool_parser


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
        node += nodes.strong('LiteralBlock',
                             'LiteralBlock')
        if block.comment is not NOT_DEFINED:
            return [node, nodes.literal_block(block.comment, block.comment+' ')]
        return [node]

    def visit_subquestion_block(self, block):
        pass

    def _add_concrete_question(self, question):
        res_node = nodes.paragraph()
        body = self._generate_body_as_literal(question)
        res_node += self._generate_title_line(question.short_name, question, len(body) != 0)
        if body is not None:
            res_node.append(body)
        return res_node

    @staticmethod
    def _generate_title_line(key, question, content):
        node = nodes.line(f'{key}', f"{key}, ")
        node += nodes.strong(f'{question.typ}',
                             f'{question.typ}')
        if content is True:
            node += nodes.strong(':', ':')
        return node

    @staticmethod
    def _generate_body_as_literal(question):
        validator = question.validator
        res = []
        #
        default = validator.get()
        if default is not NOT_DEFINED:
            txt = f'default: {default}'
            if question.choices is not None:
                txt += f', from {validator.choices}'
            res.append(txt)
        #
        elif question.choices is not None:
            txt = f'{validator.choices}'
            res.append(txt)

        if question.comment is not None:
            res.append(question.comment)

        res = "\n".join(res)

        return nodes.literal_block(res, res+' ')


class ColtDirective(SphinxDirective):
    """load questions from a given python module


    .. colt:: path_to_the_file name_of_the_class
        :name: name_of_the_questions

    """
    #
    has_content = False
    #
    required_arguments = 2
    optional_arguments = 0
    option_spec = {'name': str}

    def run(self):
        visitor = SphinxGeneratorVisitor()
        qform = QuestionForm(self._load_questions())
        #
        main_node = nodes.topic('')
        #
        for block_name, block in sorted(qform.blocks.items()):
            #
            node = self._make_title(block_name)
            #
            if node is not None:
                main_node += node
            #
            for question in block.concrete.values():
                main_node += question.accept(visitor)
        #
        name = self.options.get('name', None)
        #
        if name is not None:
            node = nodes.line('', '')
            node += nodes.strong(f"{name}", f"{name}")
            node = [node, main_node]
        else:
            node = [main_node]
        #
        return node

    @staticmethod
    def _make_title(txt):
        if txt == '':
            return None
        node = nodes.line('', '')
        node += nodes.strong(f"[{txt}]", f"[{txt}]")
        return node

    def _load_questions(self):
        module_name = self.arguments[0]

        try:
            module = import_module(module_name)
        except ImportError:
            msg = f'Could not find module {module_name}'
            raise Exception(msg) from None

        cls = self.arguments[1]
        if hasattr(module, cls):
            obj = getattr(module, cls, None)
            #
            return obj.colt_user_input
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


class ColtCommandlineDirective(SphinxDirective):
    """load questions from a given python module

    .. colt:: path_to_the_file name_of_the_obj
        :name: name_of_the_questions
        :header: True

    """
    has_content = True
    #
    required_arguments = 2  # module
    optional_arguments = 0
    option_spec = {'name': str,
                   'subparsers': str,
                   'header': str,
                   }

    def run(self):
        description = None
        if len(self.content) != 0:
            description = HelpFormatterGenerator.from_questions(
                                    config=StringIO("\n".join(self.content)),
                                    check_only=True)
        parser = self._load_parser(description=description)
        #
        node = nodes.topic('')
        subparser = self.options.get('subparsers', None)
        header = bool_parser(self.options.get('header', 'yes'))

        if subparser is None:
            node += self._display_arg_parse(parser)
        else:
            node += self._display_parser(parser, subparser, display_header=header)
        return [node]

    def _display_parser(self, parser, name, *, display_header=False):
        """name should be: parent.opt(child).child_of_child"""
        options = name.split('.')
        for i, option in enumerate(options, start=1):
            subparser_name, option = self._parse_option(option)
            for subparser in parser.children:
                if subparser.name == subparser_name:
                    break
            else:
                raise ValueError(f"Could not find subparser '{subparser_name}'")
            if option == '*':
                if i != len(options):
                    raise ValueError("Can use '*' only for last option")
                node = nodes.paragraph()
                for name, parser in subparser.cases.items():
                    if display_header is True:
                        line = nodes.line()
                        line += nodes.strong(f'{name}', f"{name}")
                        node += line
                    node += self._display_arg_parse(parser)
                return node

            parser = subparser.cases.get(option)
            if parser is None:
                raise ValueError(f"Option '{option}' in subparser '{subparser.name}' unknown")
        if display_header is True:
            node = nodes.line(f'{name}', f"{name}")
        else:
            node = nodes.line()
        node += self._display_arg_parse(parser)
        return node

    def _parse_option(self, option):
        '''expect opt, opt(child)'''
        subparser, _, option = option.partition('(')
        assert option[-1] == ')'

        return subparser, option[:-1]

    def _display_arg_parse(self, parser):
        node = nodes.literal_block(rawsource=parser.help, text=parser.help+' ')
        return node

    def _load_parser(self, *, description=None):
        module_name = self.arguments[0]
        try:
            module = import_module(module_name)
        except ImportError:
            msg = f'Could not find module {module_name}'
            raise Exception(msg) from None

        cls = self.arguments[1]
        if hasattr(module, cls):
            obj = getattr(module, cls, None)
            #
            if not isinstance(obj, CommandlineInterface):
                raise ValueError(f"Obj '{cls}' in '{module_name}' is not a CommandlineInterface")
            if description is not None:
                obj.description = description
            return obj.get_parser()
        raise Exception(f"Module '{module_name}' contains no class '{cls}'")


def nice_format_dict(dct):
    import json
    return json.dumps(dct, indent=4)


def setup(app):
    #
    app.add_directive("colt", ColtDirective)
    app.add_directive("colt_qfile", ColtQFileDirective)
    app.add_directive("colt_questions", ColtQuestionsDirective)
    app.add_directive("colt_commandline", ColtCommandlineDirective)
    #
    return {'version': '0.1',
            'parallel_read_safe': True,
            'parallel_write_safe': True,
            }
