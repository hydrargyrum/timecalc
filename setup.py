#!/usr/bin/env python3
# this project is licensed under the WTFPLv2, see COPYING.txt for details

import glob
import os

from setuptools import setup, find_packages


with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as fd:
    README = fd.read().strip()


setup(
    name='timecalc',
    version='0.9.0',

    description='timecalc - a date/time/duration calculator',
    long_description=README,
    url='https://github.com/hydrargyrum/timecalc',
    author='Hg',
    license='WTFPLv2',
    classifiers=[
        'Development Status :: 4 - Beta',

        'Environment :: Console',

        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',

        'License :: Public Domain',

        'Topic :: Utilities',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='date time datetime duration calculator repl evaluate compute',

    packages=find_packages(),
    scripts=['timecalc'],
    data_files=[
        ('share/doc/timecalc', ['README.rst']),
    ],

    install_requires=['python-dateutil'],
)
