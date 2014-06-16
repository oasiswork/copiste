import marshal

class Trigger:
    """A SQL trigger"""
    def __init__(self, sql_table, name, moment='BEFORE'):
        self.table = sql_table
        self.name = name
        self.moment = moment

    def sql_disable(self):
        return 'DROP TRIGGER {} ON {}'.format(self.db_name(), self.table)

    def db_name(self):
        return 'copiste__{}'.format(self.name)

class WriteTrigger(Trigger):
    """ Trigger executed on write/update/deletes, row-level
    """
    def sql_enable(self, func_name, args={}):
        """Gives the SQL sentence to enable the SQL trigger

        @param func_name the function to call on trigger activation
        @param args a dictionary with args for the method (if any), those args
               are always the same for each call of this trigger.
        """
        pyargs_marshalled = marshal.dumps(args).encode('base64')

        if not func_name.startswith('copiste__'):
            raise ValueError(
                '"{}" does not seem to be a copiste function'.format(func_name))

        sql = ("CREATE TRIGGER {} {} INSERT OR UPDATE OR DELETE ON {} "+
               "FOR EACH ROW EXECUTE PROCEDURE {}();"
        ).format(self.db_name(), self.moment ,self.table,
                 func_name, pyargs_marshalled)
        return sql
