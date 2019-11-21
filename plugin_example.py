from colt import PluginBase, Colt


class Example(Colt):

    _questions = """
        nstates = :: int
        key = hi
        root = :: int
    """


class QMFactory(PluginBase):
    """QMFactory"""


    _plugins_storage = '_software'
    _is_plugin_factory = True

    _questions = """
        software =
    """

    @classmethod
    def _generate_subquestions(cls, questions):
        print("is that here ever called???")
        questions.generate_cases("software", {name: sampling.questions
                                              for name, sampling in cls._software.items()})
        questions.add_questions_to_block(Example.questions)

    @classmethod
    def create_interface(cls):            
        questions = cls.generate_questions("qm", config='factory2.ini')
        answer = questions.ask('factory2.ini')
        print(answer['software'].value)
        print(cls._software)
        return cls.get_interface(answer['software'].value)

    @classmethod
    def get_interface(cls, name):
        return cls._software.get(name)


class QMBase(QMFactory):

    subquestions : 'inherited'
    _register_plugin = False

    def say_hallo(self):
        print("hallo")


class QChemFactory(QMBase):

    subquestions : 'inherited'

    _plugins_storage = '_software'
    _is_plugin_factory = True
    _is_plugin_specialisation = True

    _questions = """
        software = 
    """

    @classmethod
    def _generate_subquestions(cls, questions):
        print('wuhu...seems to work')
        print(f"cls = {type(cls)}")
        print(f"cls = {cls.__name__}")


class QChemBase(QChemFactory):
    _register_plugin = False

    def say_hallo(self):
        print("I am a qchem specialisation")


class QChemTDDFT(QChemBase):
    _questions = """
        qchem = True :: bool
        basis = sto-3g
        functional = cam-b3lyp
    """


class QChemADC(QChemBase):
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


print("ALL")
print(QMFactory())
print("QCHEM")
print(QChemFactory.create_interface())
