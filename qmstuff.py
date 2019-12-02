from colt.plugins import PluginMeta
from colt.plugins import add_defaults_to_dict



def reader_meta_setup(clsdict):
    """Manipulation of clsdict for reading info"""
    plugin_defaults = {
            'readers': {},
    }
    add_defaults_to_dict(clsdict, plugin_defaults)


class ReaderMeta(PluginMeta):

    def __new__(cls, name, bases, clsdict):
        reader_meta_setup(clsdict)
        if '_reader_parent' in clsdict:
            raise KeyError("parent cannot be in cls ReaderMeta")
        parent = None
        for base in bases:
            if issubclass(base, BaseReader):
                parent = base
        clsdict['_reader_parent'] = parent 
        return PluginMeta.__new__(cls, name, bases, clsdict)




class BaseReader(metaclass=ReaderMeta):
    """Only linear responds!"""

    readers = {'e': 'base energy', 'g': 'base gradient'}

    @classmethod
    def get_reader(cls, name):
        if name in cls.readers:
            return cls.readers[name]
        if cls._reader_parent is None:
            raise KeyError(f"Reader {name} not known")
        return cls._reader_parent.get_reader(name)

    @classmethod
    def register_reader(cls, name, reader):
        cls.readers[name] = reader


class Reader(BaseReader):
    readers = {'dm': 'reader dm'}



print(Reader.get_reader('e'))
print(Reader.register_reader('e', 'hi'))
print(Reader.get_reader('e'))


