from ..plugins import Plugin

__all__ = ['create_action']

def _create_factory(name, user_input, options_name, general_action):
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
        '_is_plugin_factory': True,
        '_plugins_storage': '_actions',
        'options_name': options_name,
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


def _create_action_decorator(BaseAction):
    def action(description, user_input,
               name=None, lazy_imports=None):
        def _wrapper(func):
            nonlocal name
            if name is None:
                name = func.__name__
            data = {'_user_input': user_input, 'run': staticmethod(func), 'name': name}
            if description is not None:
                data['_colt_description'] = description
            if lazy_imports is not None:
                data['_lazy_imports'] = lazy_imports
            # just create the type for registration
            type(name, (BaseAction, ), data)
            return func
        return _wrapper
    return action


def create_action(name, user_input=None, options_name=None, general_action=None):
    """Create bassic action generator using colt"""
    Factory = _create_factory(name, user_input, options_name, general_action)
    BaseAction = _create_base_action(name, Factory)
    deco = _create_action_decorator(BaseAction)
    return Factory.from_commandline(as_parser=True), BaseAction, deco
