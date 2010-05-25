

import os
import sys
import shutil
import tempfile
import logging

import glob
import fnmatch

import subprocess

import zc.buildout
import zc.recipe.egg


SKIP_SYS_DIRS = [
    'site-packages',
    'dist-packages'
]



####################################################################################################

NAMESPACE_STANZA = """
# See http://peak.telecommunity.com/DevCenter/setuptools#namespace-packages
try:
    __import__('pkg_resources').declare_namespace(__name__)
except ImportError:
    from pkgutil import extend_path
    __path__ = extend_path(__path__, __name__)
"""


def makedirs(target, is_namespace = False):
    """
    Similar to os.makedirs, but adds __init__.py files as it goes.  Returns a boolean
    indicating success.
    """
    drive, path = os.path.splitdrive(target)
    parts = path.split(os.path.sep)
    current = drive + os.path.sep
    for part in parts:
        current = os.path.join(current, part)
        if os.path.islink(current):
            return False
        if not os.path.exists(current):
            os.mkdir(current)
            init_filename = os.path.join(current, '__init__.py')
            if not os.path.exists(init_filename):
                init_file = open(init_filename, 'w')
                if is_namespace:
                    init_file.write(NAMESPACE_STANZA)
                else:
                    init_file.write('# mushroom')
                init_file.close()
    return True


####################################################################################################

