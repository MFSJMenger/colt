from .colt import Colt, ColtMeta

def _get_private_variable_name(clsobj, name):
    return f'_{clsobj.__name__}__{name}'

def get_private_variable(clsobj, name):
    return getattr(clsobj, _get_private_variable_name(clsobj, name), None)


# def plugin_meta_setup(clsdict):


class PluginMeta(ColtMeta):
    """Meta class to keep subclasshooks to handle plugins in a very simple manner
       (It also supports Colts question routines)
    """

 #   def __new__(cls, name, bases, clsdict):
 #       plugin_meta_setup(clsdict)
 #       return ColtMeta.__new__(cls, name, bases, clsdict)

    def __init__(cls, name, bases, clsdict):
        # 
        cls.__store_subclass(name)
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
        if get_private_variable(cls, 'register_plugin') is not False:
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
            if get_private_variable(plugin_class, 'is_plugin_factory') is True:
                storage_classes.append(plugin_class)
                idx.append(i)
                # stop if it is just a plugin specialisation
                if get_private_variable(plugin_class, 'is_plugin_specialisation') is not True: 
                    break
        if idx == []:
            idx = -1
        else:
            idx = idx[0]
        return storage_classes, idx

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
    """Base class for the construction of PluginFactories"""

    __plugins_storage = '_plugins'
    __is_plugin_factory = False
    __register_plugin = False
    __is_plugin_specialisation = False

    @classmethod    
    def add_plugin(cls, name, clsobj):
        """Register a plugin"""
        cls.plugins[name] = clsobj
