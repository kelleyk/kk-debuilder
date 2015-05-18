#!/usr/bin/env python3.4
""".

gbp buildpackage --git-debian-branch=master --git-upstream-branch=upstream --git-no-ignore-branch --git-no-submodules --git-postexport='/home/kelleyk/repos/docker-debuild/changelog_modifier/rewrite-in-place.sh debian/changelog utopic +14.10' --git-export-dir=../compton-build --git-purge --git-no-overlay --git-verbose --git-force-create --git-builder=/home/kelleyk/repos/docker-debuild/run-builder.py utopic -- -uc -us -i -I
"""

import os
import os.path
import sys
import argparse
import subprocess
if sys.version_info < (3,):
    from pipes import quote as shell_quote
else:
    from shelx import quote as shell_quote


def build_parser():
    p = argparse.ArgumentParser()
    return p


def main(argv=None):
    argv = argv or sys.argv
    args = build_parser().parse_args(argv[1:])

    # bin_path = '/home/kelleyk/repos/docker-debuild/changelog_modifier'
    build_tmp_path = '../compton-build'
    debian_branch = 'master'
    upstream_branch = 'upstream'
    gbp_debug = True
    debuild_args = ('-uc', '-us', '-i', '-I')
    target_distribution = 'utopic'
    version_suffix = '+14.10'

    cmd = ['gbp', 'buildpackage']
    cmd.append('--git-debian-branch={}'.format(debian_branch))
    cmd.append('--git-upstream-branch={}'.format(upstream_branch))
    cmd.extend((
        '--git-no-ignore-branch',  # (defualt)
        '--git-no-submodules',     # (default)
        '--git-purge',
        '--git-no-overlay',
        '--git-force-create',
    ))
    cmd.append('--git-postexport={}'.format(' '.join(shell_quote(s) for s in (
        # os.path.join(bin_path, 'rewrite-in-place.sh'),
        'kk-debuilder-changelog-rewriter',
        '--version-suffix', version_suffix,
        'debian/changelog',
        target_distribution,
        ))))

    cmd.append('--git-export-dir={}'.format(build_tmp_path))
                
    if gbp_debug:
        cmd.extend(('--git-verbose',))

    cmd.extend(('--git-builder=docker-debuild',))
    # Any arguments that gbp buildpackage doesn't recognize will be passed to our --git-builder.
    cmd.extend((target_distribution, '--'))
    cmd.extend(debuild_args)

    print(cmd)
    p = subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr)
    p.communicate(sys.stdin)


if __name__ == '__main__':
    main()
