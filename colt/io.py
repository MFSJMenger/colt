from abc import abstractmethod, ABC
from copy import deepcopy
import json
import re
import os

from .config import FileIterable
from .validator import file_exists, ValidatorErrorNotInChoices


class ColtInputError:
    """Class to handle error messages for input setting"""

    __slots__ = ('_errors', '_current')

    def __init__(self):
        self._errors = []
        self._current = None

    def __str__(self):
        if self.is_none():
            return ""

        return "\n".join(f"{block}" for block in self._errors)

    def is_none(self):
        return len(self._errors) == 0

    def append(self, block_error):
        self._errors.append(block_error)


class QuestionVisitor(ABC):
    """Base class to define visitors for the question form
    the entry point is always the `QuestionForm`"""

    __slots__ = ()

    def visit(self, qform, **kwargs):
        """Visit a question form"""
        return qform.accept(self, **kwargs)

    @abstractmethod
    def visit_qform(self, qform, **kwargs):
        pass

    @abstractmethod
    def visit_question_block(self, block):
        pass

    @abstractmethod
    def visit_concrete_question_select(self, question):
        pass

    @abstractmethod
    def visit_concrete_question_hidden(self, question):
        pass

    @abstractmethod
    def visit_concrete_question_input(self, question):
        pass

    @abstractmethod
    def visit_literal_block(self, block):
        pass

    def visit_subquestion_block(self, block):
        """visit subquestion blocks"""
        answer = block.answer
        if answer in ("", None):
            return {}
        #
        return block.cases[answer].accept(self)

    def on_empty_entry(self, answer, question):
        pass

    def on_value_error(self, answer, question):
        pass

    def on_wrong_choice(self, answer, question):
        pass

    def set_answer(self, question, answer):
        return question.set(answer, on_empty_entry=self.on_empty_entry,
                            on_value_error=self.on_value_error,
                            on_wrong_choice=self.on_wrong_choice)

    def _visit_block(self, block):
        """visit a block, first only concrete questions, then the subblocks"""
        for question in block.concrete.values():
            question.accept(self)
        #
        for subblock in block.blocks.values():
            subblock.accept(self)


class ConfigFileReader:

    _is_header = re.compile(r"\s*\[\s*(?P<header>.*)\]\s*")
    _is_entry = re.compile(r"(?P<key>.*)=(?P<value>.*)")

    comment = '#'

    def __init__(self, qform):
        self.qform = qform
        self.error = None

    def read(self, filename):
        """ """
        try:
            filename = file_exists(filename)
        except ValueError:
            raise SystemExit(f"No such file as '{filename}'") from None
        #
        fileiter = FileIterable(filename)
        # Parse file and store values
        self.error = ColtInputError()
        #
        valid_block = True
        self.qform.set_active_block('')
        for filenumber, line in fileiter:
            header = self._header(line)
            # handle headers and literal blocks
            if header is not None:
                header = self._handle_literal_blocks(header, fileiter)
                # end
                if header is None:
                    break
                valid_block = header in self.qform.blocks
                if valid_block is True:
                    self.qform.set_active_block(header)
                continue
            # Handle entries
            line = line.strip()
            if line == "" or line.startswith(self.comment):
                continue
            key, value = self._entry(line)
            if key is not None:
                if valid_block is True:
                    self.qform.set_answer(key, value)
                continue
            self.error.append(f"Error understanding line {filenumber}: {line} ")
        # catch basic errors in the field
        if not self.error.is_none():
            raise ValueError(str(self.error))

    def _handle_literal_blocks(self, header, fileiter):
        # handle literal block and find next header
        while header in self.qform.literals:
            value, _header = self._parse_literals(header, fileiter)
            if value not in ('', None):
                self.qform.set_literal_block(header, value, is_fullname=True)
            header = _header
        return header

    def _header(self, line):
        match = self._is_header.match(line)
        if match is None:
            return None
        return match['header'].strip()

    def _parse_literals(self, currentheader, fileiter):
        string = []
        for linenumber, line in fileiter:
            header = self._header(line)
            if header is not None:
                return "".join(string), header
            string.append(line)
        return "".join(string), None

    def get_literals(self, header, literals, fileiter):
        literals[header], header = self._parse_literals(header, fileiter)
        # if next block is also a literalblock continue
        if header in literals:
            return self.get_literals(header, literals, fileiter)
        # return next block
        return header

    def _entry(self, line):
        match = self._is_entry.match(line)
        if match is None:
            return None, None
        return match['key'].strip(), match['value'].strip()


