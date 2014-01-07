import os
os.environ['COPISTE_SETTINGS_MODULE'] = 'tests.settings_testenv'

from unittest import TestCase
import psycopg2
import copiste


class TestServerConnection(TestCase):
    def setUp(self):
        from copiste.settings import SETTINGS
        con = psycopg2.connect(**SETTINGS.DB)
        self.cur = con.cursor()

    def test_login(self):
        self.cur.execute('SELECT version()')
        self.assertIn('PostgreSQL', self.cur.fetchone()[0])

class TestServerBehaviour(TestCase):
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

    def tearDown(self):
        self.con.close()
        self.management_cur.execute('DROP DATABASE unittest')
        self.management_con.close()

    def test_install_plpythonu(self):
        self.cur.execute('CREATE LANGUAGE plpythonu')




