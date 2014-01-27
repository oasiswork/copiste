#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from setuptools import setup

README = open(os.path.join(os.path.dirname(__file__), 'README.md')).read()


def mk_version(base_version):
    try:
        GIT_HEAD = open('.git/HEAD').readline().split(':')[1].strip()
        GIT_HEAD_REV = open('.git/{}'.format(GIT_HEAD)).readline().strip()
        return '{}-git-{:.7}'.format(base_version, GIT_HEAD_REV)
    except IOError:
        return base_version

setup(name='copiste',
      version=mk_version('0.1'),
      description='PostgreSQL to LDAP realtime sync tools',
      long_description=README,
      author='Jocelyn Delalande',
      author_email='jdelalande@oasiswork.fr',
      url='https://dev.oasiswork.fr/projects/copiste/',
      packages=['copiste', 'copiste.functions'],
      install_requires=['psycopg2', 'python-ldap'],
      scripts=['bin/copiste']
      )
