# kk-debuilder

## Packaging tool suite

This tool is one of four that I use in my `git-buildpackage`-based workflow for creating, forking, and maintaining
Debian (`.deb`) packages.  These tools were written for personal use and most definitely have rough edges.  Please let
me know if you have trouble!  The four are

- [`kk-debuilder`](https://github.com/kelleyk/kk-debuilder)
- [`docker-debuild`](https://github.com/kelleyk/docker-debuild)
- [my `git-buildpackage` fork](https://github.com/kelleyk/git-buildpackage)
- [`apt-config-tool`](https://github.com/kelleyk/apt-config-tool), and

## Overview

`kk-debuilder` is a workflow tool that wraps both `docker-debuild` and my fork of `git-buildpackage`.  It lets you build packages for several Ubuntu distributions from a single
`git-buildpackage`-style source repository.  Containers are used to sandbox each build and to make cross-distribution builds easy.

## Usage examples

    # The arguments '--upstream-branch=upstream --debian-branch=master' are left out since those are the default values.
    # This will produce binary packages, ready to install.
    $ kk-debuilder --target wily
    # This will produce source packages, ready to sign and upload to Launchpad.
    $ kk-debuilder --target wily --source-only
    # Why stop with just one distribution?
    $ kk-debuilder --all-supported

## Features

- Through `docker-debuild`, automatic detection of (and use of) your caching `apt` proxy.

- Flexible selection of target distributions (see `--help` for details).

## Tips

- Some packages have extensive check suites.  Try `--no-check` to avoid the delay while troubleshooting.

- You must have built `docker-debuild` images for each target distribution.  See the `build.sh` script distributed with
  that tool.

## kk-debuilder-changelog-rewriter

The `debian/changelog` file must include the name of the distribution that the package is for (e.g. `wily`, `vivid`,
`trusty`, ...).  This is a problem if we would like to build packages from the same repository for several distributions
of Ubuntu.

Just leave the changelog distribution `UNRELEASED`, and do not add a distribution-specific suffix to the package's
version number.  `kk-debuilder` will use the changelog rewriter to automatically turn entries like

    compton (0.1~beta3~1.git0e0b35a-kk1) UNRELEASED; urgency=medium

into

    compton (0.1~beta3~1.git0e0b35a-kk1+15.10) wily; urgency=medium
    compton (0.1~beta3~1.git0e0b35a-kk1+15.04) vivid; urgency=medium
    ...

## TODO

- It'd be nice to also support Debian suite names (instead of only Ubuntu ones).
