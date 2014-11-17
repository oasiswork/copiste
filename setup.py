#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from setuptools import setup

README = open(os.path.join(os.path.dirname(__file__), 'README.md')).read()

setup(name='copiste',
      version='0.2',
      description='PostgreSQL to LDAP realtime sync tools',
      long_description=README,
      author='Jocelyn Delalande',
      author_email='jdelalande@oasiswork.fr',
      url='https://dev.oasiswork.fr/projects/copiste/',
      packages=['copiste', 'copiste.functions'],
      install_requires=['psycopg2', 'python-ldap'],
      scripts=['bin/copiste']
      )
