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

        sys-dir
           The system libraries directory. Default: the lib directory in the virtualenv (if present)

        scripts
            The scripts that will be copied to the package. Tese scripts will have their paths relocated to the installation prefix.

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

        eggs           = ${main:eggs}

        python-version = 2.6
        sys-dir        = /usr/lib/python2.6
        scripts        =
                         testapp

        extra-copies   =
                         /usr/local/lib/mylib.so      ->   lib/
                         /usr/local/lib/myextras*.so  ->   lib/

        pre-install    =
                 echo "Installing at ${buildout:pkg-prefix}"

        post-install   =
                 echo "Installed at ${buildout:pkg-prefix}"
                         
        debug          = yes

