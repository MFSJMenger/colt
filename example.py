from colt import AskQuestions
from colt import Question, ConditionalQuestion


qchem = ConditionalQuestion("method",
            Question("Which method do you want to use?", 'str', "cc2"),
            {'tddft': {'basis': Question('Which basisset?'),
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


questions = AskQuestions("sh", qm_software, config="example.ini")
questions.ask('example_out.ini')
