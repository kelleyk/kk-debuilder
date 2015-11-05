#!/usr/bin/env python3.4
import sys
import argparse
from io import BytesIO

try:
    import debian.changelog
except ImportError:
    import os.path
    # XXX: Yes, this is horrible; I should just bundle a copy of this module.
    dist_package_path = '/usr/lib/python{}.{}/dist-packages'.format(*sys.version_info[:2])
    if os.path.exists(dist_package_path) and dist_package_path not in sys.path:
        sys.path += [dist_package_path]
        import debian.changelog
    else:
        raise

    
def changelog_to_bytes(ch):
    out = BytesIO()
    ch.write_to_open_file(out)
    return out.getvalue()


class ChangelogRewriter(object):
    def __init__(self, distribution_name, distribution_version=1, which_blocks='first', version_suffix=None):
        assert which_blocks in ('first', 'all', 'unreleased', 'first-or-unreleased')
        self.which_block = which_blocks

        self.distribution_name = distribution_name  # e.g. 'vivid', 'trusty', ...
        self.distribution_version = distribution_version  # i.e. the 1 in '~vivid1'.
        
        self.version_suffix = version_suffix

    def process(self, ch):
        if self.which_block == 'all':
            for block in ch:
                self._process_block(block)
        elif self.which_block == 'first':
            self._process_block(next(iter(ch)))
        elif self.which_block == 'unreleased':
            for block in ch:
                if block.distributions.upper() == 'UNRELEASED':
                    self._process_block(block)
        elif self.which_block == 'first-or-unreleased':
            it = iter(ch)
            self._process_block(next(it))
            for block in it:
                if block.distributions.upper() == 'UNRELEASED':
                    self._process_block(block)
        else:
            raise AssertionError()

    def _process_block(self, block):
        
        block.distributions = self.distribution_name

        if self.version_suffix:
            block.version = '{}{}'.format(block.version, self.version_suffix)
        
        #  'date': 'Tue, 1 Jan 2015 17:00:00 -0700',
        #  'author': 'John Doe <jdoe@gmail.com>',        
        #  'distributions': 'vivid',
        #  'other_pairs': {},
        #  'package': 'mypackage',
        #  'urgency': 'medium',
        #  'urgency_comment': '',


# class ArgumentParser(argparse.ArgumentParser):
#     def add_bool_argument(self, name,
        

def build_parser():
    p = argparse.ArgumentParser()
    p.add_argument('changelog_path', action='store')
    p.add_argument('dist_name', action='store')
    p.add_argument('--which-blocks', action='store', default='first-or-unreleased')
    p.add_argument('--inplace', action='store_true')

    p.add_argument('--version-suffix', action='store', default=None)
    
    # p.add_argument('--rewrite-version', action='store_true', dest='rewrite_version')
    # p.add_argument('--no-rewrite-version', action='store_false', dest='rewrite_version')
    # p.set_defaults(**{'rewrite_version': True})

    return p


def main(argv=None):
    argv = sys.argv if argv is None else argv
    args = build_parser().parse_args(argv[1:])
    
    with open(args.changelog_path, 'r') as f:
        ch = debian.changelog.Changelog(f)

    rewriter = ChangelogRewriter(
        distribution_name=args.dist_name,
        # distribution_version=args.dist_version,
        distribution_version=1,
        which_blocks='first-or-unreleased',
        # rewrite_version=args.rewrite_version,
        version_suffix=args.version_suffix,
        )

    rewriter.process(ch)
    result = changelog_to_bytes(ch)

    if args.inplace:
        with open(args.changelog_path, 'wb') as f:
            f.write(result)
    else:
        print(result.decode('utf-8'))


if __name__ == '__main__':
    main()
    
