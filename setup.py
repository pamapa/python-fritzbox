import os
from setuptools import setup

setup(name='python-fritzbox',
  version='0.1',
  description='Automate the Fritz!Box with python',
  url='https://github.com/pamapa/python-fritzbox',
  author='Patrick Ammann',
  author_email='pammann@gmx.net',
  license='GNU',
  packages=['fritzbox', 'tools'],
  zip_safe=False,
  scripts=[
    os.path.join('tools', 'fritzboxutil.py'),
    os.path.join('tools', 'fritzboxktipp.py'),
  ]
)

