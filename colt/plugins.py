from .colt import Colt, ColtMeta
from .colt import add_defaults_to_dict, delete_inherited_keys


def plugin_meta_setup(clsdict):
    plugin_defaults = { 
            '_register_plugin': True,
            '_is_plugin_factory': False,
            '_is_plugin_specialisation': False,
            '_plugins_storage': 'inherited'
    }

    add_defaults_to_dict(clsdict, plugin_defaults)
    delete_inherited_keys(['_plugins_storage'], clsdict)
             

class PluginMeta(ColtMeta):
    """Meta class to keep subclasshooks to handle plugins in a very simple manner
       (It also supports Colts question routines)
    """

    def __new__(cls, name, bases, clsdict):
        plugin_meta_setup(clsdict)
        return ColtMeta.__new__(cls, name, bases, clsdict)

    def __init__(cls, name, bases, clsdict):
        # 
        cls.__store_subclass(name)
        cls._plugin_storage = cls.__plugins_storage_name
        type.__init__(cls, name, bases, clsdict)

    def __store_subclass(cls, name):
        """main routine to store the current class, that has been already created with __new__,
           in one of the `plugin_storage_classes` this class inherites from

           Args:
                cls (object): Current Class
                name (str): Name of the class

        """
        plugin_storage_classes, idx = cls.__get_storage_classes()
        # case current class is a storage class!
        if idx == 0:
            cls.__new_plugin_storage()
            return
        # store hook for current class in all selected plugin_storage classes
        cls.__store_plugin(name, plugin_storage_classes)

    def __store_plugin(cls, name, plugin_storage_classes):
        """store plugin in the plugin_storage_classes it inherits from"""
        if getattr(cls, '_register_plugin', True) is False:
            return
        # store plugin in all stoarge classes
        for storage_class in plugin_storage_classes:
            storage_class.add_plugin(name, cls)

    def __get_storage_classes(cls):
        """return all relevant storage classes"""
        mro = cls.mro()
        # 
        storage_classes = []
        idx = []
        #
        for i, plugin_class in enumerate(mro):
            if getattr(plugin_class, '_is_plugin_factory', False) is True:
                storage_classes.append(plugin_class)
                idx.append(i)
                # stop if it is just a plugin specialisation
                if getattr(plugin_class, '_is_plugin_specialisation', False) is not True: 
                    break

        if idx == []:
            idx = -1
        else:
            idx = idx[0]
        return storage_classes, idx

    @property
    def __plugins_storage_name(cls):
        return getattr(cls, '_plugins_storage', '_plugins')

    @property
    def plugins(cls):
        """Return dict of the stored plugins, if not defined, return empty dict"""
        return getattr(cls, cls.__plugins_storage_name, {})

    def __new_plugin_storage(cls):
        """create new plugin storage"""
        setattr(cls, cls.__plugins_storage_name, {})


class PluginBase(Colt, metaclass=PluginMeta):
    """Base class for the construction of PluginFactories"""

    _plugins_storage = '_plugins'
    _is_plugin_factory = False
    _register_plugin = False
    _is_plugin_specialisation = False

    @classmethod    
    def add_plugin(cls, name, clsobj):
        """Register a plugin"""
        cls.plugins[name] = clsobj