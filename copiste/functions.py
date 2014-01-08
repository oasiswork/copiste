import inspect
import marshal
import uuid

class PlPythonFunction:
    def __init__(self, **kwargs):
        self.args = kwargs

        # builds a uuid withou '-' sign which is forbidden in SQL functions names
        self.uuid = ''
        for f in uuid.uuid4().fields:
            self.uuid += str(f)

    def func_name(self):
        class_name = self.__class__.__name__
        return 'copiste__{}__{}'.format(class_name.lower(), self.uuid)

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
        return 'DROP FUNCTION {}()'.format(self.func_name())

class Copy(PlPythonFunction):
    def __init__(self, sql_table, attr_map):
        self.attr_map = attr_map
        self.sql_table = sql_table
    #TODO


class LogWarn(PlPythonFunction):
    def call(self, TD, plpy):
        plpy.warning(self.args['message'])
