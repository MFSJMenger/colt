from .qform import QuestionForm, ValidatorErrorNotInChoices


class AskQuestions(QuestionForm):

    _helpkeys = (":help", ":h")

    def __init__(self, questions, config=None):
        QuestionForm.__init__(self, questions)
        if config is not None:
            self.set_answers_from_file(config)

    def ask(self, ask_all=False):
        for name, setting in self.setup_iterator():
            if name != "":
                print(f"[{name}]")
            for key, value in setting['fields'].items():
                self._select_question_and_ask(key, value, ask_all=ask_all)
        return self.get_answers(check=False)

    def check_only(self, configfile=None):
        if configfile is not None:
            self.set_answers_from_file(configfile)
        return self.get_answers(check=True)

    def _select_question_and_ask(self, name, settings, ask_all=False):
        if settings['type'] in ('select', 'input'):
            return self._ask_question_concrete_question(name, settings, ask_all=ask_all)
        if settings['type'] in ('literal'):
            return
        raise Exception(f"unknown type {settings['type']}")

    def _ask_question_concrete_question(self, name, settings, ask_all=False):
        if ask_all is True or settings['is_set'] is False:
            text, accept_enter, default = self._generate_question_text(name, settings)
            self._ask(settings['id'], text, accept_enter, default)
        #

    def _generate_question_text(self, name, settings):
        if settings['type'] == 'select':
            return self._select_question_text(name, settings)
        if settings['type'] == 'input':
            return self._input_question_text(name, settings)
        raise Exception(f"unknown type {settings['type']}")

    def _ask(self, idname, text, accept_enter, default):
        answer = self._perform_ask_question(text, accept_enter, default)
        try:
            self.set_answer_f(idname, answer)
            return
        except ValueError:
            print(f"Unknown input type '{answer}', redo")
        except ValidatorErrorNotInChoices:
            print(f"Answer '{answer}' not in choices!")
        return self._ask(idname, text, accept_enter, default)

    def _perform_ask_question(self, text, accept_enter, default, comment=None):
        answer = self._ask_question_implementation(text, accept_enter, default)
        if any(answer == helper for helper in self._helpkeys):
            print(comment)
            return self._perform_ask_question(text, accept_enter, default, comment)
        return answer

    def _ask_question_implementation(self, text, accept_enter, default):
        answer = input(text).strip()  # strip is important!
        if answer == "":
            if accept_enter is True:
                return default
            else:
                return self._ask_question_implementation(text, accept_enter, default)
        return answer

    def _select_question_text(self, name, settings):
        accept_enter = False
        txt = f"{settings['label']}"
        if settings['value'] != "":
            txt += f" [{settings['value']}], "
            accept_enter = True
        txt += "choices = (%s)" % (", ".join(str(opt) for opt in settings['options']))
        return txt + ": ", accept_enter, settings['value']

    def _input_question_text(self, name, settings):
        accept_enter = False
        txt = f"{settings['label']}"
        if settings['value'] != "":
            txt += f" [{settings['value']}]"
            accept_enter = True
        return txt + ": ", accept_enter, settings['value']
