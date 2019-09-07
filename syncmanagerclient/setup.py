from setuptools import setup, find_packages
from os import path
from io import open

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(path.dirname(here), 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='syncmanagerclient',
    version='0.1.0',
    description='For Managing multiple synchronizations via unison, git, ...',
    long_description=long_description,
    # This field corresponds to the "Description-Content-Type" metadata field:
    # https://packaging.python.org/specifications/core-metadata/#description-content-type-optional
    long_description_content_type='text/markdown',
    url='https://github.com/Grid-LTS/syncmanager',
    author='Gerd Friemel',
    author_email='gerd.friemel@gmail.com',
    license='MIT',
    # For a list of valid classifiers, see https://pypi.org/classifiers/
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    keywords='git unison',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=['gitpython', 'pathlib', 'configparser', 'requests'],
    python_requires='>=3',

    extras_require={
        'dev': [
            'setuptools>=35.0.1'
            'wheel>=0.29.0'
        ],
        # 'test': ['coverage'],
    },

    #  package_data={
    #  },

    # executes the function `main` from this package when invoked:
    entry_points={
        'console_scripts': [
            'syncmanager=syncmanagerclient:main',
            'syncmanager-legacy=syncmanagerclient:legacy',
        ],
    }

)
