from .qform import QuestionForm, ValidatorErrorNotInChoices


def empty_entry(answer, settings):
    print("Empty entry not possiple, please enter answer")


def value_error(answer, settings):
    print(f"Could not parse '{answer}', should be '{settings['typ']}', redo")


def wrong_choice(answer, settings):
    print(f"Answer '{answer}' not in choices!")


class AskQuestions(QuestionForm):
    """Questionform to ask questions from the commandline"""

    _helpkeys = (":help", ":h")
    _callbacks = {'EmptyEntry': empty_entry,
                  'ValueError': value_error,
                  'WrongChoice': wrong_choice,
                  }

    def __init__(self, questions, config=None, presets=None):
        QuestionForm.__init__(self, questions, config=config,
                              presets=presets, callbacks=self._callbacks)

    def ask(self, config=None, ask_all=False, presets=None):
        """Main routine to get settings from the user,
           if all answers are set, and ask_all is not True

            Kwargs:
                config, str:
                    name of an existing config file

                ask_all, bool:
                    whether to ask all questions, or skip those already set

                presets, str:
                    presets to be used
        """
        self.set_answers_and_presets(config, presets)
        if ask_all is True:
            return self._ask_impl(ask_all=ask_all)
        #
        if self.is_all_set:
            return self.get_answers()
        #
        return self._ask_impl(ask_all=ask_all)

    def check_only(self, config=None, presets=None):
        """Check that all answers set by config are correct and
           return the settings

            Kwargs:
                config, str:
                    name of an existing config file

                presets, str:
                    presets to be used
        """
        self.set_answers_and_presets(config, presets)
        return self.get_answers(check=True)

    def generate_input(self, filename, config=None, presets=None, ask_all=False):
        #
        self.set_answers_and_presets(config, presets)
        #
        answer = self.ask(presets=presets, ask_all=ask_all)
        self.write_config(filename)
        return answer

    def _ask_impl(self, config=None, ask_all=False, presets=None):
        """Actuall routine to get settings from the user

            Kwargs:
                config, str:
                    name of an existing config file

                ask_all, bool:
                    whether to ask all questions, or skip those already set

                presets, str:
                    presets to be used
        """
        self.set_answers_and_presets(config, presets)
        for name, setting in self.setup_iterator(presets=presets):
            if name != "":
                print(f"[{name}]")
            for _, question in setting['fields'].items():
                self._select_question_and_ask(question, ask_all=ask_all)
        #
        if config is not None:
            self.write_config(config)
        #
        return self.get_answers(check=False)

    def _select_question_and_ask(self, settings, ask_all=False):
        if settings['type'] in ('select', 'input'):
            return self._ask_question_concrete_question(settings, ask_all=ask_all)
        if settings['type'] == 'literal':
            return None
        raise Exception(f"unknown type {settings['type']}")

    def _ask_question_concrete_question(self, settings, ask_all=False):
        if ask_all is True or settings['is_set'] is False:
            text = self._generate_question_text(settings)
            self._ask_question(text, settings['self'], None)

    def _generate_question_text(self, settings):
        if settings['type'] == 'select':
            return self._select_question_text(settings)
        if settings['type'] == 'input':
            return self._input_question_text(settings)
        raise Exception(f"unknown type {settings['type']}")

    def _ask_question(self, text, question, comment):
        """Ask the question, and handle events like :h, :help"""
        answer = input(text).strip()  # strip is important!
        if any(answer == helper for helper in self._helpkeys):
            if comment is None:
                print("No help available")
            else:
                print(comment)
            return self._ask_question(text, question, comment)
        elif question.set(answer) is True:
            return
        return self._ask_question(text, question, comment)

    @staticmethod
    def _select_question_text(settings):
        txt = f"{settings['label']}"
        if settings['value'] is None:
            txt += f" [optional]"
        elif settings['value'] != "":
            txt += f" [{settings['value']}]"
        txt += ", choices = (%s)" % (", ".join(str(opt) for opt in settings['options']))
        return txt + ": "

    @staticmethod
    def _input_question_text(settings):
        txt = f"{settings['label']}"
        if settings['value'] is None:
            txt += f" [optional]"
        elif settings['value'] != "":
            txt += f" [{settings['value']}]"
        return txt + ": "
