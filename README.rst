=======================
COLT: COmmand Line Tool
=======================

Simple, extensible tool to create out of the box input files and commandline
interfaces for Python, that are type validated.
For the input file the `ini` file-format is used around Python's configparser_.


* Free software: Apache License 2.0


Features
--------

1. Build simple commandline interfaces using the FromCommandline-decorator

.. literalinclude:: examples/commandline_xrange.py
   :linenos:

::

   usage: commandline_xrange.py [-h] [-step step] xstart xstop

   positional arguments:
      xstart      int, Range(>0)
                  start of the range
      xstop       int, Range(>1)
                  end of the range

   optional arguments:
      -h, --help  show this help message and exit
      -step step  int,
                  step size


Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
.. _configparser: https://docs.python.org/3/library/configparser.html
