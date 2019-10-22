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
}

qm_software = {'code': ConditionalQuestion("code",
            Question("What qm method do you want to use?", 'str', "qchem"),
            {'qchem': qchem, 'gaussian': gaussian}),
            'qmregion': Question("What are the qm atoms?", "ilist"),}


if __name__ == '__main__':
    questions = AskQuestions("sh", qm_software, config="ex.ini")
    questions.ask('ex.ini')
