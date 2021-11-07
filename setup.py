#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = []

setup_requirements = ['pytest-runner', ]

test_requirements = ['pytest>=3', ]

setup(
    author="Maximilian F.S.J. Menger",
    author_email='m.f.s.j.menger@rug.nl',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="Command Line Tool for Python",
    install_requires=requirements,
    license="Apache License v2.0",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='pycolt',
    name='pycolt',
    packages=find_packages(include=['colt', 'colt.*']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/mfsjmenger/colt',
    version='0.5.3',
    zip_safe=False,
)
