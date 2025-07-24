#!/usr/bin/env python

from setuptools import setup

setup(
    name='composed_object_analysis',
    version='1.0',
    description='pyCPA composed synchronous analysis extension for large data objects',
    author='Jonas Peeck',
    author_email='peeck@ida.ing.tu-bs.de',
    url='https://github.com/IDA-TUBS/pycpa_composed_object_analysis',
    license='MIT',
    packages= ['composed_object_analysis'],
    install_requires=['pycpa', 'networkx']
)
