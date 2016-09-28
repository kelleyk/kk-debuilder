# -*- encoding: utf-8 -*-

from setuptools import setup, find_packages


setup(
    name='kk-debuilder',
    version='0.0.1',
    description='',
    author='Kevin Kelley',
    author_email='kelleyk@kelleyk.net',
    url='https://github.com/kelleyk/kk-debuilder',
    packages=find_packages(include='kk_debuilder.*'),
    include_package_data=True,
    install_requires=[
        'arrow',
        'six',
        # requires my gbp fork;
        # requires kelleyk/docker-debuild
    ],
    entry_points={
        'console_scripts': [
            'kk-debuilder = kk_debuilder.wrapper:main',
            'kk-debuilder-changelog-rewriter = kk_debuilder.changelog_rewriter:main',
        ],
    },
)
