#!/usr/bin/env python2.6

from setuptools import setup, find_packages
import os


__VERSION__ = '0.2.20'




setup(
    name                = "as.recipe.frozenpkg",
    description         = "ZC Buildout recipe for freezing buildouts in RPM's, tar.gz's, etc",
    long_description    = open('README.md', 'rt').read(),
    version             = __VERSION__,

    # Get more strings from http://www.python.org/pypi?%3Aaction=list_classifiers
    classifiers = [
        'Framework :: Buildout',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        ],

    keywords        = 'buildout recipe',
    author          = 'Alvaro Saurin',
    author_email    = 'name dot surname at gmail.com',

    packages        = find_packages(exclude = ['ez_setup']),

    namespace_packages = ['as',
                          'as.recipe'],

    include_package_data = True,
    install_requires = [
        'distribute',
        'virtualenv',
    ],

    license             = 'GPL',
    zip_safe            = False,

    entry_points        = {
        'zc.buildout': [
            'default = as.recipe.frozenpkg.frozenrpm:FrozenRPM',
            'rpm     = as.recipe.frozenpkg.frozenrpm:FrozenRPM',
            'tgz     = as.recipe.frozenpkg.frozentgz:FrozenTgz'
        ]
    },
)

