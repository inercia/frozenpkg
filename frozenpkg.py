

import logging, os, zc.buildout
import shutil
import tempfile
import glob
import subprocess

class FrozenRPM:
    """
    Parameters:

    pkg-name

    install-prefix
    eggs
    scripts
    """

    def __init__(self, buildout, name, options):
        self.name, self.options = name, options
        self.buildout = buildout

    def _log(self, msg):
        logging.getLogger(self.name).info(msg)

    def install(self):
        pkg_name    = self.options['pkg-name']
        pkg_version = self.options['pkg-version']

        buildroot   = os.path.normpath(tempfile.mkdtemp() + "/" + self.options['install-prefix'])

        # 1. copy the python bins

        bins_sdir   = self.buildout['buildout']['bin-directory']
        bins_ddir   = os.path.normpath(buildroot + "/bin")

        self._log('Copying binary python')
        try:
            os.makedirs(bins_ddir)
        except Exception,e :
            pass
        shutil.copy(bins_sdir + "/python", bins_ddir)

        # 2. copy the libs


        # 3. copy the eggs

        eggs_sdir = self.buildout['buildout']['eggs-directory']
        eggs_ddir = os.path.normpath(buildroot + "/lib/python2.6/site-packages/")

        for egg_name in self.options['eggs']:
            for egg_path in glob.glob(eggs_sdir + "/" + egg_name + "*.egg"):
                self._log('Copying egg %s' % os.path.basename(egg_path))
                egg_dest = os.path.normpath(eggs_ddir + "/" + os.path.basename(egg_path))
                shutil.copytree(egg_path, egg_dest)


        rpmspec = """
            %define installdir
            %define buildoutcfg   buildout.cfg
            %define buildroot     @BUILDROOT@

            Name:                 @PKGNAME@
            Version:              1.0
            Release:              0
            Summary:              urldownloader
            URL:                  http://www.tid.es
            License:              (c) 2010 Telefonica I+D
            Vendor:               Telefonica I+D
            Packager:             Telefonica I+D
            Group:                Applications/Networking
            Buildroot:            @BUILDROOT@

            %description

            %{summary}

            %prep

            %build

            %install

            %files
            %defattr(-, nobody, nobody, 0755)
            %{installdir}

            %clean
            """
        rpmspec.replace("@PKGNAME@", pkg_name)
        rpmspec.replace("@INSTALLPREFIX@", install-prefix)
        rpmspec.replace("@BUILDROOT@", buildroot)

        with tempfile.mktemp() as f:
            f.write(rpmspec)



    def update(self):
        pass
