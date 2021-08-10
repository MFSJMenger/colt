"""Implements ways to lazy load modules"""
import inspect
from importlib import import_module
from types import ModuleType


class LazyImporter:

    def __init__(self, data, *, callers_globals=None):
        if callers_globals is None:
            # in case caller globals is not defined get it from the spec
            callers_globals = inspect.stack()[1][0].f_globals
        self._callers_gloabals = callers_globals
        # get the package name
        self._package = callers_globals['__package__']
        #
        if not isinstance(data, dict):
            raise ValueError("modules need to be a dict")
        self._data = data

    def load(self):
        for local_name, name in self._data.items():
            if name is None:
                name = local_name
            self._load_module(name, local_name)

    def _load_module(self, name, local_name):
        package = None
        if name.startswith('.'):
            package = self._package
        # Import the target
        module = import_module(name, package=package)
        # place it into the parents global scope
        self._callers_gloabals[local_name] = module


class LazyImport(ModuleType):
    """Basic LazyImport module
    loads module upon attribute access into the global scope of the caller
    """

    def __init__(self, name, *, local_name=None, callers_globals=None):
        """Initialize an lazyloader that loads the module upon attribute access

        Parameters
        ----------

        name, str:
            name of the module to be imported

        local_name, str, optional:
            name of the module in the caller's global scope

        callers_globals, dict:
            the globals of the caller, if None it gets evaluated directly
            using `inspect`
        """
        super().__init__(name)
        #
        if callers_globals is None:
            # in case caller globals is not defined get it from the spec
            callers_globals = inspect.stack()[1][0].f_globals
        if local_name is None:
            if name.startswith('.'):
                raise ValueError(f"For relative import '{name}' define local_name")
            local_name = name
        # everything should be local!
        self._local_name = local_name
        self._callers_gloabals = callers_globals

    def __repr__(self):
        return f"LazyImport('{self.__name__}')"

    def _load(self):
        """Load the module and insert it into the caller's globals."""
        if self.__name__.startswith('.'):
            package = self._callers_gloabals['__package__']
        else:
            package = None
        # Import the target
        module = import_module(self.__name__, package=package)
        # place it into the parents global scope
        self._callers_gloabals[self._local_name] = module
        # update the dict, in case someone defines an alias
        self.__dict__.update(module.__dict__)
        return module

    def __getattr__(self, item):
        """load module up-on unknown attribute call"""
        module = self._load()
        return getattr(module, item)

    def __dir__(self):
        """load module up-on dictionary call"""
        module = self._load()
        return dir(module)


class LazyImportCreator:
    """Helper to create multiple lazy importers at once"""

    def __init__(self, callers_globals=None):
        """Create a LazyImportCreater to generate many LazyImport from
        a single globals

        Parameters
        ----------

        callers_globals, dict:
            the globals of the caller, if None it gets evaluated directly
            using `inspect`
        """
        if callers_globals is None:
            # get globals of the caller
            callers_globals = inspect.stack()[1][0].f_globals
        self._callers_gloabals = callers_globals

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        pass

    def lazy_import_as(self, name, local_name):
        """import name as local_name

        Parameters
        ----------

        name, str:
            name of the module to be imported

        local_name, str:
            name of the module in the callers global namespace

        Returns
        -------
        LazyImport for the module
        """
        return LazyImport(name, local_name=local_name, callers_globals=self._callers_gloabals)

    def lazy_import(self, name):
        """import name

        Parameters
        ----------

        name, str:
            name of the module to be imported

        Returns
        -------
        LazyImport for the module
        """
        return LazyImport(name, callers_globals=self._callers_gloabals)
