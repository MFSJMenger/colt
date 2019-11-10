import re
import configparser
from collections import namedtuple
#
from colt import AskQuestions
from colt import Question, ConditionalQuestion

qchem = ConditionalQuestion("method",
            Question("Which method do you want to use?", 'str', "cc2"),
            {'tddft': {'basis':
                       {'dft': Question('Which basisset?'),
                        'hf': Question("what functional?"),},
                        'functional': Question('Which functional?')},
            'cc2': {'basis': Question('Which basisset?')},
        })

gaussian = {
        'basis': Question('Which basisset?'),
        'functional': Question('Which functional?'),
        'opt': { 
            'symm': Question('sym'),
            }
}

qm_software = {'code': ConditionalQuestion("code",
            Question("What qm method do you want to use?", 'str', "qchem"),
            {'qchem': qchem, 'gaussian': gaussian}),
            'qmmm': {
                'qmatoms': Question("What are the qm atoms?", "ilist"),
                }
            }

pattern = re.compile(r"(?P<code>.*)\((?P<decission>.*)\)")
Conditionals = namedtuple("Conditionals", ["code", "decission"])

def parse_conditionals(block):
    result = pattern.match(block)
    if result is None:
        return None
    return Conditionals(result.group("code"), result.group("decission"))

def get_question_block(questions, block):
    """Parse down the abstraction tree to extract
       particular questions based on their
       block name in the config file"""
    old_block, delim, new_block = block.partition('::')
    if new_block == "":
        # end of the recursive function
        return questions, old_block
    # Check for conditionals
    block_key, _, _ = new_block.partition('::')
    conditionals = parse_conditionals(block_key)
    #
    if conditionals is None:
        # go down the tree
        return get_question_block(questions[block_key], new_block)
    # Handle conditionals
    code, decission = conditionals
    return get_question_block(questions[code][decission], new_block)


def set_answers_from_config(questions, filename):
    parsed = configparser.ConfigParser(allow_no_value=True)
    parsed.read(filename)
    for section in parsed.sections():
        q, se = get_question_block(questions, section)
        if q is None:
            print(f"""Section = {section} unkown, maybe typo?""")
            continue
        for key, value in parsed[section].items():
            try:
                q[key].set_answer(value)
            except:
                print(f"""In Section({section}) key({key}) unkown, maybe typo?""")

if __name__ == '__main__':
    questions = AskQuestions("sh", qm_software, config="extrue2.ini")
#    set_answers_from_config(questions, "extrue2.ini")
    questions.ask("extrue2.ini")
        
