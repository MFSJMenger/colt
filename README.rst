=======================
COLT: COmmand Line Tool
=======================

Simple, extensible tool to create out of the box input files and commandline
interfaces for Python, that are type validated.
For the input file the `ini` file-format is used around Python's configparser_.


|PyPI version fury.io|
|PyPI download month|  
|PyPI license|
|PyPI implementation|

.. |PyPI implementation| image:: https://img.shields.io/pypi/implementation/pycolt.svg
   :target: https://pypi.python.org/pypi/pycolt/

.. |PyPI download month| image:: https://img.shields.io/pypi/dm/pycolt.svg
   :target: https://pypi.python.org/pypi/pycolt/
  

.. |PyPI version fury.io| image:: https://badge.fury.io/py/pycolt.svg
   :target: https://pypi.python.org/pypi/pycolt/


.. |PyPI license| image:: https://img.shields.io/pypi/l/pycolt.svg
   :target: https://pypi.python.org/pypi/pycolt/

Features
--------

1. Build simple commandline interfaces using the FromCommandline-decorator

.. code:: python

   # examples/commandline_xrange.py
   from colt import from_commandline


   @from_commandline("""
   # start of the range
   xstart = :: int :: >0
   # end of the range
   xstop = :: int :: >1
   # step size
   step = 1 :: int 
   """)
   def x_range(xstart, xstop, step):
      for i in range(xstart, xstop, step):
         print(i)

   if __name__ == '__main__':
      x_range()

.. code:: python

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
