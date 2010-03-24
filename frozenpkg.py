

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
        install_prefix = self.options['install-prefix']
        pkg_name       = self.options['pkg-name']
        pkg_version    = self.options['pkg-version']
        pkg_vendor     = self.options['pkg-vendor']
        pkg_packager   = self.options['pkg-packager']
        pkg_url        = self.options['pkg-url']
        pkg_license    = self.options['pkg-license']
        pkg_group      = self.options['pkg-group']


        buildroot   = os.path.normpath(tempfile.mkdtemp() + "/" + install_prefix)

        # 1. copy the python bins

        bins_sdir   = self.buildout['buildout']['bin-directory']
        bins_ddir   = os.path.normpath(buildroot + "/bin")

        self._log('Copying binary python')
        try: os.makedirs(bins_ddir)
        except Exception: pass

        shutil.copy(bins_sdir + "/python", bins_ddir)

        # 2. copy the libs


        # 3. copy the eggs

        eggs_sdir = self.buildout['buildout']['eggs-directory']
        eggs_ddir = os.path.normpath(buildroot + "/lib/python2.6/site-packages/")

        for egg_name in self.options['eggs']:
            for egg_path in os.listdir(eggs_sdir):
                if fnmatch.fnmatch(egg_path, egg_name + "*.egg"):
                    self._log('Copying egg %s' % os.path.basename(egg_path))
                    egg_dest = os.path.normpath(eggs_ddir + "/" + os.path.basename(egg_path))
                    shutil.copytree(egg_path, egg_dest)


        rpmspec = """
            %define buildroot     @BUILDROOT@

            Name:                 @PKG_NAME@
            Version:              @PKG_VERSION@
            Release:              0
            Summary:              @PKG_NAME@
            URL:                  @PKG_URL@
            License:              @PKG_LICENSE@
            Vendor:               @PKG_VENDOR@
            Packager:             @PKG_PACKAGER@
            Group:                @PKG_GROUP@
            Buildroot:            @BUILD_ROOT@

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
        rpmspec.replace("@PKG_NAME@",        pkg_name)
        rpmspec.replace("@PKG_VENDOR@",      pkg_vendor)
        rpmspec.replace("@PKG_VERSION@",     pkg_version)
        rpmspec.replace("@PKG_PACKAGER@",    pkg_packager)
        rpmspec.replace("@PKG_URL@",         pkg_url)
        rpmspec.replace("@PKG_LICENSE@",     pkg_license)
        rpmspec.replace("@PKG_GROUP@",       pkg_group)
        rpmspec.replace("@INSTALL_PREFIX@",  install_prefix)
        rpmspec.replace("@BUIL_DROOT@",      buildroot)

        with tempfile.mktemp() as f:
            f.write(rpmspec)



    def update(self):
        pass
