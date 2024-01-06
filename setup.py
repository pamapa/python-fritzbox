import setuptools

setuptools.setup(name='python-fritzbox',
  version='0.4',
  description='Automate the Fritz!Box with python',
  url='https://github.com/pamapa/python-fritzbox',
  author='Patrick Ammann',
  author_email='pammann@gmx.net',
  license='GNU',
  packages=['fritzbox'],
  zip_safe=False,
  scripts=[
    'fritzboxphonebook.py',
    'fritzboxktipp.py',
  ]
)
