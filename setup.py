#!/usr/bin/env python

from setuptools import setup, find_packages
import os

def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()


long_description = (
    read('README.txt')
    + '\n' +
    'Contributors\n'
    '************\n'
    + '\n' +
    read('CONTRIBUTORS.txt')
    + '\n'
)


setup(
    name             = "as.recipe.frozenpkg",
    description      = "ZC Buildout recipe for freezing buildouts in RPM's, tar.gz's, etc",
    long_description = long_description,
    version          = '0.1.1',

    # Get more strings from http://www.python.org/pypi?%3Aaction=list_classifiers
    classifiers = [
        'Framework :: Buildout',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        ],
    keywords = 'buildout recipe',
    author   = 'Alvaro Saurin',
    author_email = 'name dot surname at gmail.com',

    packages             = find_packages(exclude=['ez_setup']),
    namespace_packages   = ['as', 'as.recipe'],
    include_package_data = True,
    install_requires     = [
        'setuptools',
        'zc.recipe.egg',
        'zc.buildout'
        # -*- Extra requirements: -*-
    ],
    license  = 'GPL',
    zip_safe = False,
    entry_points = {
        'zc.buildout': [
            'default = as.recipe.frozenpkg:FrozenRPM',
            'rpm     = as.recipe.frozenpkg:FrozenRPM'
        ]
    },
)