class Frozen(object):
    """
    Frozen packages base class
    """

    def __init__(self, buildout, name, options):
        self.name = name
        self.options = options
        self.buildout = buildout
        self.logger = logging.getLogger(self.name)

        self.egg = zc.recipe.egg.Egg(buildout, options['recipe'], options)

        debug = options.get('debug', '').lower()
        if debug in ('yes', 'true', 'on', '1', 'sure'):
            self.debug = True
        else:
            self.debug = False

        ignore_develop = options.get('ignore-develop', '').lower()
        develop_eggs = []
        if ignore_develop in ('yes', 'true', 'on', '1', 'sure'):
            develop_eggs = os.listdir(
                               buildout['buildout']['develop-eggs-directory'])
            develop_eggs = [dev_egg[:-9] for dev_egg in develop_eggs]

        ignores = options.get('ignores', '').split()
        self.ignored_eggs = develop_eggs + ignores

        products = options.get('products', '').split()
        self.packages = [(p, 'Products') for p in products]
        self.packages += [l.split()
                         for l in options.get('packages', '').splitlines()
                         if l.strip()]

        # the "site-packages" installation directory
        self.site_packages_rel_dir = None
        self.site_packages_full_dir = None


    def _checkPython(self):
        if sys.version_info < (2, 6):
            raise "must use python 2.6 or greater"


    def _log(self, msg, isdebug = True):
        if (not isdebug) or self.debug:
            self.logger.info(msg)


    def _replaceInFile(self, filename, orig_str, new_str):
        #self._log('Replacing %s by %s' % (orig_str, new_str))

        try:
            with open(filename, "r") as f:
                content = f.read(65535 * 4)

            new_content = content.replace(orig_str, new_str)

            with open(filename, "w") as f:
                f.write(new_content)

        except Exception, e:
            print "ERROR: when replacing strings in %s" % filename, e


    def _copyFiles(self, src, dest):
        """
        Copy a files tree
        """
        if not os.path.exists(src):
            self._log('Cannot find file %s (bad symlink)' % src)
            return

        if os.path.exists(dest):
            self._log('File %s already exists' % dest)
            return

        if not os.path.exists(os.path.dirname(dest)):
            self._log('Creating parent directories for %s' % os.path.dirname(dest))
            os.makedirs(os.path.dirname(dest))

        # self._log('Copying to %s' % dest)
        if os.path.isdir(src):
            shutil.copytree(src, dest, symlinks = False)
        else:
            shutil.copy2(src, dest)


    def _getPythonBin(self, root, vers = ""):
        """
        Get the python exe
        """
        pos_p = [
                self.buildout['buildout']['bin-directory'] + "/python" + vers,
                self.buildout['buildout']['bin-directory'] + "/python" + vers.replace(".", ""),
                self.buildout['buildout']['bin-directory'] + "/python",
                "/usr/local/bin/python" + vers,
                "/usr/local/bin/python" + vers.replace(".", ""),
                "/usr/local/bin/python",
                "/usr/bin/python" + vers,
                "/usr/bin/python" + vers.replace(".", ""),
                "/usr/bin/python"
        ]

        for p in pos_p:
            if os.path.exists(p):
                return p

        return None


    def _getPythonLibDir(self, root, pythonexe = None):
        assert (root != None)
        assert (len(root) > 0)

        if not pythonexe:
            return os.path.abspath(glob.glob(root + "/lib/python*")[0])
        else:
            if os.path.exists(pythonexe):
                pythonquery = [
                    pythonexe,
                    "-c",
                    "import os ; print os.path.dirname(os.__file__)"
                ]

                # self._log('Running %s' % (" ".join(pythonquery)))
                job = subprocess.Popen(pythonquery,
                               stdout = subprocess.PIPE,
                               stderr = subprocess.PIPE)
                (stdoutdata, stderrdata) = job.communicate()
                if job.returncode == 0:
                    libdir = [r.strip() for r in stdoutdata.split('\n')][0]
                    self._log('Library found at %s' % (libdir))
                    return libdir

            return None


    def _getPythonVers(self, pythonexe):
        if os.path.exists(pythonexe):
            pythonquery = [
                pythonexe,
                "-c",
                "import sys; print str(sys.version_info[0]) + '.' + str(sys.version_info[1])"
            ]

            # self._log('Running %s' % (" ".join(pythonquery)))
            job = subprocess.Popen(pythonquery,
                            stdout = subprocess.PIPE,
                            stderr = subprocess.PIPE)
            (stdoutdata, stderrdata) = job.communicate()
            if job.returncode == 0:
                vers = [r.strip() for r in stdoutdata.split('\n')][0]
                self._log('Python version found %s' % (vers))
                return vers

        return None


    def _getPythonInfo(self, buildroot_projdir):
        """
        Get the python binary, the version and the library.
        """
        self.python_vers = None
        if self.options.has_key('python-version'):
            self.python_vers = self.options['python-version']

        if self.options.has_key('sys-python'):
            self.python_bin = self.options['sys-python']
        else:
            self.python_bin = self._getPythonBin(buildroot_projdir, self.python_vers)

        if not self.python_vers:
            self.python_vers = self._getPythonVers(self.python_bin)

        if not self.python_bin or not self.python_vers:
            print "ERROR: python binary or version not found"
            sys.exit(1)

        self.python_bin_rel = self.install_prefix + "/bin/" + os.path.basename(self.python_bin)

        if self.options.has_key('skip-sys'):
            self.python_skip_sys = (self.options['skip-sys'].lower() == "yes" or \
                                    self.options['skip-sys'].lower() == "true")
        else:
            self.python_skip_sys = False

        if self.options.has_key('sys-lib'):
            self.python_libdir = self.options['sys-lib']
        else:
            self.python_libdir = self._getPythonLibDir(buildroot_projdir, self.python_bin)

        if not self.python_libdir:
            print "ERROR: python library not found"
            sys.exit(1)
        else:
            # remove some prefixes, so that
            # BUILDROOT/opt/pkg/usr/lib64/python2.6   ->   lib64/python2.6
            prefixes = [
                buildroot_projdir,
                self.buildout['buildout']['directory'],
                "/usr",
                "/usr/local",
                "/opt",
                "/System/Library/Frameworks/Python.framework/Versions/" + self.python_vers,
                "/System/Library/Frameworks/Python.framework/Versions/" + self.python_vers.replace(".", "")
            ]
            self.python_libdir_rel = self.python_libdir
            for p in prefixes:
                self.python_libdir_rel = self.python_libdir_rel.replace(p, "")




    def _copyPythonDist(self, root_dir, install_prefix):
        """
        Copy the basic python distribution files: the Python interpreter and
        the standard library files.
        """

        replacements = []

        buildroot = os.path.abspath(root_dir + "/" + install_prefix)

        # copy the python bins
        bins_sdir = self.buildout['buildout']['bin-directory']
        bins_ddir = os.path.abspath(buildroot + "/bin")

        venv_python_bin = self.buildout['buildout']['bin-directory'] + "/python"

        self._log('Copying python binary %s to %s' % (self.python_bin, self.install_prefix + "/bin"))
        os.makedirs(bins_ddir)
        shutil.copy(self.python_bin, bins_ddir)

        replacements = replacements + [
                                      (self.python_bin, self.python_bin_rel),
                                      (venv_python_bin, self.python_bin_rel)
                                      ]

        # calculate the local python "lib"
        venv_lib_prefix = '/lib/python' + self.python_vers
        venv_lib_sdir = os.path.abspath(self.buildout['buildout']['directory'] + venv_lib_prefix)
        if not os.path.exists(venv_lib_sdir):
            venv_lib_prefix = '/lib64/python' + self.python_vers
            venv_lib_sdir = os.path.abspath(self.buildout['buildout']['directory'] + venv_lib_prefix)

        # copy the libs
        if self.python_skip_sys:
            lib_prefix = venv_lib_prefix
            lib_sdir = venv_lib_sdir
        else:
            lib_prefix = self.python_libdir
            lib_sdir = lib_prefix


        lib_ddir = os.path.abspath(buildroot + self.python_libdir_rel)
        rel_lib_ddir = lib_ddir.replace(root_dir, "")

        if not os.path.isdir(lib_sdir):
            print "ERROR: %s is not a directory" % lib_sdir
            sys.exit(1)

        self._log('Copying system library %s to %s' %
                      (lib_sdir, self.install_prefix + self.python_libdir_rel))
        try:
            for fn in os.listdir(lib_sdir):
                if not fn in SKIP_SYS_DIRS:
                    self._copyFiles(os.path.abspath(lib_sdir + "/" + fn),
                                    os.path.abspath(lib_ddir + "/" + fn))
        except Exception, e:
            self._log('ERROR: when copying %s' % lib_sdir)
            print e

        # copy the site libs
        site_lib_sdir = os.path.abspath(venv_lib_sdir + '/site-packages')
        if os.path.exists(site_lib_sdir):
            site_lib_ddir = os.path.abspath(lib_ddir + '/site-packages')
            rel_site_lib_ddir = site_lib_ddir.replace(root_dir, "")

            shutil.copytree(site_lib_sdir, site_lib_ddir)

            # save the "site-packages" directory
            self.site_packages_rel_dir = rel_site_lib_ddir
            self.site_packages_full_dir = site_lib_ddir

            replacements = replacements + [
                        (site_lib_sdir, rel_site_lib_ddir)
                       ]

        # here comes a really DIRTY HACK !!!
        # in order to put the new library in front of the PYTHONPATH, we
        # replace "sys.path[0:0] = [" by the same string PLUS the new
        # library path...
        base_string = "sys.path[0:0] = ["
        new_base_string = base_string + "\n" + \
                          "  '" + rel_lib_ddir + "',\n" + \
                          "  '" + rel_lib_ddir + "/lib-dynload" + "',\n" + \
                          "  '" + rel_site_lib_ddir + "',"

        replacements = replacements + [
                        (base_string, new_base_string)
                       ]

        return replacements


    def _copyNeededEggs(self, root_dir, install_prefix):
        """
        Copy the eggs
        The list of eggs is obtained from the 'eggs' option.
        """
        assert (root_dir != None and len(root_dir) > 0)
        assert (install_prefix != None and len(install_prefix) > 0)

        replacements = []

        assert (self.site_packages_full_dir != None)
        eggs_ddir = self.site_packages_full_dir

        self._log('Copying eggs to %s' % eggs_ddir)

        try:
            requirements, ws = self.egg.working_set()

            for dist in ws.by_key.values():
                project_name = dist.project_name
                self._log('... processing %s egg' % project_name)
                if project_name in self.ignored_eggs:
                    self._log('...... ignored')
                else:
                    namespaces = {}
                    for line in dist._get_metadata('namespace_packages.txt'):
                        ns = namespaces
                        for part in line.split('.'):
                            ns = ns.setdefault(part, {})
                    top_level = list(dist._get_metadata('top_level.txt'))
                    native_libs = list(dist._get_metadata('native_libs.txt'))

                    def create_namespaces(namespaces, ns_base = ()):
                        for k, v in namespaces.iteritems():
                            ns_parts = ns_base + (k,)
                            link_dir = os.path.join(eggs_ddir, *ns_parts)
                            if not os.path.exists(link_dir):
                                if not makedirs(link_dir, is_namespace = True):
                                    self.logger.warn("WARNING: while processing egg %s: could not create namespace directory (%s).  Skipping." % (project_name, link_dir))
                                    continue

                            if len(v) > 0:
                                create_namespaces(v, ns_parts)
                            else:
                                egg_ns_dir = os.path.join(dist.location, *ns_parts)
                                if not os.path.isdir(egg_ns_dir):
                                    self.logger.info("WARNING: while processing egg '%s': package '%s' is zipped. Skipping." % (project_name, os.path.sep.join(ns_parts)))
                                    continue
                                dirs = os.listdir(egg_ns_dir)
                                for name in dirs:
                                    if not os.path.isdir(os.path.join(egg_ns_dir, name)):
                                        continue
                                    if name.startswith('.'):
                                        continue
                                    name_parts = ns_parts + (name,)
                                    src = os.path.join(dist.location, *name_parts)
                                    dst = os.path.join(eggs_ddir, *name_parts)
                                    if not os.path.exists(dst):
                                        if os.path.isdir(src):
                                            shutil.copytree(src, dst)
                                        else:
                                            shutil.copy(src, dst)

                    create_namespaces(namespaces)

                    for package_name in top_level:
                        if package_name in namespaces:
                            # These are processed in create_namespaces
                            continue
                        else:
                            if not os.path.isdir(dist.location):
                                self.logger.info("...... copying package '%s' / '%s'." % (project_name, package_name))
                                dest = os.path.join(eggs_ddir, package_name)
                                shutil.copy(dist.location, dest)
                            else:
                                package_location = os.path.join(dist.location, package_name)
                                link_location = os.path.join(eggs_ddir, package_name)

                                # check for single python module
                                if not os.path.exists(package_location):
                                    package_location = os.path.join(dist.location, package_name + ".py")
                                    link_location = os.path.join(eggs_ddir, package_name + ".py")

                                # check for native libs
                                # XXX - this should use native_libs from above
                                if not os.path.exists(package_location):
                                    package_location = os.path.join(dist.location, package_name + ".so")
                                    link_location = os.path.join(eggs_ddir, package_name + ".so")

                                if not os.path.exists(package_location):
                                    package_location = os.path.join(dist.location, package_name + ".dll")
                                    link_location = os.path.join(eggs_ddir, package_name + ".dll")

                                if not os.path.exists(package_location):
                                    self.logger.warn("WARNING: while processing egg '%s': package '%s' not found. Skipping." % (project_name, package_name))
                                    continue

                                if not os.path.exists(link_location):
                                    self._log('...... copying tree for %s' % (package_name))
                                    shutil.copytree(package_location, link_location)
                                else:
                                    self.logger.info("WARNING: while processing egg '%s': link already exists '%s' -> '%s'. Skipping." % (project_name, package_location, link_location))

        except:
            if os.path.exists(eggs_ddir) and not self.debug:
                shutil.rmtree(eggs_ddir)
            raise

        return replacements



    def _copyExtraFiles(self, root_dir, install_prefix):
        """
        Copy any extra files, from the 'extra' options in the buildout
        """
        assert (root_dir != None and len(root_dir) > 0)
        assert (install_prefix != None and len(install_prefix) > 0)

        replacements = []

        buildroot = os.path.normpath(root_dir + "/" + install_prefix)

        extra_copies = [
            r.strip()
            for r in self.options.get('extra-copies', self.name).split('\n')
            if r.strip()]
        for copy_line in extra_copies:
            try:
                src, dest = [b.strip() for b in copy_line.split("->")]
            except Exception, e:
                print "ERROR: malformed copy specification", e
                return replacements

            if not os.path.isabs(src):
                src = self.buildout['buildout']['directory'] + '/' + src

            full_path_dest = os.path.normpath(buildroot + "/" + dest)
            for src_el in glob.glob(src):
                self._log('Copying %s' % src_el)
                try:
                    if os.path.isdir(src_el):
                        shutil.copytree(src_el, full_path_dest)
                    else:
                        shutil.copy(src_el, full_path_dest)

                except Exception, e:
                    self._log('ERROR: when copying %s to %s' % (src_el, full_path_dest))

        return replacements

    def _fixScripts(self, replacements, buildroot_projdir):
        """
        Fix the copied scripts, by replacing some paths by the new
        installation paths, and creating a wrapper script that will call the
        real Python script after setting some environment variables...
        """
        if self.options.has_key('scripts'):

            fix_scripts = [
                r.strip()
                for r in self.options['scripts'].split('\n') if r.strip()]

            for scr in fix_scripts:
                full_scr_path = self.buildout['buildout']['bin-directory'] + "/" + scr
                new_scr_path = buildroot_projdir + "/bin/" + scr + ".real"
                new_wrapper_path = buildroot_projdir + "/bin/" + scr
                new_rel_path = self.install_prefix + "/bin/" + scr + ".real"

                if os.path.exists(full_scr_path):
                    self._log('Copying %s' % (scr))
                    shutil.copyfile (full_scr_path, new_scr_path)

                    self._log('... and fixing paths at %s' % (scr))
                    for orig_str, new_str in replacements:
                        self._replaceInFile(new_scr_path, orig_str, new_str)

                    # Create a wrapper file that will set the library path and
                    # then call the real Python script
                    self._log('... and creating wrapper %s' % (os.path.basename(new_wrapper_path)))
                    with open(new_wrapper_path, "w") as w:
                        w.write("#!/bin/sh\n")
                        w.write("\n\n")

                        # Set the right LD_LIBRARY_PATH
                        w.write("LD_LIBRARY_PATH=%s:%s:$LD_LIBRARY_PATH\n" % \
                            (self.install_prefix + "/lib64",
                             self.install_prefix + "/lib"))
                        w.write("export LD_LIBRARY_PATH\n\n")

                        # Set a different PYTHONPATH
                        w.write("PYTHONPATH=%s\n" % \
                            (self.install_prefix + "/" + self.python_libdir_rel))
                        w.write("export PYTHONPATH\n\n")

                        w.write("%s %s $@\n\n" % (self.python_bin_rel, new_rel_path))
                        os.chmod(new_wrapper_path, 0755)

                    os.chmod(new_scr_path, 0755)

                else:
                    self._log('WARNING: script %s not found' % (full_scr_path))

    def _createTar(self, root_dir, tarfile, compress = False):
        """
        Create a tar file with all the needed files
        """

        # Check if we can create the tar file
        f = os.path.basename(tarfile)
        d = os.path.dirname(tarfile)
        if not os.path.exists(d):
            os.makedirs(d)

        self._log('Creating tar file %s at %s' % (f, d))

        # warning: these "tar" args work on Linux, but not on Mac
        if os.uname()[0] == 'Darwin':
            # -H follows the symlink and archives the link target
            tar_flags = "-c -p -f"
        else:
            tar_flags = "-c -p --dereference -f"

        cmd = 'cd "%(root_dir)s" ; tar %(tar_flags)s "%(tarfile)s" *' % vars()
        if self.debug:
            self._log('... running %s' % (cmd))
        os.system(cmd)

        if compress:
            if self.debug:
                self._log('... compressing %s' % (tarfile))
            cmd = 'gzip "%(tarfile)s"' % vars()
            os.system(cmd)
            result = os.path.join(tarfile + ".gz")
        else:
            result = tarfile

        return result




###############################################################################

if __name__ == '__main__':
    f = Frozen()
