

import logging
import os
import zc.buildout
import shutil
import tempfile
import glob
import subprocess
import fnmatch
import subprocess



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

%define _unpackaged_files_terminate_build   0

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

%description

The @PKG_NAME@ package.
@PKG_LICENSE@

%files

%defattr(-, nobody, nobody, 0755)

@INSTALL_PREFIX@

# empty lines
"""



class FrozenRPM:

    def __init__(self, buildout, name, options):
        self.name, self.options = name, options
        self.buildout = buildout

    def _log(self, msg):
        logging.getLogger(self.name).info(msg)

    def createTar(self, root_dir, buildroot, tarfile):
        # 1. copy the python bins

        bins_sdir   = self.buildout['buildout']['bin-directory']
        bins_ddir   = os.path.normpath(buildroot + "/bin")

        try: os.makedirs(bins_ddir)
        except Exception: pass

        for pybin in glob.glob(bins_sdir + "/python"):
            self._log('Copying python binary: %s' % pybin)
            shutil.copy(pybin, bins_ddir)

        # 2. copy the libs
        lib_sdir = os.path.normpath(self.buildout['buildout']['directory'] + "/lib")
        lib_ddir = os.path.normpath(buildroot + "/lib")

        shutil.copytree(lib_sdir, lib_ddir)

        # 3. copy the eggs
        python_libdir = glob.glob(buildroot + "/lib/python*")[0]

        eggs_sdir = self.buildout['buildout']['eggs-directory']
        eggs_ddir = os.path.normpath(python_libdir + "/site-packages/")

        eggs = [
            r.strip()
            for r in self.options.get('eggs', self.name).split('\n')
            if r.strip()]

        for egg_name in eggs:
            for egg_path in os.listdir(eggs_sdir):
                if fnmatch.fnmatch(egg_path, egg_name + "*.egg"):
                    self._log('Copying egg %s to %s' % (egg_path, python_libdir))

                    egg_src  = os.path.normpath(eggs_sdir + "/" + os.path.basename(egg_path))
                    egg_dest = os.path.normpath(eggs_ddir + "/" + os.path.basename(egg_path))

                    shutil.copytree(egg_src, egg_dest)

        #  create source tar
        self._log('Creating tar file %s' % (tarfile))
        os.system('cd "%(root_dir)s"; tar cfz "%(tarfile)s" *' % vars())



    def createRpm(self):

        top_rpmbuild_dir  = os.path.abspath(tempfile.mkdtemp(suffix= '', prefix = 'rpmbuild-'))

        os.mkdir(top_rpmbuild_dir + "/BUILDROOT")
        os.mkdir(top_rpmbuild_dir + "/RPMS")
        os.mkdir(top_rpmbuild_dir + "/SOURCES")
        os.mkdir(top_rpmbuild_dir + "/SPECS")
        os.mkdir(top_rpmbuild_dir + "/SRPMS")

        pkg_name       = self.options['pkg-name']
        pkg_version    = self.options.get('pkg-version', '0.1')
        pkg_vendor     = self.options.get('pkg-vendor', 'unknown')
        pkg_packager   = self.options.get('pkg-packager', 'unknown')
        pkg_url        = self.options.get('pkg-url', 'unknown')
        pkg_license    = self.options.get('pkg-license', 'unknown')
        pkg_group      = self.options.get('pkg-group', 'unknown')
        pkg_autodeps   = self.options.get('pkg-autodeps', 'no')

        buildroot_topdir  = top_rpmbuild_dir + "/BUILDROOT/" + pkg_name

        install_prefix    = self.options.get('install-prefix', '/opt/' + pkg_name)

        buildroot_projdir = os.path.normpath(buildroot_topdir + "/" + install_prefix)


        rpmspec = RPM_SPEC_TEMPLATE
        rpmspec = rpmspec.replace("@TOP_DIR@",         top_rpmbuild_dir)
        rpmspec = rpmspec.replace("@PKG_NAME@",        pkg_name)
        rpmspec = rpmspec.replace("@PKG_VENDOR@",      pkg_vendor)
        rpmspec = rpmspec.replace("@PKG_VERSION@",     pkg_version)
        rpmspec = rpmspec.replace("@PKG_PACKAGER@",    pkg_packager)
        rpmspec = rpmspec.replace("@PKG_URL@",         pkg_url)
        rpmspec = rpmspec.replace("@PKG_LICENSE@",     pkg_license)
        rpmspec = rpmspec.replace("@PKG_GROUP@",       pkg_group)
        rpmspec = rpmspec.replace("@PKG_AUTODEPS@",    pkg_autodeps)
        rpmspec = rpmspec.replace("@INSTALL_PREFIX@",  install_prefix)
        rpmspec = rpmspec.replace("@BUILD_ROOT@",      buildroot_topdir)

        # create the spec file
        os.makedirs(buildroot_topdir)
        spec_filename = os.path.normpath(buildroot_topdir + "/" + pkg_name + ".spec")

        self._log('Using spec file %s' % (spec_filename))
        spec_file = None
        try:
            spec_file = open(spec_filename, "w")
            spec_file.write(rpmspec)
            spec_file.flush()
        except Exception, e:
            return []

        if spec_file:
            spec_file.close()

        tarfile = top_rpmbuild_dir + "/SOURCES/" + pkg_name + ".tar"
        self.createTar(buildroot_topdir, buildroot_projdir, tarfile)

        rpmbuild = [
                    "rpmbuild",
                    "--buildroot", buildroot_topdir,
                    "--define", "_topdir %s" % (top_rpmbuild_dir,),
                    "-ta", tarfile,
                ]

        self._log('Launching "%s"' % (" ".join(rpmbuild)))
        job = subprocess.Popen(rpmbuild,
                               stdout = subprocess.PIPE,
                               stderr = subprocess.STDOUT)
        stdout, _ = job.communicate()

        if job.returncode != 0:
            print stdout
            return []

        result_rpms = []
        for arch_dir in os.listdir(top_rpmbuild_dir + "/RPMS"):
            full_arch_dir = os.path.abspath(top_rpmbuild_dir + "/RPMS/" + arch_dir)
            if os.path.isdir(full_arch_dir):
                for rpm_file in os.listdir(full_arch_dir):
                    if fnmatch.fnmatch(rpm_file, "*.rpm"):
                        full_rpm_file = os.path.abspath(full_arch_dir + "/" + rpm_file)
                        full_local_rpm_file = os.path.abspath(self.buildout['buildout']['directory'] + "/" + os.path.basename(full_rpm_file))

                        shutil.copyfile(full_rpm_file, full_local_rpm_file)

                        self._log('Built %s' % (full_local_rpm_file))
                        result_rpms = result_rpms + [full_local_rpm_file]

        return result_rpms

    def install(self):
        return self.createRpm()

    def update(self):
        pass
