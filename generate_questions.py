import re
import configparser
from collections import namedtuple

from colt import Question, ConditionalQuestion


question_config = """
a = 10
b = 100
hallo = wtf

[hallo(wtf)]
key = 123

[hallo(wtf2)]
key = 321

[hallo(wtf)::code(qchem)]
basis = sto-3g
functional = cam-b3lyp

[hallo(wtf)::code(gaussian)]
basis = sto-3g
functional = cam-b3lyp

[hallo(wtf2)::code]
a = 1
b = 1

[config]
value = 10

[config::input]
key = 123
value = ficken

"""

default = '__QUESTIONS__'

def parse_string(string):
    # add [DEFAULT] for easier parsing!
    if not string.lstrip().startswith(f'[{default}]'):
        string = f'[{default}]\n' + string
    #
    config = configparser.ConfigParser()
    config.read_string(string)
    return config


def parse_question_line(key, line):
    line = line.split("::")
    len_line = len(line)
    if len_line == 1:
        return Question(question=key, default=line[0])
    if len_line == 2:
        return Question(question=key, default=line[0], typ=line[1]) 
    if len_line == 3:
        return Question(default=line[0], typ=line[1], question=line[2]) 

def is_subblock(block):
    if any(key in block for key in ('::', '(', ')')):
        return True
    return False

def get_keys(block):
    return block.split('::')

parse_conditionals_helper = re.compile(r"(?P<key>.*)\((?P<decission>.*)\)")
Conditionals = namedtuple("Conditionals", ["key", "decission"])

def is_decission(key):
    conditions = parse_conditionals_helper.match(key)
    if conditions is None:
        return False
    return Conditionals(conditions.group("key"), conditions.group("decission"))

def get_next_section(sections, key):

    conditions = is_decission(key)
    if conditions is False:
        return sections.get(key, None)

    key, decission = conditions
    sections = sections.get(key, None)
    if sections is not None:
        return sections.get(decission, None)
    return sections


def get_section(sections, block):
    keys = block.split('::')
    #
    final_key = keys[-1]
    # we are not at the end!
    for key in keys[:-1]:
        sections = get_next_section(sections, key)
        if sections is None:
            return
    # do this
    conditions = is_decission(final_key)
    if conditions is False:
        sections[final_key] = {}
        return sections[final_key]

    key, decission = conditions
    argument = sections.get(key, None)
    if argument is None:
        # no default question defined, should also give warning?
        questions = ConditionalQuestion(key, Question(key), {decission: {}})
        sections[key] = questions
        return questions.subquestions[decission]
    if isinstance(argument, Question):
        # default question defined, but first found case
        questions = ConditionalQuestion(key, argument, {decission: {}})
        sections[key] = questions
        return questions.subquestions[decission]
    if isinstance(argument, ConditionalQuestion):
        # another found case
        argument.subquestions[decission] = {}
        return argument.subquestions[decission]
    raise Exception("cannot handle anything else")

def generate_questions(config):
    # linear parser
    questions = {}

    for key, value in config[default].items():
        questions[key] = parse_question_line(key, value)

    afterwards = [section for section in config.sections() if is_subblock(section)]

    for section in config.sections():
        if section == default:
            continue
        if is_subblock(section):
            continue
        subquestions = {}
        for key, value in config[section].items():
            subquestions[key] = parse_question_line(key, value)
        questions[section] = subquestions

    for section in afterwards:
        subquestions = get_section(questions, section)
        if subquestions is None:
            continue
        for key, value in config[section].items():
            subquestions[key] = parse_question_line(key, value)

    return questions

config = parse_string(question_config)
print(generate_questions(config))


