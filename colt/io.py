from abc import abstractmethod, ABC
import json
import re
import os

from .config import FileIterable
from .validator import file_exists


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
        # Parse file and store values
        self.error = ColtInputError()
        #
        active_block = ""
        valid_block = True
        try:
            filename = file_exists(filename)
        except ValueError:
            raise SystemExit(f"No such file as '{filename}'") from None
        #
        fileiter = FileIterable(filename)
        for filenumber, line in fileiter:
            header = self._header(line)
            # handle headers and literal blocks
            if header is not None:
                header = self._handle_literal_blocks(header, fileiter)
                # end
                if header is None:
                    break
                valid_block = header in self.qform.blocks
                active_block = header
                continue
            # Handle entries
            line = line.strip()
            if line == "" or line.startswith(self.comment):
                continue
            key, value = self._entry(line)
            if key is not None:
                if valid_block is True:
                    self._handle_concrete_answer(active_block, key, value)
                continue
            self.error.append(f"Error understanding line {filenumber}: {line} ")
        # catch basic errors in the field
        if not self.error.is_none():
            raise ValueError(str(self.error))

    def _handle_concrete_answer(self, blockname, key, answer):
        block = self.qform.blocks[blockname]
        if key not in block:
            print(f"unknown key '{key}' in '{blockname}'")
            return
        question = block[key]
        if answer == "":
            if question.is_optional:
                question.is_set = True
                question.is_set_to_empty = True
            return
        #
        try:
            question.answer = answer
        except ValueError as e:
            self.error.add(key, f"{answer}, ValueError: {e}", linenumber)
        except ValidatorErrorNotInChoices as err_choices:
            self.error.add(key, f"{answer}, Wrong Choice: {err_choices}", linenumber)

    def _handle_literal_blocks(self, header, fileiter):
        # handle literal block and find next header
        while header in self.qform.literals:
            value, _header =  self._parse_literals(header, fileiter)
            if value not in ('', None):
                self.qform.literals[header].answer = value
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

    __slots__ = ('json',)

    def __init__(self):
        self.json = None

    def visit_qform(self, qform, **kwargs):
        if 'filename' not in kwargs:
            raise ValueError("Filename needs to be provided")
        with open(kwargs['filename'], 'r') as fh:
            self.json = json.load(fh)
        qform.form.accept(self)
        self.json = None

    def visit_question_block(self, block):
        # first all normal questions
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
        print(f"answer = '{answer}'")
        if answer is not None:
            question.answer = answer

    def visit_concrete_question_hidden(self, question):
        question.answer = self.json

    def visit_concrete_question_input(self, question):
        question.answer = self.json

    def visit_literal_block(self, block):
        block.answer = self.json

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
        self.reader = JsonQuestionSetter()

    def read(self, filename):
        self.reader.visit(self.qform, filename=filename)


class ColtReader:

    reader = {'ini': ConfigFileReader, 'json': JsonReader}

    def __init__(self, qform, default_format='ini'):
        self.qform = qform
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
        print(f"Selected format = '{format}'")
        reader = self._select_reader(format)
        reader.read(filename)

    def _select_reader(self, format):
        reader = self.reader.get(format, None)
        if reader is None:
            raise ValueError(f"Cannot handle format '{format}'")
        return reader(self.qform)

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
        for block in qform.literals.items():
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
