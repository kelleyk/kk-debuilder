#!/usr/bin/env python3.4
""".

gbp buildpackage --git-debian-branch=master --git-upstream-branch=upstream --git-no-ignore-branch --git-no-submodules --git-postexport='/home/kelleyk/repos/docker-debuild/changelog_modifier/rewrite-in-place.sh debian/changelog utopic +14.10' --git-export-dir=../compton-build --git-purge --git-no-overlay --git-verbose --git-force-create --git-builder=/home/kelleyk/repos/docker-debuild/run-builder.py utopic -- -uc -us -i -I
"""

import os
import os.path
import sys
import shutil
import logging
import argparse
import subprocess

if sys.version_info < (3,):
    from pipes import quote as shell_quote
else:
    from shlex import quote as shell_quote

from six import text_type
    
from . import distro_info
from .util import TemporaryDirectory, realpath

    
class KKDebuilderTool(object):

    BUILD_PRODUCT_SUFFIXES = {
        '.deb',
        '.ddeb',
        '.dsc',
        '.build',
        '.changes',
        '.tar.xz',
        '.tar.bz2',  # should be using xz now
        '.tar.gz',   # should be using xz now
    }
    
    def __init__(self, *args, **kwargs):
        log = kwargs.pop('log', None)
        super(KKDebuilderTool, self).__init__(*args, **kwargs)
        self._log = log or logging.getLogger('kk_debuilder')

        self.verbosity = 0

    def build_parser(self):
        p = argparse.ArgumentParser()

        g_trouble = p.add_argument_group('troubleshooting')
        g_trouble.add_argument('--dry-run', action='store_true',
                               help='Print information about what would happen, but do nothing.')
        # The default const is None, which is fine; we just care about the length.
        g_trouble.add_argument('-v', '--verbose', action='append_const', const=None, dest='verbose',
                               help='Enable more detailed output.  May be specified a second time for debug-level output.')
        g_trouble.add_argument('--verbose-gbp', action='store_true',
                               help='Make git-buildpackage verbose, too.  (Enabled by default with -vv.)')
        g_trouble.add_argument('--no-remove-container', action='store_false', dest='remove_container',
                               help='Do not automatically remove the container after the build ends.')
        # TODO: Add an option that lets us skip removing the usually-temporary build directory.

        g_build = p.add_argument_group('build configuration')
        g_build.add_argument('--source-only', action='store_true',
                             help='Build only source packages; do not build binary packages.  (This option is '
                             'appropriate for preparing packages to be uploaded to Launchpad.)')
        g_build.add_argument('--no-check', action='store_false', dest='check',
                             help='Skip running Debian tests.  (This option sets DEB_BUILD_OPTIONS=nocheck.)')
        
        g_path = p.add_argument_group('path selection')
        g_path.add_argument('--repo', '--repository', metavar='path', action='store', dest='repository',
                            help='Path to git repository from which packages will be built.'
                            '  Default is to use the current working directory.')
        g_path.add_argument('--tmp-path', metavar='path', action='store',
                            help='Path in which a temporary directory will be created for each build.  If not given, '
                            'the default system location (e.g. /tmp) is used.')
        g_path.add_argument('--output-path', metavar='path', action='store',
                            help='Path where successfully-built artifacts will be left.  By default, the parent of the'
                            ' working directory will be used.')

        g_branch = p.add_argument_group('branch selection')
        g_branch.add_argument('--upstream-branch', action='store', metavar='branch-name', default='upstream',
                              help='The branch that will be treated as the "upstream version" from the point of view of '
                              'the Debian packaging tools.')
        g_branch.add_argument('--debian-branch', action='store', metavar='branch-name', default='master',
                              help='The branch containing the Debianized and packaged version of the software.  This is '
                              'usually the --upstream-branch with packaging information (i.e., the debian/ subdirectory) added.')

        g_target = p.add_argument_group('target selection')
        g_target.add_argument('--target', action='append', dest='target_suites',
                              help='Manually add one or more suites to the list of targets.'
                              '  May be given multiple times or with a comma-separated list.')
        g_target.add_argument('--no-target', metavar='suite(s)', action='append', dest='untarget_suites',
                              help='Manually exclude one or more suites from the list of targets.  (This option overrides '
                              'any inclusive options.)  May be given multiple times or with a comma-separated list.')
        g_target.add_argument('--all-supported', action='store_true',
                              help='Add any released suite that has not reached EOL (and server EOL, if different) '
                              'to the list of targets.')
        g_target.add_argument('--all-since', action='store', metavar='suite-name',
                              help='Add the given suite and any later, released suites to the list of targets.')
        g_target.add_argument('--all-unreleased', action='store_true',
                              help='Add all not-yet-released suites to the list of targets.')
        g_target.add_argument('--allow-no-targets', action='store_true',
                              help='If no target(s) are selected, do not treat the situation as an error.')

        g_aptproxy = p.add_argument_group('package management')
        g_aptproxy.add_argument('--apt-proxy', metavar='proxy-url', action='store', default=None, dest='apt_proxy',
                                help='Explicitly specify the URL of an apt proxy that should be used, such as '
                                '"http://10.0.0.1:3142/".  If not given, the default behavior is to use the '
                                'host\'s apt proxy configuration.  (This option is passed through to docker-debuild.)')
        g_aptproxy.add_argument('--no-apt-proxy', action='store_const', const=False, dest='apt_proxy',
                                help='Prevent the use of any apt proxy.  (This option is passed through to docker-debuild.)')
        
        return p

    def main(self, argv=None):
        argv = argv or sys.argv
        self.args = args = self.build_parser().parse_args(argv[1:])

        self.verbosity = min(2, len(self.args.verbose or ()))
        if self.verbosity > 0:
            level = {1: logging.INFO, 2: logging.DEBUG}[self.verbosity]
            logging.basicConfig(level=level)
            self._log.setLevel(level)
            self._log.debug('Enabled verbose output!')

        self.verbose_gbp = args.verbose_gbp or self.verbosity >= 2
       
        self.suite_info = suite_info = {x.series: x for x in distro_info.get_ubuntu_distro_info()}
        targets = self._parse_target_options(args, suite_info)

        # XXX: Make this check more robust.
        # XXX: Check that the repository is clean, too.
        self.source_repository_path = realpath(args.repository or os.getcwd())
        if not os.path.exists(os.path.join(self.source_repository_path, '.git')):
            raise Exception('Does not appear to be a git repository: {}'.format(self.source_repository_path))

        self.output_path = realpath(args.output_path or os.path.dirname(os.getcwd()))
        if not (os.path.exists(self.output_path) and os.path.isdir(self.output_path)):
            raise Exception('Output path does not exist or is not a directory: {}'.format(self.output_path))

        self.tmp_path = realpath(args.tmp_path)
        
        if args.dry_run:
            self._log.debug('In dry-run mode; stopping here!')
            return

        for target in targets:
            self._build_target(target)

    def _parse_target_options(self, args, suite_info):
        targets = set()
        for x in (args.target_suites or ()):
            targets.update(x.split(','))
        if args.all_supported:
            targets.update(suite.series for suite in suite_info.values()
                           if suite.released and (suite.supported or suite.supported_server))
        if args.all_since:
            release = suite_info[args.all_since].release
            targets.append(args.all_since)
            targets.update(suite.series for suite in suite_info.values()
                           if suite.released and suite.release > release)
        if args.all_unreleased:
            targets.update(suite.series for suite in suite_info.values()
                           if not suite.released)

        for x in (args.untarget_suites or ()):
            targets -= set(x.split(','))

        for target in targets:
            if target not in suite_info:
                raise ValueError('Unknown suite: {}'.format(target))

        if not targets and not args.allow_no_targets:
            raise ValueError('No target(s) selected!')

        self._log.info('Selected targets: ' + ', '.join(sorted(targets)))

        return targets

    def _build_target(self, target_suite):

        # TODO: should have a way to specify a temp dir; if not, use '/tmp'; create subdir int here to use as build_Tmp_path
        
        # TODO: should copy the build products out of there to somewhere more useful (an output dir?  default to cwd?)
        
        # TODO: should let them specify debian_branch and upstream_branch; should also have a way of autodetecting from repository
        
        # TODO: should have a way of specifying debuild_args
        
        # TODO: should, after builds are done, have a command that wraps the signing process

        # TODO: source-only builds (for e.g. launchpad) or binary-and-source builds

        # TODO: should check for suite-specific branches (?)

        # TODO: start passing --git-ignore-branch to make it easier to use multiple branches?

        # TODO: time the build
        
        target_suite_info = self.suite_info[target_suite]
        
        # build_tmp_path = '../compton-build'

        debuild_args = ['-uc', '-us', '-i', '-I']
        version_suffix = '+{}'.format(target_suite_info.numeric_version)

        if self.args.source_only:
            debuild_args.append('-S')
        
        with TemporaryDirectory(dir=self.tmp_path, suffix='.kk-debuilder') as tmpdir:

            self._log.info('Temporary directory for build: {}'.format(tmpdir.pathname))
        
            cmd = ['gbp', 'buildpackage']
            cmd.append('--git-debian-branch={}'.format(self.args.debian_branch))
            cmd.append('--git-upstream-branch={}'.format(self.args.upstream_branch))

            # XXX: @KK 2016.06: Without this option, I believe that --git-upstream-branch is simply ignored in favor of
            # recreating the 'orig' tarball using pristine-tar.
            cmd.append('--git-no-pristine-tar')
            
            cmd.extend((
                '--git-no-ignore-branch',  # (default)
                '--git-no-submodules',     # (default)
                
                # Don't delete the build diretory that we have exported from the git repository; let
                # it be removed along with the temporary directory it's in.  (This makes troubleshooting easier.)
                '--git-no-purge',
                
                '--git-no-overlay',
                '--git-force-create',
            ))
            cmd.append('--git-postexport={}'.format(' '.join(shell_quote(s) for s in (
                # os.path.join(bin_path, 'rewrite-in-place.sh'),
                'kk-debuilder-changelog-rewriter',
                '--inplace',
                '--version-suffix', version_suffix,
                'debian/changelog',
                target_suite,
                ))))

            cmd.append('--git-export-dir={}'.format(tmpdir.pathname))

            if self.verbose_gbp:
                cmd.extend(('--git-verbose',))

            cmd.extend(('--git-builder=docker-debuild',))
            # Any arguments that gbp buildpackage doesn't recognize will be passed to our --git-builder.
            if self.args.apt_proxy is False:
                cmd.append('--no-apt-proxy')
            elif self.args.apt_proxy:
                cmd.append('--apt-proxy={}'.format(self.args.apt_proxy))
            if not self.args.remove_container:
                cmd.append('--no-rm')
            if not self.args.check:
                cmd.append('--env=DEB_BUILD_OPTIONS=nocheck')
            cmd.extend((target_suite, '--'))
            cmd.extend(debuild_args)

            self._log.debug(text_type(cmd))
            try:
                p = subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr)
            except OSError as exc:
                if exc.errno == 2:
                    raise OSError(2, 'No such executable: {}'.format(cmd[0]))
                raise
            p.communicate(sys.stdin)

            products = list(self._collect_build_products(tmpdir.pathname))
            if not self.args.source_only and not any(filepath.endswith('.deb') for filepath in products):
                # XXX: e.g. you will have only the orig tarball and the .build file
                raise Exception('Build seems to have failed; no deb packages were produced!')
            
            self._log.info('Moving build products to output directory...')
            for filepath in products:
                filename = os.path.basename(filepath)
                self._log.info('  - {}'.format(filename))
                shutil.move(filepath, os.path.join(self.output_path, filename))
                
    def _collect_build_products(self, path):
        for name in os.listdir(path):
            if any(name.endswith(suffix) for suffix in self.BUILD_PRODUCT_SUFFIXES):
                yield os.path.join(path, name)
            
        
def main():
    KKDebuilderTool().main()

    
if __name__ == '__main__':
    main()
