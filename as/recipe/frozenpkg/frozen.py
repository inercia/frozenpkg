

import os
import sys
import shutil
import logging
import glob
import re
import tempfile
import pkg_resources
import subprocess



logger = logging.getLogger(__name__)



#: list of regular expressions for eggs that we will not copy
SKIP_EGGS = [
    'zc.recipe.egg-.*',
]



def _lst_from_cfg(opt):
    return [r.strip() for r in opt.split('\n') if r.strip()]

################################################################################

class Frozen(object):
    """
    Frozen packages base class
    """

    def __init__ (self, buildout, name, options):
        self.name = name
        self.options = options
        self.buildout = buildout
        self.logger = logging.getLogger(self.name)

        # patch some options
        self.eggs = self.options["eggs"]

        debug = options.get('debug', '').lower()
        if debug in ('yes', 'true', 'on', '1', 'sure'):
            self.debug = True
        else:
            self.debug = False

    def install(self):
        """
        Create a RPM
        """
        self.rpmbuild_dir = os.path.abspath(tempfile.mkdtemp(suffix = '', prefix = 'rpmbuild-'))

        self.pkg_name = self.options['pkg-name']
        self.pkg_version = self.options.get('pkg-version', '0.1')
        self.pkg_vendor = self.options.get('pkg-vendor', 'unknown')
        self.pkg_packager = self.options.get('pkg-packager', 'unknown')
        self.pkg_url = self.options.get('pkg-url', 'unknown')
        self.pkg_license = self.options.get('pkg-license', 'unknown')
        self.pkg_group = self.options.get('pkg-group', 'unknown')
        self.pkg_autodeps = self.options.get('pkg-autodeps', 'no')
        self.pkg_prefix = self.options.get('pkg-prefix', os.path.join('opt', self.pkg_name))

        self.buildroot = os.path.abspath(os.path.join(self.rpmbuild_dir, "BUILDROOT", self.pkg_name))
        self.virtualenv_dir = os.path.abspath(self.buildroot + self.pkg_prefix)

        ## create the build directory
        try:
            if not os.path.exists(self.virtualenv_dir):
                os.makedirs(self.virtualenv_dir)

            self._create_venv()
        except:
            logger.critical('ERROR: could not create virtual environment at "%s".' % (self.virtualenv_dir))
            raise

    ############################################################################

    def _virtualenv_path(self, path):
        """
        Return a path inside the virtualenv
        """
        return os.path.normpath(os.path.abspath(self.virtualenv_dir + '/' + path))

    def _create_venv(self):
        """
        Create a virtualenv in a directory
        """

        ## we cannot use the Virtualenv library: there is something broken that do not allows us
        ## to use it as a library...

        virtualenv = [
            'virtualenv',
            '--distribute',
            '--no-site-packages',
            '--clear',
            self.virtualenv_dir,
            ]

        logger.info('Creating virtualenv by launching "%s".' % (" ".join(virtualenv)))
        job = subprocess.Popen(virtualenv,
                               stdout = subprocess.PIPE,
                               stderr = subprocess.STDOUT)
        stdout, _ = job.communicate()

        if job.returncode != 0:
            logger.critical('could not run virtualenv')
            sys.exit(1)


    def _copy_eggs (self):
        """
        Copy all the required eggs to the virtualenv
        """
        bin_dir = os.path.join(self.virtualenv_dir, 'bin')
        easy_install = os.path.join(bin_dir, 'easy_install')
        if not os.path.exists(easy_install):
            logger.critical('could NOT find easy_install at %s' % easy_install )
            sys.exit(1)

        distributions = _lst_from_cfg(self.options.get('eggs', self.name))

        import zc.buildout.easy_install
        ws = zc.buildout.easy_install.working_set(
                distributions,
                [self.buildout['buildout']['develop-eggs-directory'], self.buildout['buildout']['eggs-directory']]
                )

        logger.info('Installing eggs in virtualenv.')
        for dist in ws:

            ## check if we must skip this egg
            skip_eggs = _lst_from_cfg(self.options.get('eggs-skip', '')) + list(SKIP_EGGS)
            if dist.key in skip_eggs:
                logger.debug('... skipping "%s"' % dist.key)
                continue

            logger.info('... installing "%s" from "%s"' % (dist.key, dist.location))

            args = ['--no-deps']
            try:
                find_links = _lst_from_cfg(self.buildout['buildout']['find-links'])
                for l in find_links:
                    args += ['--find-links', l]
            except KeyError:
                logger.debug('... no additional find-links')

            command = [easy_install] + args + [dist.location]
            job = subprocess.Popen(command, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
            stdout, _ = job.communicate()

            if job.returncode != 0:
                logger.debug('...... retrying with easy_install')
                command = [easy_install] + args + ["%s==%s" % (dist.key, dist.version)]
                job = subprocess.Popen(command, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
                stdout, _ = job.communicate()

                if job.returncode != 0:
                    from zc.buildout import UserError
                    msg = 'could NOT run easy_install: %s: %s' % (' '.join(command), stdout)
                    logger.critical()
                    raise UserError(stdout)


    def _copy_outputs(self):
        """
        Copies the outputs from parts
        :param self.virtualenv_dir: the root directory where to copy things
        """
        logger.info('Copying outputs.')
        buildout_dir = self.buildout['buildout']['directory']
        for part in self.buildout['buildout']['parts'].split():
            try:
                outputs = self.buildout[part]['output']
                for output in outputs.splitlines():
                    rel_dir = os.path.relpath(output, buildout_dir)
                    dest_dir = self._virtualenv_path(os.path.dirname(rel_dir))

                    logger.debug('... "%s" -> "%s"' % (rel_dir, dest_dir))
                    if not os.path.exists(dest_dir):
                        os.makedirs(dest_dir)
                    shutil.copy2(output, dest_dir)

            except KeyError:
                pass


    def _copy_extra_files (self):
        """
        Copy any extra files, from the 'extra' options in the buildout
        :param self.virtualenv_dir: the root directory where to copy things
        """
        assert (self.virtualenv_dir != None and len(self.virtualenv_dir) > 0)
        assert (self.pkg_prefix != None and len(self.pkg_prefix) > 0)

        buildout_dir = self.buildout['buildout']['directory']

        extra_copies = _lst_from_cfg(self.options.get('extra-copies', self.name))
        logger.info('Copying extras.')
        for copy_line in extra_copies:
            try:
                src, dest = [b.strip() for b in copy_line.split("->")]
            except Exception, e:
                print "ERROR: malformed copy specification", e
                return

            if not os.path.isabs(src):
                src = os.path.join(buildout_dir, src)

            full_path_dest = os.path.normpath(self._virtualenv_path(dest))
            for src_el in glob.glob(src):
                logger.debug('... copying "%s".' % src_el)
                try:
                    if os.path.isdir(src_el):
                        shutil.copytree(src_el, full_path_dest)
                    else:
                        # maybe the destination is a directory: then we have to
                        # create it at the target too...
                        if dest.endswith('/') and not os.path.exists(full_path_dest):
                            logger.debug('... creating "%s" directory.' % dest)
                            os.makedirs(full_path_dest)

                        shutil.copy(src_el, full_path_dest)

                except Exception, e:
                    logger.critical('ERROR: when copying "%s" to "%s"' % (src_el, full_path_dest))


    def _create_extra_dirs (self):
        """
        Create any extra dirs
        :param self.virtualenv_dir: the root directory where to copy things
        """
        assert self.virtualenv_dir != None and len(self.virtualenv_dir) > 0

        extra_dirs_str = self.options.get('extra-dirs', None)
        if extra_dirs_str:
            logger.info('Creating extras directories.')
            for directory in _lst_from_cfg(extra_dirs_str):

                full_path_dest = self._virtualenv_path(directory)
                if not os.path.exists(full_path_dest):
                    try:
                        logger.debug('... creating "%s".' % full_path_dest)
                        os.makedirs(full_path_dest)
                    except Exception, e:
                        msg = 'ERROR: when creating "%s" to "%s"' % (full_path_dest, str(e))
                        logger.critical(msg)
                        raise Exception(msg)

                elif not os.path.isdir(full_path_dest):
                    msg = 'ERROR: "%s" exists but is not a directory'
                    logger.critical(msg)
                    raise Exception(msg)


    def _extra_cleanups(self):
        """
        Some extra cleanups in the virtualenv...
        """
        extra_cleanups = self.options.get('extra-cleanups', None)
        if extra_cleanups:
            logger.debug('Performing extra cleanups.')
            for cleanup_pattern in _lst_from_cfg(extra_cleanups):
                for cleanup_file in glob.glob(self._virtualenv_path(cleanup_pattern)):
                    logger.debug('... removing "%s".' % cleanup_file)
                    if os.path.isdir(cleanup_file):
                        shutil.rmtree(cleanup_file, ignore_errors = True)
                    else:
                        try:
                            os.remove(cleanup_file)
                        except IOError, e:
                            logger.error('ERROR: could not remove "%s": %s' % (cleanup_file, str(e)))


    def _prepare_venv(self):
        """
        Finish the virtualenv by making it relocatable and removing some extra things we do not need...
        """

        virtualenv = [
            'virtualenv',
            '--relocatable',
            self.virtualenv_dir,
            ]

        logger.info('Making virtualenv relocatable with "%s".' % (" ".join(virtualenv)))
        job = subprocess.Popen(virtualenv,
                               stdout = subprocess.PIPE,
                               stderr = subprocess.STDOUT)
        stdout, _ = job.communicate()

        if job.returncode != 0:
            logger.critical('ERROR: could not run "virtualenv".')
            sys.exit(1)

        local_dir = os.path.join(self.virtualenv_dir, "local")
        if os.path.exists(local_dir):
            logger.debug('Removing "%s".' % local_dir)
            shutil.rmtree(local_dir)



    def _create_tar (self, filename, compress = False):
        """
        Create a tar file from the virtualenv
        """
        logger.info('Creating tar file from the virtualenv.')
        import tarfile
        with tarfile.open(filename, 'w' if not compress else 'w:gz', dereference = True) as t:
            for name in glob.glob(os.path.join(self.buildroot, '*')):
                rel_name = '/' + os.path.relpath(name, self.buildroot)
                t.add(name, arcname = rel_name)

        if compress:
            output = os.path.join(filename + ".gz")
        else:
            output = filename

        logger.debug('... output: %s.' % output)
        return output


    ################################################################################

if __name__ == '__main__':
    f = Frozen()