class JsonQuestionSetter(QuestionVisitor):
    """Visitor to write the answers to a string"""

    __slots__ = ('json', 'qform')

    def __init__(self, qform):
        self.json = None
        self.qform = qform

    def visit_qform(self, qform, **kwargs):
        if 'filename' not in kwargs:
            raise ValueError("Filename needs to be provided")
        with open(kwargs['filename'], 'r') as fh:
            self.json = json.load(fh)
        qform.form.accept(self)
        self.json = None

    def visit_question_block(self, block):
        # first all normal questions
        self.qform.set_active_block(block.name)
        #
        old_json = self.json
        for name, question in block.concrete.items():
            self.json = old_json.get(name, None)
            if self.json is not None:
                question.accept(self)
        #
        for name, subblock in block.blocks.items():
            self.json = old_json.get(name, None)
            if self.json is not None:
                subblock.accept(self)
        self.json = old_json

    def visit_concrete_question_select(self, question):
        answer = self.json.get('__answer__', None)
        if answer is not None:
            self.qform.set_answer(question.short_name, answer)

    def visit_concrete_question_hidden(self, question):
        self.qform.set_answer(question.short_name, self.json)

    def visit_concrete_question_input(self, question):
        self.qform.set_answer(question.short_name, self.json)

    def visit_literal_block(self, block):
        self.qform.set_literal_block(block.short_name, self.json)

    def visit_subquestion_block(self, block):
        """visit subquestion blocks"""
        answer = block.main_question.answer
        self.json = self.json.get(answer, None)
        if self.json is None:
            return
        subblock = block.cases.get(answer)
        if subblock is None:
            return
        subblock.accept(self)


class JsonReader:

    def __init__(self, qform):
        self.qform = qform
        self.reader = JsonQuestionSetter(qform)

    def read(self, filename):
        print("qform = ", self.qform.qform)
        self.reader.visit(self.qform.qform, filename=filename)


class QFormSetter:

    def __init__(self, qform):
        self.qform = qform
        self._active_block_name = ''
        self._active_block = self.qform.blocks[self._active_block_name]

    def accept(self, visitor, **kwargs):
        return visitor.visit_qform(self.qform, **kwargs)

    @property
    def blocks(self):
        return self.qform.blocks

    @property
    def literals(self):
        return self.qform.literals

    def set_active_block(self, newvalue, exit_on_error=False):
        if newvalue not in self.qform.blocks:
            return False
        self._active_block_name = newvalue
        self._active_block = self.qform.blocks[newvalue]
        return True

    def set_answer(self, key, answer, linenumber=None):
        question = self._active_block.get(key, None)
        if question is None:
            return f"unknown key '{key}' in '{self._active_block_name}'"

        if answer == "":
            if question.is_optional:
                question.is_set = True
                question.is_set_to_empty = True
            return None
        #
        try:
            question.answer = answer
        except ValueError as e:
            return f"{key} = {answer}, ValueError: {e}"
        except ValidatorErrorNotInChoices as err_choices:
            return f"{key} = {answer}, Wrong Choice: {err_choices}"
        return None

    def set_literal_block(self, name, value, is_fullname=False):
        if is_fullname is True:
            literal = self.qform.literals.get(name, None)
        else:
            literal = self._active_block.get(name, None)
        if literal is not None:
            literal.answer = value


class QFormComparer(QFormSetter):

    def __init__(self, qform):
        super().__init__(qform)
        self._answers = None

    def get_current_answers(self):
        return {blockname: {name: question.get_answer_as_string()
                            for name, question in block.items()}
                for blockname, block in self.qform.blocks.items()}

    def set_answer(self, key, answer, linenumber=None):
        """Set the answer for an concrete question in the active block"""
        question = self._active_block.get(key, None)
        if question is None:
            return f"unknown key '{key}' in '{self._active_block_name}'"

        if answer == "":
            if question.is_optional:
                question.is_set = True
                question.is_set_to_empty = True
                self._answers[self._active_block_name][key] = answer
            return None
        #
        try:
            question.validator.validate(answer)
        except ValueError as e:
            return f"{key} = {answer}, ValueError: {e}"
        except ValidatorErrorNotInChoices as err_choices:
            return f"{key} = {answer}, Wrong Choice: {err_choices}"
        self._answers[self._active_block_name][key] = answer
        return None

    def set_literal_block(self, name, value, is_fullname=False):
        """Set the value for an literal block"""
        if is_fullname is True:
            literal = self.qform.literals.get(name, None)
        else:
            literal = self._active_block.get(name, None)
        if literal is not None:
            self._answers[literal.name] = value
            literal.answer = value

    def compare(self, filenames, *, format=None, set_answers=False):
        defaults = self.get_current_answers()

        reader = ColtReader(self)
        total = {}
        for filename in filenames:
            self._answers = deepcopy(defaults)
            reader.read(filename, format=format)
            total[filename] = self._answers
            self._answers = None

        print(total)
        first = total[filenames[0]]
        for filename in filenames[1:]:
            if (first != total[filename]):
                raise Exception
        if set_answers is True:
            self.qform.set_answers_from_dct(first, raise_error=True)


