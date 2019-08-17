from setuptools import setup, find_packages
from os import path
import sys
from io import open

here = path.abspath(path.dirname(__file__))
sys.path.append(here)
import properties


# Get the long description from the README file
with open(path.join(path.dirname(here), 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='syncmanagerapi',
    version=properties.__version__,
    description='Provides Server for managing multiple synchronizations via unison, git, ...',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/Grid-LTS/syncmanager',
    author='Gerd Friemel',
    author_email='gerd.friemel@gmail.com',
    license = 'MIT',
    # For a list of valid classifiers, see https://pypi.org/classifiers/
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    keywords='git unison',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    package_data={'syncmanagerapi': ['swagger.yaml']},
    include_package_data=True,
    install_requires=['configparser','connexion','flask','flask-marshmallow','flask-sqlalchemy','flask-basicauth',
                      'gitpython','marshmallow','marshmallow-sqlalchemy', 'mysqlclient'],
    python_requires='>=3',

    extras_require={
        'dev': [
            'setuptools>=35.0.1'
            'wheel>=0.29.0'
                ],
    },

    # executes the function `main` from this package when invoked:
    entry_points={
        'console_scripts': [
            'syncmanagerapi=syncmanagerapi:main',
        ],
    }

)