from .colt import Colt, ColtMeta
from .colt import get_private_variable

class PluginMeta(ColtMeta):
    """Meta class to keep subclasshook to handle plugins
        
       also supports Colts question routines
    """

    def __init__(cls, name, bases, clsdict):
        # 
        cls.__store_subclass(name)
        type.__init__(cls, name, bases, clsdict)

    def __store_subclass(cls, name):
        plugin_class, idx = cls.__get_storage_class()
        #
        if idx == 0:
            cls.__new_plugin_storage()
            return

        if plugin_class is not None:
            cls.__store_plugin(name, plugin_class)

    def __store_plugin(cls, name, clsplugin):
        if get_private_variable(cls, 'register_plugin') is not False:
             clsplugin.add_plugin(name, cls)

    def __get_storage_class(cls):
        mro, idx = cls.__get_idx()
        if idx != -1:
            return mro[idx], idx
        return None, None

    def __get_idx(cls):
        mro = cls.mro()
        for i, plugin_class in enumerate(mro):
            if get_private_variable(plugin_class, 'is_plugin_factory') is True:
                return mro, i
        return mro, -1

    @property
    def __plugins_storage_name(cls):
        name = get_private_variable(cls, 'plugins_storage')
        if name is None:
            name = '_plugins'
        return name

    @property
    def plugins(cls):
        """Return dict of the stored plugins, if not defined, return empty dict"""
        return getattr(cls, cls.__plugins_storage_name, {})

    def __new_plugin_storage(cls):
        """create new plugin storage"""
        setattr(cls, cls.__plugins_storage_name, {})


class PluginBase(Colt, metaclass=PluginMeta):
    """Base class"""

    __plugins_storage = '_plugins'
    __is_plugin_factory = False
    __register_plugin = False

    @classmethod    
    def add_plugin(cls, name, clsobj):
        cls.plugins[name] = clsobj
