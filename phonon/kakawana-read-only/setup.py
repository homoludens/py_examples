# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
import sys, os

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
NEWS = open(os.path.join(here, 'NEWS.txt')).read()


version = '0.1'

install_requires = [
    # List your project dependencies here.
    # For more details, see:
    # http://packages.python.org/distribute/setuptools.html#declaring-dependencies
    "Elixir >=0.6",
    "BeautifulSoup",
    "Keyring",
    "oauth2",
    "lxml",
]


setup(name='kakawana',
    version=version,
    description="A modern news aggregator",
    long_description=README + '\n\n' + NEWS,
    classifiers=[
      # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    ],
    keywords='rss atom qt pyqt aggregator news',
    author='Roberto Alsina',
    author_email='ralsina@netmanagers.com.ar',
    url='http://kakawana.googlecode.com',
    license='GPLv2',
    packages=find_packages('src'),
    package_dir = {'': 'src'},include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    entry_points={
        'console_scripts':
            ['kakawana=kakawana.main:main']
    }
)
