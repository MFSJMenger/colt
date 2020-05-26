import importlib.util
import os
import sys


class AddFolderToPath:

    __slots__ = ('folder', 'idx')

    def __init__(self, folder):
        if folder in ('', None): 
            folder = '.'
        self.folder = folder
        self.idx = None

    def __enter__(self, *args, **kwargs):
        sys.path.append(self.folder)

    def __exit__(self, *args, **kwargs):
        try:
            sys.path.remove(self.folder)
        except:
            pass



class PluginLoader:
    """Basic class to load plugins from a folder"""
    __slots__ = ()

    def __init__(self, folder):
        if os.path.isdir(folder):
            self.load_folder(folder)

    def import_module(self, path):
        """import a module"""
        path, name = os.path.split(path)
        with AddFolderToPath(path):
            importlib.import_module(name)

    def load_folder(self, folder):
        files = tuple(os.listdir(folder))
        #
        if '__init__.py' in files:
            return self.import_module(folder)
        #
        files = tuple(os.path.join(folder, filename) for filename in files)
        #
        for filename in files:
            if filename.endswith('.py'):
                self.load_file(filename)
            elif os.path.isdir(filename):
                self.load_folder(filename)

    def load_file(self, filepath):
        _, name = os.path.split(filepath)
        spec = importlib.util.spec_from_file_location(name[:-3], filepath)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except:
            pass
        return module
