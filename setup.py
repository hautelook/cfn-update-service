#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name = "cfnupdateservice",
    version = "1.0.0",
    packages = find_packages('src'),
    package_dir = { '': 'src'},
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
