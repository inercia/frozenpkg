

import logging
import os
import shutil
import tempfile

import zc.buildout
import glob
import fnmatch

import subprocess

import setuptools
from setuptools.command.easy_install import easy_install

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



class FrozenRPM(object):

    def __init__(self, buildout, name, options):
        self.name, self.options = name, options
        self.buildout = buildout
        self.debug    = False

    def _log(self, msg):
        if self.debug:
            logging.getLogger(self.name).info(msg)

    def _replaceInFile(self, filename, orig_str, new_str):
        try:
            with open(filename, "r") as f:
                content = f.read(65535 * 4)

            new_content = content.replace(orig_str, new_str)

            with open(filename, "w") as f:
                f.write(new_content)

        except Exception, e:
            print "ERROR: when replacing strings in %s" % filename, e

    def _getPythonLibDir(self, root):
        assert (root != None)
        assert (len(root) > 0)
        return os.path.abspath(glob.glob(root + "/lib/python*")[0])

    def _copyNeededEggs(self, root_dir, install_prefix):
        """
        Copy the eggs
        """
        replacements  = []
        
        buildroot     = os.path.normpath(root_dir + "/" + install_prefix)
        python_libdir = self._getPythonLibDir(buildroot)

        eggs_sdir    = self.buildout['buildout']['eggs-directory']
        eggs_devsdir = self.buildout['buildout']['develop-eggs-directory']
        eggs_ddir    = os.path.normpath(python_libdir + "/site-packages/")

        eggs = [
            r.strip()
            for r in self.options.get('eggs', self.name).split('\n')
            if r.strip()]

        for egg_name in eggs:
            # first, look for any eggs we need from the "eggs" directory
            for egg_path in os.listdir(eggs_sdir):
                if fnmatch.fnmatch(egg_path, egg_name + "*.egg"):
                    self._log('Copying egg %s to %s' % (egg_path, eggs_ddir))

                    egg_src  = os.path.abspath(eggs_sdir + "/" + os.path.basename(egg_path))
                    egg_dest = os.path.abspath(eggs_ddir + "/" + os.path.basename(egg_path))

                    shutil.copytree(egg_src, egg_dest)
                    
                    egg_dest_rel = egg_dest.replace(root_dir, "")
                    replacements = replacements + [(egg_src, egg_dest_rel)]

            # now look for the "develop-eggs"
            for egg_path in os.listdir(eggs_devsdir):
                if fnmatch.fnmatch(egg_path, egg_name + "*.egg-link"):
                    egg_lnk_src  = os.path.normpath(eggs_devsdir + "/" + os.path.basename(egg_path))

                    with open(egg_lnk_src) as f:
                        egg_src = f.readline().strip()
                        egg_dest = os.path.normpath(eggs_ddir + "/" + egg_name)

                        self._log('Copying egg %s link to %s' % (egg_name, egg_dest))
                        shutil.copytree(egg_src, egg_dest)

                        egg_dest_rel = egg_dest.replace(root_dir, "")
                        replacements = replacements + [(egg_src, egg_dest_rel)]
                        
                        self._log('Fixing egg-info')
                        shutil.move (egg_dest + "/" + egg_name + ".egg-info", eggs_ddir)


        return replacements
        
    def _copyPythonDist(self, root_dir, install_prefix):

        replacements  = []
        
        buildroot     = os.path.normpath(root_dir + "/" + install_prefix)

        # copy the python bins
        bins_sdir   = self.buildout['buildout']['bin-directory']
        bins_ddir   = os.path.normpath(buildroot + "/bin")

        try: os.makedirs(bins_ddir)
        except Exception: pass

        for pybin in glob.glob(bins_sdir + "/python"):
            self._log('Copying python binary: %s' % pybin)
            shutil.copy(pybin, bins_ddir)
            replacements = replacements + [
                            (pybin, lib_ddir.replace(bins_ddir, ""))
                           ]

        # copy the libs
        lib_sdir = os.path.normpath(self.buildout['buildout']['directory'] + "/lib")
        lib_ddir = os.path.normpath(buildroot + "/lib")

        shutil.copytree(lib_sdir, lib_ddir)

        replacements = replacements + [
                        (lib_sdir, lib_ddir.replace(root_dir, ""))
                       ]

        return replacements


    def _createTar(self, root_dir, tarfile):
        """
        Create a tar file with all the needed files
        """
        self._log('Creating tar file %s' % (tarfile))
        os.system('cd "%(root_dir)s"; tar cfz "%(tarfile)s" *' % vars())
        return tarfile

    def _createRpm(self):
        """
        Create a RPM
        """

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

        if self.options.has_key('debug'):
            self.debug = True

        buildroot_topdir  = top_rpmbuild_dir + "/BUILDROOT/" + pkg_name

        install_prefix    = self.options.get('install-prefix', '/opt/' + pkg_name)

        buildroot_projdir = os.path.normpath(buildroot_topdir + "/" + install_prefix)

        # replace the variables in the "spec" template
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

        replacements  = []

        # copy all the files we need
        replacements = replacements + self._copyPythonDist(buildroot_topdir, buildroot_projdir)
        replacements = replacements + self._copyNeededEggs(buildroot_topdir, install_prefix)
        
        # fix the copied scripts, by replacing some paths by the new
        # installation paths
        if self.options.has_key('scripts'):

            replacements = replacements + [
                (self.buildout['buildout']['directory'],      install_prefix)
            ]

            fix_scripts = [
                r.strip()
                for r in self.options['scripts'].split('\n') if r.strip()]

            for scr in fix_scripts:
                full_scr_path = self.buildout['buildout']['bin-directory'] + "/" + scr
                new_scr_path  = buildroot_projdir + "/bin/" + scr
                
                if os.path.exists(full_scr_path):
                    self._log('Copying %s' % (full_scr_path))
                    shutil.copyfile (full_scr_path, new_scr_path)
                    
                    self._log('Fixing paths at %s' % (new_scr_path))
                    for orig_str, new_str in replacements:
                        self._log('... replacing %s by %s' % (orig_str, new_str))                        
                        self._replaceInFile(new_scr_path, orig_str, new_str)
                else:
                    self._log('WARNING: script %s not found' % (full_scr_path))

        # create a tar file at SOURCES/.
        # we can pass a tar file to rpmbuild, so it is easier as we may need a "tar" anyway.
        # the spec file should be inside the tar, at the top level...
        tarfile = top_rpmbuild_dir + "/SOURCES/" + pkg_name + ".tar"
        tarfile = self._createTar(buildroot_topdir, tarfile)

        # launch rpmbuild
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


        # now try to find the RPMs we have built
        result_rpms = []
        for arch_dir in os.listdir(top_rpmbuild_dir + "/RPMS"):
            full_arch_dir = os.path.abspath(top_rpmbuild_dir + "/RPMS/" + arch_dir)
            if os.path.isdir(full_arch_dir):
                for rpm_file in os.listdir(full_arch_dir):
                    if fnmatch.fnmatch(rpm_file, "*.rpm"):
                        full_rpm_file = os.path.abspath(full_arch_dir + "/" + rpm_file)

                        shutil.copy(full_rpm_file, self.buildout['buildout']['directory'])

                        self._log('Built %s' % (rpm_file))
                        result_rpms = result_rpms + [rpm_file]

        if not self.debug:
            shutil.rmtree(top_rpmbuild_dir)

        return result_rpms

    def install(self):
        return self._createRpm()

    def update(self):
        pass
