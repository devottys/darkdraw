#!/usr/bin/env python3

from setuptools import setup
from pathlib import Path

def requirements():
    return Path('requirements.txt').read_text().splitlines()

__version__='0.3'

setup(name='darkdraw',
      version=__version__,
      description='art and animation for the terminal, in the terminal',
      author='devottys',
      python_requires='>=3.7',
      url='bluebird.sh',
      py_modules=['darkdraw'],
      install_requires=requirements(),
      packages=['darkdraw'],
      include_package_data=True,
      entry_points={'visidata.plugins': 'darkdraw=darkdraw'},
      package_data={'darkdraw': ['darkdraw/ansi.html']},
)