class ColtReader:

    reader = {'ini': ConfigFileReader, 'json': JsonReader}

    def __init__(self, qform, default_format='ini'):
        self.qform = qform
        self.is_setter = True if isinstance(qform, QFormSetter) else False
        if default_format not in self.reader:
            raise ValueError("could not find parser for format..")
        self._default_format = default_format

    def read(self, filename, format=None):
        """Read input from file"""
        if format is None:
            format = self._select_format(filename)
        else:
            if format not in self.reader:
                raise ValueError(f"format '{format}' unknown!")
        reader = self._select_readercls(format)
        if self.is_setter is True:
            reader = reader(self.qform)
        else:
            reader = reader(QFormSetter(self.qform))
        reader.read(filename)

    def compare(self, filenames, format=None, set_answers=True):
        compare = QFormComparer(self.qform)
        compare.compare(filenames, format=format, set_answers=set_answers)

    def _select_readercls(self, format):
        reader = self.reader.get(format, None)
        if reader is None:
            raise ValueError(f"Cannot handle format '{format}'")
        return reader

    def _select_format(self, filename):
        _, format = os.path.splitext(filename)
        if format != '':
            format = format[1:]
            if format in self.reader:
                return format
        return self._default_format


class WriteJsonVisitor(QuestionVisitor):
    """Visitor to write the answers to a string"""

    __slots__ = ()

    def visit_qform(self, qform, **kwargs):
        data = qform.form.accept(self)
        return json.dumps(data, indent=4)

    def visit_question_block(self, block):
        # first all normal questions
        dct = {}
        for name, question in block.concrete.items():
            res = question.accept(self)
            if res is not None:
                dct[name] = res
        #
        for name, subblock in block.blocks.items():
            dct[name] = subblock.accept(self)
        return dct

    def visit_concrete_question_select(self, question):
        return question.get_answer_as_string()

    def visit_concrete_question_hidden(self, question):
        pass

    def visit_concrete_question_input(self, question):
        return question.get_answer_as_string()

    def visit_literal_block(self, block):
        answer = block.answer
        if answer.is_none is True:
            return None
        return answer.data

    def visit_subquestion_block(self, block):
        """visit subquestion blocks"""
        answer = block.main_question.answer
        dct = {'__answer__': answer}
        if answer is None:
            return {}
        subblock = block.cases.get(answer)
        if subblock is None:
            return {}
        dct[answer] = subblock.accept(self)
        return dct


class WriteConfigVisitor(QuestionVisitor):
    """Visitor to write the answers to a string"""

    __slots__ = ('txt', '_ignore_literals')

    def __init__(self):
        self.txt = ''

    def visit_qform(self, qform, **kwargs):
        self.txt = ''
        self._ignore_literals = True
        for blockname in qform.get_blocks():
            # normal blocks
            qform[blockname].accept(self)
        self._ignore_literals = False
        #
        for block in qform.literals.values():
            # literal blocks
            block.accept(self)
        #
        txt = self.txt
        self.txt = ''
        return txt

    def visit_question_block(self, block):
        """Visit concrete questions"""
        if block.name != '':
            self.txt += f'\n[{block.name}]\n'
        # first all normal questions
        for question in block.concrete.values():
            question.accept(self)

    def visit_concrete_question_select(self, question):
        self.txt += f'{question.short_name} = {question.get_answer_as_string()}\n'

    def visit_concrete_question_hidden(self, question):
        pass

    def visit_concrete_question_input(self, question):
        self.txt += f'{question.short_name} = {question.get_answer_as_string()}\n'

    def visit_literal_block(self, block):
        if self._ignore_literals:
            return
        answer = block.answer
        if answer.is_none is True:
            return
        self.txt += f'[{block.id}]\n{answer}\n'

    def visit_subquestion_block(self, block):
        """visit subquestion blocks"""
        raise Exception("should never arrive in subquestion block!")


class ColtWriter:

    writer = {'ini': WriteConfigVisitor, 'json': WriteJsonVisitor}

    def __init__(self, qform, default_format='ini'):
        self.qform = qform
        if default_format not in self.writer:
            raise ValueError("could not find parser for format..")
        self._default_format = default_format

    def write(self, filename, format=None):
        """Write data to filename"""
        if format is None:
            format = self._select_format(filename)
        else:
            if format not in self.writer:
                raise ValueError(f"format '{format}' unknown!")
        print(f"Selected format = '{format}'")
        writer = self._select_writer(format)
        with open(filename, 'w') as fhandle:
            fhandle.write(writer.visit(self.qform))

    def _select_format(self, filename):
        _, format = os.path.splitext(filename)
        if format != '':
            format = format[1:]
            if format in self.writer:
                return format
        return self._default_format

    def _select_writer(self, format):
        if format is None:
            format = self._default_format
        writer = self.writer.get(format, None)
        if writer is None:
            raise ValueError(f"Cannot handle format '{format}'")
        return writer()
