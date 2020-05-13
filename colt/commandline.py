import argparse
from argparse import Action
#
from .qform import QuestionForm, QuestionVisitor, split_keys, join_case
from .qform import ValidatorErrorNotInChoices


class CommandlineParserVisitor(QuestionVisitor):

    __slots__ = ('parser', 'block_name')

    def __init__(self):
        self.parser = None
        self.block_name = None

    def visit_qform(self, qform, description=None):
        parser = get_parser(description)
        self.parser = parser
        qform.form.accept(self)
        return parser

    def visit_question_block(self, block):
        for question in block.concrete.values():
            if question.is_subquestion_main is False:
                question.accept(self)
        #
        for block in block.blocks.values():
            block.accept(self)

    def visit_concrete_question_select(self, question):
        self.add_concrete_to_parser(question)

    def visit_concrete_question_input(self, question):
        self.add_concrete_to_parser(question)

    def visit_subquestion_block(self, block):
        #
        parser = self.parser
        block_name = self.block_name
        #
        comment = self.get_comment(block.main_question)
        subparser = parser.add_subparsers(action=SubQuestionAction, question=block.main_question, 
                                          help=f'{comment}')
        for case, subblock in block.cases.items():
            self.block_name = join_case(block.name, case)
            self.parser = subparser.add_parser(case)
            subblock.accept(self)
        self.parser = parser

    def _get_default_and_name(self, question):
        id_name = question.id
        if self.block_name is not None:
            id_name = id_name.replace(self.block_name, '') 
            if id_name[:2] == '::':
                id_name = id_name[2:]
        #
        default = question.answer
        if default not in ('', None):
            # default exists -> Optional Argument
            name = f"-{id_name}"
        else: 
            # default does not exist -> Positional Argument
            name = f"{id_name}"
            default = None
        return default, name

    def _get_validate(self, question):

        def _type(answer):
            try:
                question.set_answer(answer)
            except ValidatorErrorNotInChoices as e:
                raise ValueError(str(e)) from None
        
        _type.__name__ = question.typ
        return _type

    def get_comment(self, question):
        """get comment string"""
        choices = question.choices
        if choices is None:
            choices = ''
        #
        comment = f"{question.typ}, {choices}"
        if question.comment is not None:
            comment += f"\n{question.comment}"
        return comment

    def add_concrete_to_parser(self, question):
        default, name = self._get_default_and_name(question)
        #
        comment = self.get_comment(question)
        #
        self.parser.add_argument(name, metavar=question.label, type=self._get_validate(question),
                                 default=default, help=comment)

    def visit_literal_block(self, block):
        pass


class SubQuestionAction(Action):

    class _ChoicesPseudoAction(Action):

        def __init__(self, name, aliases, help):
            metavar = dest = name
            if aliases:
                metavar += ' (%s)' % ', '.join(aliases)
            Action.__init__(option_strings=[], dest=dest, help=help, metavar=metavar)

    def __init__(self, option_strings, prog, parser_class, 
                 required=True, help=None, question=None):
        #
        if question is None:
            raise Exception("Need question set for SubquestionAction")
        self.question = question
        # set the name of the metavar
        metavar=self.question.name
        dest=argparse.SUPPRESS
        #
        self._prog_prefix = prog
        self._parser_class = parser_class
        self._name_parser_map = {}
        #
        Action.__init__(self, 
                option_strings=option_strings,
                dest=argparse.SUPPRESS,
                nargs=argparse.PARSER,
                choices=self._name_parser_map,
                required=required,
                help=help,
                metavar=metavar)

    def add_parser(self, name, **kwargs):
        # set prog from the existing prefix
        if kwargs.get('prog') is None:
            kwargs['prog'] = '%s %s' % (self._prog_prefix, name)

        aliases = kwargs.pop('aliases', ())

        # create a pseudo-action to hold the choice help
        if 'help' in kwargs:
            help = kwargs.pop('help')
            choice_action = self._ChoicesPseudoAction(name, aliases, help)
            self._choices_actions.append(choice_action)

        # create the parser and add it to the map
        parser = self._parser_class(**kwargs)
        self._name_parser_map[name] = parser

        # make parser available under aliases also
        for alias in aliases:
            self._name_parser_map[alias] = parser

        return parser

    def __call__(self, parser, namespace, values, option_string=None):
        parser_name = values[0]
        arg_strings = values[1:]

        if self.question.set(parser_name) is True:
            parser = self._name_parser_map.get(parser_name, None)
        else:
            args = {'parser_name': parser_name,
                    'choices': ', '.join(self._name_parser_map)}
            msg = _('unknown parser %(parser_name)r (choices: %(choices)s') % args
            raise argparse.ArgumentError(self, msg)


        subnamespace, arg_strings = parser.parse_known_args(arg_strings, None)
        for key, value in vars(subnamespace).items():
            setattr(namespace, key, value)
        
        if arg_strings:
            vars(namespace).setdefault(_UNRECOGNIZED_ARGS_ATTR, [])
            getattr(namespace, _UNRECOGNIZED_ARGS_ATTR).extend(arg_strings)


def get_config_from_commandline(questions, description=None, presets=None):
    #
    visitor = CommandlineParserVisitor()
    #
    qform = QuestionForm(questions, presets=presets)
    #
    parser = visitor.visit(qform)
    # parse commandline args
    parser.parse_args()
    return qform.get_answers()


def get_parser(description):
    return argparse.ArgumentParser(description=description,
                                   formatter_class=argparse.RawTextHelpFormatter)
