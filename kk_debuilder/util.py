# -*- encoding: utf-8 -*-
"""Utilities for dealing with the filesystem."""

from __future__ import division, absolute_import, unicode_literals, print_function

import os
import os.path
import stat
import shutil
import tempfile


def realpath(s):
    return os.path.normpath(os.path.expanduser(s))


def pack_mode(mode_str, is_file=False, is_dir=False):
    """Converts a human-readable mode string (e.g., 0644) into a
    bit-packed mode.  The keyword arguments set file type flags."""
    bits = int(mode_str, 8)
    if is_file:
        bits |= stat.S_IFREG
    if is_dir:
        bits |= stat.S_IFDIR
    return bits


class TemporaryDirectory(object):
    """Creates a temporary directory similarly to how
    tempfile.TemporaryFile creates a temporary file."""

    def __init__(self, suffix=None, dir=None):
        self.pathname = tempfile.mkdtemp(suffix=suffix or '', dir=dir)

    # @property
    # def path(self):
    #     return Path(self.pathname)

    @property
    def name(self):
        return os.path.basename(self.pathname)

    def close(self):
        self._clean()

    def _clean(self):
        if not os.path.isdir(self.pathname):
            return

        # Walk the temporary directory, chmodding everything so that
        # it can be modified.
        def chmod_dir(arg, dirname, names):
            for name in names:
                os.chmod(os.path.join(dirname, name), pack_mode('1777'))
        os.walk(self.pathname, chmod_dir, None)

        # Now kill it.
        shutil.rmtree(self.pathname)

    def __enter__(self):
        return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        # N.B.: The arguments to __exit__ describe the exception, if
        # any, that was thrown in the 'with' block.
        self._clean()

    def __del__(self):
        self._clean()

    def __unicode__(self):
        """Returns just the path, so that you can e.g. pass a
        TemporaryDirectory to string.format() or anything else that
        expects a string."""
        return self.pathname
