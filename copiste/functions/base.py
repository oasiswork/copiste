import inspect
import marshal
import uuid

class PlPythonFunction(object):
    """ An abstract plpython object

    This class handles (un)installation, calling and naming of the stored
    functions.

    One should extend it, overriding call() and optionally __init__()
    """
    def __init__(self, **kwargs):
        self.args = kwargs

        # builds a uuid withou '-' sign which is forbidden in SQL functions names
        self.uuid = ''
        for f in uuid.uuid4().fields:
            self.uuid += str(f)

    def pymodule_name(self):
        return  self.__module__.split('.')[-1]

    def func_name(self):
        """ Generates the func_name used for storage in Postgre.

        This name is prefixed by "copiste__" and contains a random UUID.
        """
        class_name = self.__class__.__name__
        return 'copiste__{}__{}'.format(class_name.lower(), self.uuid)

    def init_func_name(self):
        """ Generates the func_name used for temporary storage of the
        data initialization function

        This name is prefixed by "copiste__" and contains a random UUID.
        """
        class_name = self.__class__.__name__
        return 'copiste__tmpinit__{}__{}'.format(class_name.lower(), self.uuid)


    def _marshalled_args(self):
        return marshal.dumps(self.args).encode('base64').strip()


    def sql_install(self):
        """ Stores the function inside the db. Actually stores only a stub,
        which will call the function. """
        pyargs_marshalled = self._marshalled_args()
        sql = """
CREATE FUNCTION {}()
RETURNS TRIGGER
AS
$$
  import copiste
  import copiste.functions.{}
  import marshal
  pyargs_marshalled = \"""{}\"""
  pyargs = marshal.loads(pyargs_marshalled.decode('base64'))
  f = copiste.functions.{}.{}(**pyargs)
  return f.call(TD, plpy)
$$
LANGUAGE plpythonu;
        """.format(self.func_name(), self.pymodule_name(),
                   pyargs_marshalled, self.pymodule_name(),
                   self.__class__.__name__)
        return sql

    def sql_uninstall(self):
        return 'DROP FUNCTION {}()'.format(self.func_name())

    def sql_install_init(self, table):
        sql = """
CREATE FUNCTION {func_name}(new {table_name})
RETURNS void
AS
$$
  import copiste
  import copiste.functions.{pymodule}
  import marshal
  pyargs_marshalled = \"""{args_data}\"""
  pyargs = marshal.loads(pyargs_marshalled.decode('base64'))
  f = copiste.functions.{pymodule}.{pyfunc_name}(**pyargs)
  f.call({{'new': new}}, plpy)
$$
LANGUAGE plpythonu;
        """.format(
            func_name  = self.init_func_name(),
            args_data  = self._marshalled_args(),
            pyfunc_name= self.__class__.__name__,
            table_name = table,
            pymodule   = self.pymodule_name()
        )
        return sql

    def sql_uninstall_init(self, table):
        return 'DROP FUNCTION {}(new {})'.format(self.init_func_name(), table)


class LogWarn(PlPythonFunction):
    """ Just a functions which prints something in postgres LOG
    """
    def call(self, TD, plpy):
        plpy.warning(self.args['message'])

class DebugParams(PlPythonFunction):
    """ Function that prints to sql log the content of its TD arg and a message
    """
    def call(self, TD, plpy):
        plpy.warning(self.args['message']+' '+str(TD))


