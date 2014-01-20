import os

from unittest import TestCase
import subprocess
import random

os.environ['COPISTE_SETTINGS_MODULE'] = 'tests.settings_testenv'
from copiste.settings import SETTINGS
del os.environ['COPISTE_SETTINGS_MODULE']

import psycopg2
import copiste
import copiste.sql
import copiste.functions.base
import copiste.binding

def randomstring():
    return '%030x' % random.randrange(16**30)

class TestServerConnection(TestCase):
    def setUp(self):
        con = psycopg2.connect(**SETTINGS.DB)
        self.cur = con.cursor()

    def test_login(self):
        self.cur.execute('SELECT version()')
        self.assertIn('PostgreSQL', self.cur.fetchone()[0])

class AbstractPgEnviron(TestCase):
    def setUp(self):
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
        self.cur.execute('CREATE TABLE unittest_table (id INT, mail VARCHAR(100))')

    def tearDown(self):
        self.con.close()
        self.management_cur.execute('DROP DATABASE {}'.format(self.dbname))
        self.management_con.close()


class TestServerBehaviour(AbstractPgEnviron):
    def test_install_plpythonu(self):
        self.cur.execute('CREATE LANGUAGE plpythonu')

class TestBinding(AbstractPgEnviron):
    def test_log_action(self):
        msg = 'unittest_'+randomstring()
        self.cur.execute('CREATE LANGUAGE plpythonu')


        logwarn_func = copiste.functions.base.LogWarn(message=msg)

        trigger = copiste.sql.WriteTrigger(
            'unittest_table', logwarn_func.func_name())
        bind = copiste.binding.Bind(trigger, logwarn_func)
        bind.install(self.con)

        # this command is supposed to trigger the trigger
        self.cur.execute("INSERT INTO unittest_table VALUES (1, '42')")
        log_path = "/var/log/postgresql/postgresql-9.1-main.log"
        log_cmd = 'vagrant ssh -c "tail {}"'.format(log_path)
        log_result = subprocess.Popen(
            log_cmd, shell=True, stdout=subprocess.PIPE).stdout.read()
        self.assertIn(msg, log_result)

    def test_exception_cancels_sql_op(self):
        """ If sowething goes wrong, we want, for data consistency sake, to write
        nothing into the db.
        """
        self.cur.execute('CREATE LANGUAGE plpythonu')

        logwarn_func = copiste.functions.base.LogWarn(message='unittest')
        del logwarn_func.args['message']

        trigger = copiste.sql.WriteTrigger(
            'unittest_table', logwarn_func.func_name())
        bind = copiste.binding.Bind(trigger, logwarn_func)
        bind.install(self.con)

        # this command is supposed to trigger the trigger
        self.con.commit()
        with self.assertRaises(Exception):
            self.cur.execute("INSERT INTO unittest_table VALUES (1, '42')")

        self.con.commit()

        self.cur.execute("SELECT * FROM unittest_table")

        self.assertEqual(self.cur.rowcount, 0)

    def test_log_action_uninstall(self):
        msg = 'unittest_'+randomstring()
        self.cur.execute('CREATE LANGUAGE plpythonu')
        self.con.commit()

        logwarn_func = copiste.functions.base.LogWarn(message=msg)

        trigger = copiste.sql.WriteTrigger(
            'unittest_table', 'warn_on_write')
        bind = copiste.binding.Bind(trigger, logwarn_func)

        # Cannot uninstall a not installed function
        with self.assertRaises(psycopg2.ProgrammingError):
            bind.uninstall(self.con)
        self.con.commit()

        bind.install(self.con)
        # this time it should succeed
        bind.uninstall(self.con)

        # the trigger should not be triggered
        self.cur.execute("INSERT INTO unittest_table VALUES (1, '42')")
        log_path = "/var/log/postgresql/postgresql-9.1-main.log"
        log_cmd = 'vagrant ssh -c "tail {}"'.format(log_path)
        log_result = subprocess.Popen(
            log_cmd, shell=True, stdout=subprocess.PIPE).stdout.read()
        self.assertNotIn(msg, log_result)


    def test_log_action_initial_sync(self):
        msg = 'unittest_'+randomstring()
        self.cur.execute('CREATE LANGUAGE plpythonu')

        # 3 values
        self.cur.execute("INSERT INTO unittest_table VALUES (1, '42')")
        self.cur.execute("INSERT INTO unittest_table VALUES (1, '42')")
        self.cur.execute("INSERT INTO unittest_table VALUES (1, '42')")
        self.con.commit()
        logwarn_func = copiste.functions.base.LogWarn(message=msg)

        trigger = copiste.sql.WriteTrigger(
            'unittest_table', logwarn_func.func_name())
        bind = copiste.binding.Bind(trigger, logwarn_func)
        bind.install(self.con)
        bind.initial_sync(self.con)

        # this command is supposed to trigger the trigger
        log_path = "/var/log/postgresql/postgresql-9.1-main.log"
        log_cmd = 'vagrant ssh -c "tail {}"'.format(log_path)
        log_result = subprocess.Popen(
            log_cmd, shell=True, stdout=subprocess.PIPE).stdout.read()
        self.assertEqual(log_result.count(msg), 3)


    def test_log_action_initial_sync_data_ok(self):
        """ This one checks that the data is passed correctly to the function
        """
        msg = 'unittest_'+randomstring()
        self.cur.execute('CREATE LANGUAGE plpythonu')

        # 3 values
        self.cur.execute("INSERT INTO unittest_table VALUES (1, '42object')")
        self.cur.execute("INSERT INTO unittest_table VALUES (1, '43object')")
        self.cur.execute("INSERT INTO unittest_table VALUES (1, '44object')")
        self.con.commit()
        logwarn_func = copiste.functions.base.DebugParams(message=msg)

        trigger = copiste.sql.WriteTrigger(
            'unittest_table', logwarn_func.func_name())
        bind = copiste.binding.Bind(trigger, logwarn_func)
        bind.install(self.con)
        bind.initial_sync(self.con)

        # this command is supposed to trigger the trigger
        log_path = "/var/log/postgresql/postgresql-9.1-main.log"
        log_cmd = 'vagrant ssh -c "tail {}"'.format(log_path)
        log_result = subprocess.Popen(
            log_cmd, shell=True, stdout=subprocess.PIPE).stdout.read()
        self.assertEqual(log_result.count(msg), 3)
        self.assertIn('42object', log_result)
        self.assertIn('43object', log_result)
        self.assertIn('44object', log_result)




class TestFunctions(AbstractPgEnviron):
    def test_register_two_occurences(self):
        self.cur.execute('CREATE LANGUAGE plpythonu')
        func1 = copiste.functions.base.LogWarn(message='msg1')
        func2 = copiste.functions.base.LogWarn(message='msg1')

        self.cur.execute(func1.sql_install())
        self.cur.execute(func2.sql_install())
