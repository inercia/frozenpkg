

import os
import sys
import shutil
import logging
import glob

import subprocess



import logging
logger = logging.getLogger(__name__)



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

    ############################################################################


    def _create_venv(self, root_dir):
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
            root_dir,
            ]

        logger.debug('Launching "%s"' % (" ".join(virtualenv)))
        job = subprocess.Popen(virtualenv,
                               stdout = subprocess.PIPE,
                               stderr = subprocess.STDOUT)
        stdout, _ = job.communicate()

        if job.returncode != 0:
            logger.critical('could not run virtualenv')
            sys.exit(1)


    def _copy_eggs (self, root_dir):
        """
        Copy all the required eggs to the virtualenv
        """
        bin_dir = os.path.join(root_dir, 'bin')

        easy_install = os.path.join(bin_dir, 'easy_install')
        if not os.path.exists(easy_install):
            logger.critical('could not find easy_install at %s' % easy_install )
            sys.exit(1)

        logger.debug('Copying eggs')
        eggs_dir = os.path.join(self.buildout['buildout']['directory'], 'eggs')
        for egg in glob.glob(os.path.join(eggs_dir, '*.egg')):
            logger.debug('... copying "%s"' % egg)
            command = [easy_install, '--no-deps', egg]
            job = subprocess.Popen(command, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
            stdout, _ = job.communicate()

            if job.returncode != 0:
                logger.critical('could run easy_install: %s' % stdout)
                raise Exception(stdout)

    def _copy_outputs(self, root_dir):
        """
        Copies the outputs from parts
        :param root_dir: the root directory where to copy things
        """
        buildout_dir = self.buildout['buildout']['directory']
        for part in self.buildout['buildout']['parts'].split():
            try:
                outputs = self.buildout[part]['output']
                for output in outputs.splitlines():
                    rel_dir = os.path.relpath(output, buildout_dir)
                    dest_dir = os.path.join(root_dir, os.path.dirname(rel_dir))

                    logger.debug('Copying %s -> %s' % (rel_dir, dest_dir))
                    if not os.path.exists(dest_dir):
                        os.makedirs(dest_dir)
                    shutil.copy2(output, dest_dir)

            except KeyError:
                pass


    def _copy_extra_files (self, root_dir, install_prefix):
        """
        Copy any extra files, from the 'extra' options in the buildout
        :param root_dir: the root directory where to copy things
        """
        assert (root_dir != None and len(root_dir) > 0)
        assert (install_prefix != None and len(install_prefix) > 0)

        pythonpath = []

        buildroot = os.path.normpath(os.path.join(root_dir, install_prefix))
        buildout_dir = self.buildout['buildout']['directory']

        extra_copies = [
            r.strip()
            for r in self.options.get('extra-copies', self.name).split('\n')
            if r.strip()]

        for copy_line in extra_copies:
            try:
                src, dest = [b.strip() for b in copy_line.split("->")]
            except Exception, e:
                print "ERROR: malformed copy specification", e
                return pythonpath

            if not os.path.isabs(src):
                src = os.path.join(buildout_dir, src)

            full_path_dest = os.path.normpath(os.path.join(buildroot, dest))
            for src_el in glob.glob(src):
                logger.debug('Copying %s' % src_el)
                try:
                    if os.path.isdir(src_el):
                        shutil.copytree(src_el, full_path_dest)
                    else:
                        # maybe the destination is a directory: then we have to
                        # create it at the target too...
                        if dest.endswith('/') and not os.path.exists(full_path_dest):
                            logger.debug('... creating %s directory' % dest)
                            os.makedirs(full_path_dest)

                        shutil.copy(src_el, full_path_dest)

                except Exception, e:
                    logger.debug('ERROR: when copying %s to %s' % (src_el, full_path_dest))

        return pythonpath


    def _prepare_venv(self, root_dir):
        """
        Finish the virtualenv by making it relocatable and removing some extra things we do not need...
        """

        virtualenv = [
            'virtualenv',
            '--relocatable',
            root_dir,
            ]

        logger.debug('Launching "%s"' % (" ".join(virtualenv)))
        job = subprocess.Popen(virtualenv,
                               stdout = subprocess.PIPE,
                               stderr = subprocess.STDOUT)
        stdout, _ = job.communicate()

        if job.returncode != 0:
            logger.critical('could not run virtualenv')
            sys.exit(1)

        local_dir = os.path.join(root_dir, "local")
        logger.debug('Removing"%s"' % local_dir)
        shutil.rmtree(local_dir)


    def _create_tar (self, root_dir, filename, compress = False):
        """
        Create a tar file from the virtualenv
        """
        import tarfile
        with tarfile.open(filename, 'w' if not compress else 'w:gz', dereference = True) as t:
            for name in glob.glob(os.path.join(root_dir, '*')):
                rel_name = '/' + os.path.relpath(name, root_dir)
                t.add(name, arcname = rel_name)

        if compress:
            return os.path.join(filename + ".gz")
        else:
            return filename


################################################################################

if __name__ == '__main__':
    f = Frozen()



