#!/usr/bin/env python2.6

from setuptools import setup, find_packages
import os

#def read(*rnames):
#    return open(os.path.join(os.path.dirname(__file__), *rnames), "r").read()


long_description = """
Introduction
============

This recipe enables you to freeze your buildout in a RPM, tgz's, etc.
You can specify the package details, the installation prefix, and the eggs and
scripts that must be copied to the package.

Only RPM packing is currently implemented.

This recipe is EXPERIMENTAL and quite unstable, so use at your own risk...

.. contents::

- PyPI page: http://pypi.python.org/pypi?:action=display&name=as.recipe.frozenpkg

Options
=======

pkg-name
    Mandatory. The package name.

pkg-version
    The package version.

pkg-vendor
    The package vendor.

pkg-packager
    The packager.

pkg-url
    The package URL.

pkg-license
    The license.

pkg-deps
    Package dependencies. It must be a space-separated list of RPM packages.

install-prefix
    The installation prefix. Default: /opt/pkg-name

eggs
    The list of eggs that must be copied to the RPM package.

python-version
    The python version that will be copied to the package.

sys-python
    The python binary that we should copy to the package. Default: the python in the virtualenv.

sys-lib
   The system libraries directory. Default: the library of the sys-python when provided, or the lib directory in the virtualenv otherwise.

scripts
    The scripts from the bin directory that will be copied to the package. These scripts will have their paths relocated to the installation prefix.

extra-copies
    Any additional extra copies. They must be specified as "orig -> dest", where orig can be any valid glob expression, and dest must be a path relative to install-prefix.

pre-install
    Shell commands to run before installing the RPM
    
post-install
    Shell commands to run after installing the RPM
       

Example
=======

        [rpm]
        recipe         = as.recipe.frozenpkg:rpm
        pkg-name       = testapp
        pkg-version    = 1.0
        pkg-vendor     = The Vendor
        pkg-packager   = My Company
        pkg-url        = http://www.mycomp.com
        pkg-license    = GPL
        pkg-deps       = libevent

        install-prefix = /opt/testapp

        eggs           = ${buildout:eggs}

        sys-python     = /usr/lib/python2.6

        scripts        =
                         testapp

        extra-copies   =
                         /usr/lib/libpython*          ->   lib/
                         /usr/local/lib/mylib.so      ->   lib/
                         /usr/local/lib/myextras*.so  ->   lib/
        pre-install    =
                         echo "Installing at ${buildout:pkg-prefix}"
                         
        post-install   =
                         echo "Installed at ${buildout:pkg-prefix}"
                                                  
        debug          = yes


Known Bugs
==========

- You must comment out the prelink_undo_cmd at /etc/rpm/macros.prelink, or the RPM generated will fail to install.

"""



setup(
    name = "as.recipe.frozenpkg",
    description = "ZC Buildout recipe for freezing buildouts in RPM's, tar.gz's, etc",
    long_description = long_description,
    version = '0.2.13',

    # Get more strings from http://www.python.org/pypi?%3Aaction=list_classifiers
    classifiers = [
        'Framework :: Buildout',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        ],
    keywords = 'buildout recipe',
    author = 'Alvaro Saurin',
    author_email = 'name dot surname at gmail.com',

    packages = find_packages(exclude = ['ez_setup']),
    namespace_packages = ['as', 'as.recipe'],
    include_package_data = True,
    install_requires = [
        'setuptools',
        'zc.buildout',
        'zc.recipe.egg'
        # -*- Extra requirements: -*-
    ],

    license = 'GPL',
    zip_safe = False,
    entry_points = {
        'zc.buildout': [
            'default = as.recipe.frozenpkg:FrozenRPM',

            'rpm     = as.recipe.frozenpkg.frozenrpm:FrozenRPM',
            'tgz     = as.recipe.frozenpkg.frozentgz:FrozenTgz'
        ]
    },
)
