#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name = "cfnupdateservice",
    version = "1.0.0",
    packages = find_packages('src'),
    package_dir = { '': 'src'},
    author = "Naftuli Tzvi Kay",
    author_email = "rfkrocktk@gmail.com",
    url = "https://github.com/hautelook/cfn-update-service",
    setup_requires=['setuptools-markdown'],
    long_description_markdown_filename='README.md',
    install_requires = [
        'setuptools',
    ],
    dependency_links = [
        'https://s3.amazonaws.com/cloudformation-examples/aws-cfn-bootstrap-latest.tar.gz',
    ],
    entry_points = {
        'console_scripts': [
            'cfn-update-service = cfnupdateservice:main'
        ]
    }
)
