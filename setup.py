import os
import trello_watchman.__about__ as a
from setuptools import setup


with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'README.md')) as f:
    README = f.read()

setup(
    name='trello-watchman',
    version=a.__version__,
    url=a.__uri__,
    license=a.__license__,
    classifiers=[
        'Intended Audience :: Information Technology',
        'Topic :: Security',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    author=a.__author__,
    author_email=a.__email__,
    long_description=README,
    long_description_content_type='text/markdown',
    description=a.__summary__,
    install_requires=[
        'requests',
        'PyYAML',
        'simplejson'
    ],
    keywords='audit trello trello-watchman watchman blue-team red-team threat-hunting',
    packages=['trello_watchman'],
    include_package_data=True,
    package_data={
            "": ["*.yml", "*.yaml"],
        },
    entry_points={
        'console_scripts': ['trello-watchman=trello_watchman:main']
    }
)
