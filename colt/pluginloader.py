import importlib.util
import os
import re
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
    __slots__ = ('ignore')

    def __init__(self, folder, config='config.ini'):
        self.ignore = lambda x: True
        if os.path.isdir(folder):
            self.ignore = IgnoreConfig(folder, config=config)
            self._load_folder(folder)

    def _import_module(self, path):
        """import a module"""
        path, name = os.path.split(path)
        with AddFolderToPath(path):
            importlib.import_module(name)

    def _load_folder(self, folder):
        if self.ignore(folder):
            return
        #
        files = tuple(os.listdir(folder))
        #
        if '__init__.py' in files:
            return self._import_module(folder)
        #
        files = tuple(os.path.join(folder, filename) for filename in files)
        #
        for filename in files:
            if self.ignore(filename):
                continue
            if filename.endswith('.py'):
                self._load_file(filename)
            elif os.path.isdir(filename):
                self._load_folder(filename)

    def _load_file(self, filepath):
        _, name = os.path.split(filepath)
        spec = importlib.util.spec_from_file_location(name[:-3], filepath)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except:
            pass
        return module


def get_patter(pattern):
    parent, path = os.path.split(pattern)
    paths = [path]
    while parent != '':
        parent, path = os.path.split(parent)
        paths.append(path)

    pattern = ''
    paths.reverse()
    
    for path in paths:
        if '*' in path:
            path = path.replace('*', r'[\w\d-]*')
        pattern = os.path.join(pattern, path)

    return pattern


class PathMatcher:

    def __init__(self, pattern):
        self.pattern = re.compile(get_patter(pattern))

    def match(self, path):
        return self.pattern.match(path) is not None


class IgnoreConfig:

    def __init__(self, folder, config='config.ini'):
        if folder in ('.', ''):
            self.nignore = 0
        else:
            self.nignore = len(folder) + 1
        #
        self.folder = folder
        self.matchers = [PathMatcher(pattern) for pattern in self._setup(os.path.join(folder, config))]

    def _setup(self, config):
        return self._load_config(config)

    def _load_config(self, config):
        if not os.path.isfile(config):
            return []
        with open(config, 'r') as f:
            return sorted([line.strip() for line in f if not (line.strip().startswith('#') or line.strip() == '')])

    def __call__(self, filename):
        filename = filename[self.nignore:]
        for matcher in self.matchers:
            if matcher.match(filename) is True:
                return True
        return False
