import inspect

class PlPythonFunction:

    @classmethod
    def func_name(cls):
        return 'copiste__{}'.format(cls.__name__.lower())

    def sql_install(self):
        sql = """
        CREATE FUNCTION {}(pyargs_marshalled text)
          import copiste
          import marshall
          marshall.loads(pyargs_marshalled)
          f = copiste.functions.{}(**pyargs)
          return f.call(TD)
        RETURNS TRIGGER
        AS $$
        $$ LANGUAGE plpythonu;
        """.format(self.func_name(), self.__class__.__name__)
        return sql

    def sql_uninstall(self):
        return 'DROP FUNCTION {};'.format(self.func_name())

class Copy(PlPythonFunction):
    def __init__(self, sql_table, attr_map):
        self.attr_map = attr_map
        self.sql_table = sql_table
    #TODO


