import os
os.environ['COPISTE_SETTINGS_MODULE'] = 'tests.settings_testenv'

from unittest import TestCase
import subprocess

import psycopg2
import copiste
import copiste.sql
import copiste.functions
import copiste.binding


class TestServerConnection(TestCase):
    def setUp(self):
        from copiste.settings import SETTINGS
        con = psycopg2.connect(**SETTINGS.DB)
        self.cur = con.cursor()

    def test_login(self):
        self.cur.execute('SELECT version()')
        self.assertIn('PostgreSQL', self.cur.fetchone()[0])


class AbstractPgEnviron(TestCase):
    def setUp(self):
        from copiste.settings import SETTINGS

        self.dbname = 'unittest'

        management_con = psycopg2.connect(**SETTINGS.DB)
        management_con.set_isolation_level(0)
        management_cur = management_con.cursor()
        management_cur.execute('CREATE DATABASE '+self.dbname)

        self.management_con = management_con
        self.management_cur = management_cur

        db_settings = SETTINGS.DB.copy()
        db_settings['database'] = self.dbname
        self.con = psycopg2.connect(**db_settings)
        self.cur = self.con.cursor()
        self.cur.execute('CREATE TABLE unittest_table (id INT, data VARCHAR(100))')

    def tearDown(self):
        self.con.close()
        self.management_cur.execute('DROP DATABASE {}'.format(self.dbname))
        self.management_con.close()


class TestServerBehaviour(AbstractPgEnviron):
    def test_install_plpythonu(self):
        self.cur.execute('CREATE LANGUAGE plpythonu')

class TestBinding(AbstractPgEnviron):
    def test_log_action(self):
        msg = 'unittest message'
        self.cur.execute('CREATE LANGUAGE plpythonu')

        trigger = copiste.sql.WriteTrigger('unittest_table', 'logwarn_unittest')
        logwarn_func = copiste.functions.LogWarn(message=msg)
        bind = copiste.binding.Bind(trigger, logwarn_func, self.con)
        bind.install()

        # this command is supposed to trigger the trigger
        self.cur.execute("INSERT INTO unittest_table VALUES (1, '42')")
        log_path = "/var/log/postgresql/postgresql-9.1-main.log"
        log_cmd = 'vagrant ssh -c "tail {}"'.format(log_path)
        log_result = subprocess.Popen(
            log_cmd, shell=True, stdout=subprocess.PIPE).stdout.read()
        self.assertIn(msg, log_result)
