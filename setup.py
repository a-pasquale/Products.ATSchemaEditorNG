from setuptools import setup, find_packages
import os

version = '0.6'

setup(name='Products.ATSchemaEditorNG',
      version=version,
      description="ATSchemaEditorNG is a framework to provide flexible schema editing for AT content-types",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from http://www.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='plone archetypes schema',
      author='Simon Pamies',
      author_email='s.pamies@banality.de',
      url='http://pypi.python.org/pypi/Products.ATSchemaEditorNG',
      license='LGPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['Products'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          # -*- Extra requirements: -*-
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
