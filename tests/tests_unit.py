import os
from os.path import dirname, abspath
import sys

# insert the name of
sys.path.insert(0, dirname(dirname(abspath(__file__))))

from unittest import TestCase
from copiste.sql import *
from copiste.models import SQLModel
from copiste.functions.base import *
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
        self.prevdir = os.getcwd()

    def tearDown(self):
        os.chdir(self.prevdir)
        shutil.rmtree(self.d)

    def testSettingsImport(self):
        os.chdir(self.d)
        settings_f = open('settings.py', 'w')
        settings_f.write("FOO_VAR = 42\n")
        settings_f.close()
        sys.path.insert(0, self.d)
        try:
            # delete module if it exists
            del(sys.modules['copiste.settings'])
        except KeyError:
            pass
        from copiste.settings import SETTINGS
        sys.path.pop()
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
CREATE FUNCTION {funcname}()
RETURNS TRIGGER
AS
$$
  import copiste
  import copiste.functions.base
  import marshal
  sql_pyargs = "SELECT data FROM copiste_pyargs WHERE funcname = '{funcname}'"
  pyargs_marshalled = plpy.execute(sql_pyargs)[0]['data']
  pyargs = marshal.loads(pyargs_marshalled.decode('base64'))
  f = copiste.functions.base.PlPythonFunction(**pyargs)
  return f.call(TD, plpy)
$$
LANGUAGE plpythonu;
        """.format(funcname = 'copiste__plpythonfunction__'+ppf.uuid)

        self.assertEqual(ppf.sql_install(), expected)

    def test_plpythonfunction_sql_uninstall(self):
        ppf = PlPythonFunction()
        expected = 'DROP FUNCTION copiste__plpythonfunction__{}()'.format(
            ppf.uuid
        )
        self.assertEqual(ppf.sql_uninstall(), expected)

    def test_plpythonfunction_sql_insert_args(self):
        ppf = PlPythonFunction()
        expected ="""
INSERT INTO copiste_pyargs(funcname, data) VALUES('{}', '{}');
""".format('copiste__plpythonfunction__'+ppf.uuid, 'ezA='  )
        self.assertEqual(ppf.sql_insert_args(), expected)


    def test_plpythonfunction_sql_install_init(self):
        ppf = PlPythonFunction()
        expected = """
CREATE FUNCTION copiste__tmpinit__plpythonfunction__{uuid}(new unittest_table)
RETURNS void
AS
$$
  import copiste
  import copiste.functions.base
  import marshal
  sql_pyargs = "SELECT data FROM copiste_pyargs WHERE funcname = 'copiste__plpythonfunction__{uuid}'"
  pyargs_marshalled = plpy.execute(sql_pyargs)[0]['data']
  pyargs = marshal.loads(pyargs_marshalled.decode('base64'))
  f = copiste.functions.base.PlPythonFunction(**pyargs)
  f.call({{'new': new, 'event': 'INSERT'}}, plpy)
$$
LANGUAGE plpythonu;
        """.format(uuid=ppf.uuid)
        self.assertEqual(ppf.sql_install_init(table='unittest_table'), expected)


    def test_plpythonfunction_sql_uninstall_init(self):
        ppf = PlPythonFunction()
        expected = 'DROP FUNCTION copiste__tmpinit__plpythonfunction__{}(new unittest_table)'.format(
            ppf.uuid
        )
        self.assertEqual(ppf.sql_uninstall_init('unittest_table'), expected)


class TestTrigger(TestCase):
    def test_writetrigger_enable(self):
        fooarg = [1,2,3]

        t = WriteTrigger('unittest_table', 'unittest_trigger')
        expected = "CREATE TRIGGER copiste__unittest_trigger BEFORE INSERT "+\
            "OR UPDATE OR DELETE ON unittest_table FOR EACH ROW "+\
            "EXECUTE PROCEDURE copiste__unittest_func();"
        got = t.sql_enable('copiste__unittest_func', args={'foo': fooarg})
        self.assertEqual(expected, got)


from copiste.ldapsync import LDAPUtils

class TestLDAPUtils(TestCase):
    def test_build_AND_filter_multi(self):
        d = {'foo': 'bar', 'spam': 'egg'}
        expected_filter = '&((foo=bar)(spam=egg))'

        self.assertEqual(LDAPUtils.build_AND_filter(d), expected_filter)

    def test_build_AND_filter_single(self):
        d = {'foo': 'bar'}
        expected_filter = '(foo=bar)'

        self.assertEqual(LDAPUtils.build_AND_filter(d), expected_filter)

    def test_build_AND_filter_empty(self):
        d = {}
        expected_filter = ''

        self.assertEqual(LDAPUtils.build_AND_filter(d), expected_filter)
