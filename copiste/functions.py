import inspect
import marshal

class PlPythonFunction:
    def __init__(self, **kwargs):
        self.args = kwargs

    @classmethod
    def func_name(cls):
        return 'copiste__{}'.format(cls.__name__.lower())

    def sql_install(self):
        pyargs_marshalled = marshal.dumps(self.args).encode('base64').strip()
        sql = """
CREATE FUNCTION {}()
RETURNS TRIGGER
AS
$$
  import copiste
  import copiste.functions
  import marshal
  pyargs_marshalled = \"""{}\"""
  pyargs = marshal.loads(pyargs_marshalled.decode('base64'))
  f = copiste.functions.{}(**pyargs)
  return f.call(TD, plpy)
$$
LANGUAGE plpythonu;
        """.format(self.func_name(), pyargs_marshalled, self.__class__.__name__)
        return sql

    def sql_uninstall(self):
        return 'DROP FUNCTION {};'.format(self.func_name())

class Copy(PlPythonFunction):
    def __init__(self, sql_table, attr_map):
        self.attr_map = attr_map
        self.sql_table = sql_table
    #TODO


class LogWarn(PlPythonFunction):
    def call(self, TD, plpy):
        plpy.warning(self.args['message'])
