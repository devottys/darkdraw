#!/usr/bin/env python3

from setuptools import setup

__version__='0.3'

setup(name='darkdraw',
      version=__version__,
      description='art and animation for the terminal, in the terminal',
      author='devottys',
      python_requires='>=3.7',
      url='bluebird.sh',
      py_modules=['darkdraw'],
      install_requires=['visidata>=2.9', 'wcwidth', 'requests'],
      packages=['darkdraw'],
      include_package_data=True,
      package_data={'darkdraw': ['darkdraw/ansi.html']},
)
