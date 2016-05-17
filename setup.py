import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()
VERSION = open(os.path.join(here, 'VERSION')).read()


requires = [
    'WebTest',
    'WSGIProxy2',
    'ramlfications==0.1.8',
    'jsonschema',
    'six',
    'pytest',
    'simplejson',
    'inflection',
    'wrapt',
]


setup(name='ra',
      version=VERSION,
      description='Test RAML API definition',
      long_description=README,
      classifiers=[
          "Programming Language :: Python",
          "Programming Language :: Python :: 2",
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 3.4",
          "Programming Language :: Python :: 3.5",
          "Framework :: Pyramid",
          "Topic :: Internet :: WWW/HTTP",
          "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
      ],
      author='Ramses',
      author_email='hello@ramses.tech',
      url='https://github.com/ramses-tech/ra',
      keywords='web raml',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=requires,
      test_suite="ra",
      entry_points = {
          'pytest11': [
              'ra = ra.plugins.pytest_'
          ]
      })
