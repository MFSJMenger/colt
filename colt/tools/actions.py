from ..plugins import Plugin


__all__ = ['create_action']


def _create_factory(name, user_input, options_name, general_action, description):
    """Generates a Plugin Factory for commandline parsing """

    if user_input is None:
        user_input = "options =  :: str"

    if options_name is None:
        options_name = 'options'

    if general_action is None:
        @classmethod
        def general_action(cls, config):
            pass

    if not isinstance(general_action, classmethod):
        general_action = classmethod(general_action)

    @classmethod
    def _extend_user_input(cls, questions):
        questions.generate_cases(options_name, {action.name: action.colt_user_input
                                                for action in cls.plugins.values()})

    @classmethod
    def from_config(cls, config):
        cls.general_action(config)
        config = config[options_name]
        for action in cls.plugins.values():
            if action.name == config.value:
                return action.from_config(config)
        raise Exception(f"Action '{config[config.value]}' unknown")

    return type(name + 'Factory', (Plugin, ), {
        'name': name,
        '_colt_description': description,
        '_is_plugin_factory': True,
        '_plugins_storage': '_actions',
        'options_name': options_name,
        'general_action': general_action,
        '_extend_user_input': _extend_user_input,
        '_user_input': user_input,
        'from_config': from_config,
    })


def _create_base_action(name, Factory):

    @classmethod
    def from_config(cls, config):
        if not isinstance(cls.run, staticmethod):
            cls.run = staticmethod(cls.run)
        return cls.run(**config)

    def run(**options):
        raise NotImplementedError

    return type(name + 'Action', (Factory, ), {
        '_register_plugin': False,
        'from_config': from_config,
        'run': run,
        })


class ActionDecorator:
    """Decorator to create actions (from config/commandline callable functions)"""

    def __init__(self, Factory, BaseAction):
        self._Factory = Factory
        self.Action = BaseAction
        self._subparser = {}

    def run(self):
        return self._Factory.from_commandline()

    def add_subparser(self, name, description=None, user_input=None,
                      options_name=None, general_action=None, overwrite=False):
        if overwrite is False and name in self._Factory.plugins.keys():
            raise ValueError(f"Name '{name}' already registered as plugin")
        Factory, deco = _create_action_factory_and_deco(name, user_input, options_name, general_action, description)
        # register the factory
        self._Factory.add_plugin(name, Factory) 
        return deco

    def __call__(self):
        return self.run()

    # normal function call
    def register(self, description, user_input,
                       name=None, lazy_imports=None):
        def _action_creator(func):
            nonlocal name
            if name is None:
                name = func.__name__
            data = {'_user_input': user_input, 'run': staticmethod(func), 'name': name}
            if description is not None:
                data['_colt_description'] = description
            if lazy_imports is not None:
                data['_lazy_imports'] = lazy_imports
            # just create the type for registration
            type(name, (self.Action, ), data)
            return func
        return _action_creator

class Marker:

    """Class Marker"""

    __slots__ = ('description', 'function', 'user_input')

    def __init__(self, description, user_input):
        self.description = description
        self.user_input = user_input
        self.function = None

    def __call__(self, function):
        self.function = function
        return self

class _ColtActionMaker(ABCMeta):

    def __prepare__(cls, metacls, *args, **kwargs):
        return {'register': Marker}

    def __new__(cls, name, bases, clsdict):
        """Modify clsdict before the new method of the metaclass is called"""
        markers = {}
        for name, value in clsdict.items():
            if isinstance(value, Marker):
                markers[name] = (value.description, value.user_input)
        for name in markers:
            clsdict[name] = clsdict[name].function

        action_name = clsdict.get('_colt_action_name', 'commandline')
        if '__init__' in clsdict:
            __init__ = clsdict['__init__']
            def _init(self, *args, **kwargs):
                action = create_action('value')
                for name, (description, user_input) in markers.items():
                    action.register(description, user_input)(getattr(self, name))
                setattr(self, action_name, action)
                __init__(self, *args, **kwargs)
        else:
            def _init(self, *args, **kwargs):
                action = create_action('value')
                for name, (description, user_input) in markers.items():
                    action.register(description, user_input)(getattr(self, name))
                setattr(self, action_name, action)
                super().__init__(*args, **kwargs)

        #
        clsdict['__init__'] = _init
        #
        return ABCMeta.__new__(cls, name, bases, clsdict)


class ColtAction(metaclass=ColtActionMaker):
    pass


def _create_action_factory_and_deco(name, user_input=None, options_name=None, 
                                    general_action=None, description=None):
    """Construct Action Factory and Action Decorator"""
    Factory = _create_factory(name, user_input, options_name, general_action, description)
    BaseAction = _create_base_action(name, Factory)
    deco = ActionDecorator(Factory, BaseAction)
    return Factory, deco


def create_action(name, user_input=None, options_name=None, general_action=None, description=None):
    """Create bassic action generator using colt"""
    _, deco = _create_action_factory_and_deco(name, user_input, options_name, general_action, description)
    return deco
