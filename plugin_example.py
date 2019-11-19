from colt import PluginBase, Colt

class Example(Colt):

    _questions = """
        nstates = :: int
        key = hi
        root = :: int
    """


class QMFactory(PluginBase):

    __plugins_storage = '_software'
    __is_plugin_factory = True

    _questions = """
        software =
    """

    @classmethod
    def _generate_subquestions(cls, questions):
        questions.generate_cases("software", {name: sampling.questions
                                              for name, sampling in cls._software.items()})
        questions.add_questions_to_block(Example.questions)

    def __init__(self):            
        questions = self.generate_questions("qm", config='factory.ini')
        questions.check_only('factory2.ini')

    @classmethod
    def get_interface(cls, name):
        return cls._software.get(name, None)

class QMBase(QMFactory):
    __register_plugin = False
    _questions = "" # init as empty string per default

    def say_hallo(self):
        print("hallo")

class QChem(QMBase):
    _questions = """
        qchem = True :: bool
        basis = sto-3g
        functional = cam-b3lyp
    """

class Turbomole(QMBase):
    _questions = """
        qchem = True :: bool
        basis = sto-3g
        functional = cam-b3lyp
    """

class Gaussian(QMBase):
    _questions = """
        qchem = True :: bool
        basis = sto-3g
        natoms = :: int
        functional = cam-b3lyp
    """

QMFactory()
