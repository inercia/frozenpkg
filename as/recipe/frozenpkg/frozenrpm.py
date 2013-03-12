

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
Release:              0
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

@INSTALL_PREFIX@

# empty lines
"""


###############################################################################

class FrozenRPM(Frozen):


    def _create_dirs(self, top_rpmbuild_dir):
        """
        Create all the top dirs
        """
        try:
            os.mkdir(os.path.abspath(os.path.join(top_rpmbuild_dir, "BUILDROOT")))
            os.mkdir(os.path.abspath(os.path.join(top_rpmbuild_dir, "RPMS")))
            os.mkdir(os.path.abspath(os.path.join(top_rpmbuild_dir, "SOURCES")))
            os.mkdir(os.path.abspath(os.path.join(top_rpmbuild_dir, "SPECS")))
            os.mkdir(os.path.abspath(os.path.join(top_rpmbuild_dir, "SRPMS")))
        except:
            logger.critical('could not create directoies in %s' % top_rpmbuild_dir)
            shutil.rmtree(top_rpmbuild_dir, ignore_errors = True)
            sys.exit(1)

    def install (self):
        """
        Create a RPM
        """
        additional_ops = []

        top_rpmbuild_dir = os.path.abspath(tempfile.mkdtemp(suffix = '', prefix = 'rpmbuild-'))

        self._create_dirs(top_rpmbuild_dir)

        pkg_name = self.options['pkg-name']
        pkg_version = self.options.get('pkg-version', '0.1')
        pkg_vendor = self.options.get('pkg-vendor', 'unknown')
        pkg_packager = self.options.get('pkg-packager', 'unknown')
        pkg_url = self.options.get('pkg-url', 'unknown')
        pkg_license = self.options.get('pkg-license', 'unknown')
        pkg_group = self.options.get('pkg-group', 'unknown')
        pkg_autodeps = self.options.get('pkg-autodeps', 'no')

        if self.options.has_key('pkg-deps'):
            additional_ops = additional_ops + ["Requires: " + self.options['pkg-deps']]

        self.install_prefix = self.options.get('install-prefix', os.path.join('opt', pkg_name))

        buildroot_topdir = os.path.abspath(os.path.join(top_rpmbuild_dir, "BUILDROOT", pkg_name))
        buildroot_projdir = os.path.abspath(buildroot_topdir + self.install_prefix)

        # replace the variables in the "spec" template
        rpmspec = RPM_SPEC_TEMPLATE
        rpmspec = rpmspec.replace("@TOP_DIR@", top_rpmbuild_dir)
        rpmspec = rpmspec.replace("@PKG_NAME@", pkg_name)
        rpmspec = rpmspec.replace("@PKG_VENDOR@", pkg_vendor)
        rpmspec = rpmspec.replace("@PKG_VERSION@", pkg_version)
        rpmspec = rpmspec.replace("@PKG_PACKAGER@", pkg_packager)
        rpmspec = rpmspec.replace("@PKG_URL@", pkg_url)
        rpmspec = rpmspec.replace("@PKG_LICENSE@", pkg_license)
        rpmspec = rpmspec.replace("@PKG_GROUP@", pkg_group)
        rpmspec = rpmspec.replace("@PKG_AUTODEPS@", pkg_autodeps)
        rpmspec = rpmspec.replace("@INSTALL_PREFIX@", self.install_prefix)
        rpmspec = rpmspec.replace("@BUILD_ROOT@", buildroot_topdir)
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

        ## create the build directory
        try:
            os.makedirs(buildroot_projdir)
            self._create_venv(buildroot_projdir)
        except:
            logger.critical('Could not create virtual environment at %s' % (buildroot_projdir))
            raise

        ## save the spec file
        spec_filename = os.path.abspath(os.path.join(buildroot_topdir, pkg_name) + ".spec")
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

        self._copy_eggs(buildroot_projdir)
        self._copy_outputs(buildroot_projdir)
        self._prepare_venv(buildroot_projdir)

        # create a tar file at SOURCES/.
        # we can pass a tar file to rpmbuild, so it is easier as we may need
        # a "tar" anyway.
        # the spec file should be inside the tar, at the top level...
        tar_filename = os.path.join(top_rpmbuild_dir, "SOURCES", pkg_name + ".tar")
        tar_filename = self._create_tar(buildroot_topdir, tar_filename)


        # launch rpmbuild
        command = [
            "rpmbuild",
            "--buildroot", buildroot_topdir,
            "--define",
            "_topdir %s" % top_rpmbuild_dir,
            "-ta", tar_filename,
        ]

        logger.debug('Launching "%s"' % ' '.join(command))
        job = subprocess.Popen(command, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
        stdout, _ = job.communicate()

        if job.returncode != 0:
            logger.critical('could not build the RPM')
            print stdout
            return []

        # now try to find the RPMs we have built
        result_rpms = []
        for arch_dir in os.listdir(os.path.join(top_rpmbuild_dir, "RPMS")):
            full_arch_dir = os.path.abspath(os.path.join(top_rpmbuild_dir, "RPMS", arch_dir))
            if os.path.isdir(full_arch_dir):
                for rpm_file in os.listdir(full_arch_dir):
                    if fnmatch.fnmatch(rpm_file, "*.rpm"):
                        full_rpm_file = os.path.abspath(os.path.join(full_arch_dir, rpm_file))

                        shutil.copy(full_rpm_file, self.buildout['buildout']['directory'])

                        logger.debug('Built %s' % (rpm_file))
                        result_rpms = result_rpms + [rpm_file]

        if not self.debug:
            shutil.rmtree(top_rpmbuild_dir)

        return result_rpms

    def update (self):
        pass
