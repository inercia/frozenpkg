

import logging
import os
import sys
import shutil
import tempfile

import zc.buildout
import glob
import fnmatch

import subprocess

from frozen import Frozen



class FrozenTgz(Frozen):
    # def __init__(self, buildout, name, options):
    #     super(FrozenTgz, self).__init__(buildout, name, options)

    def install(self):
        """
        Create a RPM
        """
        additional_ops = []
        result_tgzs = []
        
        top_tgzbuild_dir = os.path.abspath(tempfile.mkdtemp(suffix = '', prefix = 'tgzfreeze-'))

        pkg_name = self.options['pkg-name']
        pkg_version = self.options.get('pkg-version', '0.1')

        self.install_prefix = self.options.get('install-prefix', os.path.join('opt', pkg_name))

        buildroot_topdir = os.path.abspath(top_tgzbuild_dir + "/PKG/" + pkg_name)
        buildroot_projdir = os.path.abspath(buildroot_topdir + "/" + self.install_prefix)
        buildroot_tgzs = os.path.abspath(top_tgzbuild_dir + "/TGZ")

        # get the python binary, the version and the library
        self._checkPython()
        self._getPythonInfo(buildroot_projdir)

        replacements = []

        # copy all the files we need
        self._log("Build root = %s" % buildroot_topdir)
        replacements = replacements + self._copyPythonDist(buildroot_topdir, self.install_prefix)
        replacements = replacements + self._copyNeededEggs(buildroot_topdir, self.install_prefix)
        replacements = replacements + self._copyExtraFiles(buildroot_topdir, self.install_prefix)

        replacements = replacements + [
            (self.buildout['buildout']['directory'], self.install_prefix)
        ]

        # fix the copied scripts, by replacing some paths by the new
        # installation paths
        self._fixScripts(replacements, buildroot_projdir)

        # create a tar file at SOURCES/.
        # we can pass a tar file to rpmbuild, so it is easier as we may need
        # a "tar" anyway.
        # the spec file should be inside the tar, at the top level...
        tarfile = os.path.join(buildroot_tgzs, pkg_name + "-" + pkg_version + ".tar")
        tgzfile = self._createTar(buildroot_topdir, tarfile, compress = True)
        b_tgzfile = os.path.basename(tgzfile)

        full_tgzfile = os.path.join(self.buildout['buildout']['directory'], b_tgzfile)
        shutil.copy(tgzfile, full_tgzfile)

        self._log('Built %s' % (full_tgzfile))
        result_tgzs = result_tgzs + [full_tgzfile]

        if not self.debug:
            shutil.rmtree(top_tgzbuild_dir)
    
        return result_tgzs

    def update(self):
        pass

