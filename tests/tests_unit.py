import os
from os.path import dirname, abspath
import sys

sys.path.insert(0, dirname(dirname(abspath(__file__))))

from unittest import TestCase
from copiste.sql import *
from copiste.models import SQLModel
from copiste.functions import *
import sys

import tempfile
import shutil




class SQLTests(TestCase):
    def test_instanciations_one_field(self):
        j = Join('a_table', [('field1', 'field2')])
        self.assertEqual(j.sql(), 'JOIN a_table ON field1 = field2')

    def test_instanciations_multiple_fields(self):
        j = Join('a_table', [('field1', 'field2'), ('field3', 'field4')])
        self.assertEqual(j.sql(),
                         'JOIN a_table ON field1 = field2 AND field3 = field4')

    def test_instanciations_no_fields(self):
        with self.assertRaises(ValueError):
            j = Join('a_table', [])

class SQLModelsTest(TestCase):
    def test_instanciation_no_pk(self):
        sm = SQLModel('table')
        self.assertEqual(sm.key, 'id')

class TestSettings(TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.d)

    def testSettingsImport(self):
        os.chdir(self.d)
        settings_f = open('settings.py', 'w')
        settings_f.write("FOO_VAR = 42\n")
        settings_f.close()
        from copiste.settings import SETTINGS
        self.assertEqual(SETTINGS.FOO_VAR, 42)

    def testSettingsInEnviron(self):
        os.chdir(self.d)
        os.environ['COPISTE_SETTINGS_MODULE'] = 'settingsfoo'
        settings_f = open('settingsfoo.py', 'w')
        settings_f.write("FOO_VAR = 42\n")
        settings_f.close()
        from copiste.settings import SETTINGS
        self.assertEqual(SETTINGS.FOO_VAR, 42)


class TestFunctions(TestCase):
    def test_plpythonfunction_sql_install(self):
        ppf = PlPythonFunction()
        expected = """
        CREATE FUNCTION copiste__plpythonfunction(pyargs_marshalled text)
          import copiste
          import marshall
          marshall.loads(pyargs_marshalled)
          f = copiste.functions.PlPythonFunction(**pyargs)
          return f.call(TD)
        RETURNS TRIGGER
        AS $$
        $$ LANGUAGE plpythonu;
        """
        self.assertEqual(ppf.sql_install(), expected)

    def test_plpythonfunction_sql_uninstall(self):
        ppf = PlPythonFunction()
        expected = 'DROP FUNCTION copiste__plpythonfunction;'
        self.assertEqual(ppf.sql_uninstall(), expected)



class TestTrigger(TestCase):
    def test_writetrigger_enable(self):
        fooarg = [1,2,3]

        t = WriteTrigger('unittest_table', 'unittest_trigger')
        expected = "CREATE TRIGGER copiste__unittest_trigger BEFORE INSERT "+\
            "OR UPDATE OR DELETE ON unittest_table FOR EACH ROW "+\
            "EXECUTE PROCEDURE copiste__unittest_func('{}');".format(
            '{t\x03\x00\x00\x00foo[\x03\x00\x00\x00i\x01\x00\x00\x00i\x02\x00\x00\x00i\x03\x00\x00\x000')
        got = t.sql_enable('copiste__unittest_func', args={'foo': fooarg})
        self.assertEqual(expected, got)

