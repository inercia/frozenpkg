

import os
import sys
import shutil
import tempfile
import glob
import fnmatch
import subprocess

from frozen import Frozen

import logging
logger = logging.getLogger(__name__)




RPM_SPEC_TEMPLATE = """

# empty lines

%define _topdir         @TOP_DIR@
%define _name           @PKG_NAME@

%define _rpmtopdir      @TOP_DIR@/%{_name}
%define _sourcedir      @TOP_DIR@/SOURCES
%define _specdir        @TOP_DIR@/SPECS
%define _rpmdir         @TOP_DIR@/RPMS
%define _srcrpmdir      @TOP_DIR@/SRPMS

# define _rpmfilename   SOMEFILENAME
# define _arch          SOMEARCH
# define _cpu           SOMECPU

%define _unpackaged_files_terminate_build       0
%define __prelink_undo_cmd                      /bin/true

Name:                 @PKG_NAME@
Version:              @PKG_VERSION@
Release:              @PKG_RELEASE@
Summary:              @PKG_NAME@
URL:                  @PKG_URL@
License:              @PKG_LICENSE@
Vendor:               @PKG_VENDOR@
Packager:             @PKG_PACKAGER@
Group:                @PKG_GROUP@
AutoReqProv:          @PKG_AUTODEPS@

@ADDITIONAL_OPS@

%description

The @PKG_NAME@ package.
@PKG_LICENSE@

@SCRIPTS@

%files

%defattr(-, nobody, nobody, 0755)

@PKG_PREFIX@

# empty lines
"""

#: directories needed in the rpm build top directory
RPM_BUILD_DIRS = [
    "BUILDROOT",
    "RPMS",
    "SOURCES",
    "SPECS",
    "SRPMS"
]

###############################################################################

class FrozenRPM(Frozen):

    def install (self):
        """
        Create a RPM
        """

        super(FrozenRPM, self).install()

        self._create_rpm_dirs()

        # replace the variables in the "spec" template
        rpmspec = RPM_SPEC_TEMPLATE
        rpmspec = rpmspec.replace("@TOP_DIR@", self.rpmbuild_dir)
        rpmspec = rpmspec.replace("@PKG_NAME@", self.pkg_name)
        rpmspec = rpmspec.replace("@PKG_VENDOR@", self.pkg_vendor)
        rpmspec = rpmspec.replace("@PKG_VERSION@", self.pkg_version)
        rpmspec = rpmspec.replace("@PKG_RELEASE@", self.pkg_release)
        rpmspec = rpmspec.replace("@PKG_PACKAGER@", self.pkg_packager)
        rpmspec = rpmspec.replace("@PKG_URL@", self.pkg_url)
        rpmspec = rpmspec.replace("@PKG_LICENSE@", self.pkg_license)
        rpmspec = rpmspec.replace("@PKG_GROUP@", self.pkg_group)
        rpmspec = rpmspec.replace("@PKG_AUTODEPS@", self.pkg_autodeps)
        rpmspec = rpmspec.replace("@PKG_PREFIX@", self.pkg_prefix)
        rpmspec = rpmspec.replace("@BUILD_ROOT@", self.buildroot)

        additional_ops = []
        if self.options.has_key('pkg-deps'):
            additional_ops = additional_ops + ["Requires: " + self.options['pkg-deps']]
        rpmspec = rpmspec.replace("@ADDITIONAL_OPS@", "\n".join(additional_ops))

        # determine if we must run any pre/post commands
        scripts = ""
        pre_cmds = self.options.get('pkg-pre-install', None)
        if pre_cmds:
            scripts += "%pre\n" + pre_cmds.strip() + "\n\n"

        post_cmds = self.options.get('pkg-post-install', None)
        if post_cmds:
            scripts += "%post\n" + post_cmds.strip() + "\n\n"

        rpmspec = rpmspec.replace("@SCRIPTS@", scripts)

        ## save the spec file
        spec_filename = os.path.abspath(os.path.join(self.buildroot, self.pkg_name) + ".spec")
        logger.debug('Using spec file %s' % (spec_filename))
        spec_file = None
        try:
            spec_file = open(spec_filename, "w")
            spec_file.write(rpmspec)
            spec_file.flush()
        except Exception, e:
            return []

        if spec_file:
            spec_file.close()

        self._copy_eggs()
        self._copy_outputs()
        self._create_extra_dirs()
        self._copy_extra_files()
        self._extra_cleanups()
        self._prepare_venv()

        # create a tar file at SOURCES/.
        # we can pass a tar file to rpmbuild, so it is easier as we may need
        # a "tar" anyway.
        # the spec file should be inside the tar, at the top level...
        tar_filename = os.path.join(self.rpmbuild_dir, "SOURCES", self.pkg_name + ".tar")
        tar_filename = self._create_tar(tar_filename)

        # launch rpmbuild
        command = [
            "rpmbuild",
            "--buildroot", self.buildroot,
            "--define",
            "_topdir %s" % self.rpmbuild_dir,
            "-ta", tar_filename,
        ]

        logger.info('Launching "%s".' % ' '.join(command))
        job = subprocess.Popen(command, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
        stdout, _ = job.communicate()

        if job.returncode != 0:
            logger.critical('could not build the RPM.')
            print stdout
            return []

        # now try to find the RPMs we have built
        result_rpms = []
        for arch_dir in os.listdir(os.path.join(self.rpmbuild_dir, "RPMS")):
            full_arch_dir = os.path.abspath(os.path.join(self.rpmbuild_dir, "RPMS", arch_dir))
            if os.path.isdir(full_arch_dir):
                for rpm_file in os.listdir(full_arch_dir):
                    if fnmatch.fnmatch(rpm_file, "*.rpm"):
                        full_rpm_file = os.path.abspath(os.path.join(full_arch_dir, rpm_file))

                        shutil.copy(full_rpm_file, self.buildout['buildout']['directory'])

                        logger.debug('Built %s' % (rpm_file))
                        result_rpms = result_rpms + [rpm_file]

        if not self.debug:
            shutil.rmtree(self.rpmbuild_dir)

        return result_rpms


    def _create_rpm_dirs(self):
        """
        Create all the top dirs
        """
        for p in RPM_BUILD_DIRS:
            full_p = os.path.join(self.rpmbuild_dir, p)
            if not os.path.exists(full_p):
                try:
                    os.makedirs(full_p)
                except:
                    logger.critical('ERROR: could not create directory "%s"' % full_p)
                    shutil.rmtree(self.rpmbuild_dir, ignore_errors = True)
                    raise


    def update (self):
        pass
