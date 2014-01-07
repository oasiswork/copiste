import marshal

class Join:
    """ A SQL Join"""
    def __init__(self, table, fields):
        """ A SQL Join

        @param table the table to Join
        @param fields a list of couples : fields to join (AND linked)
        """
        if len(fields) <= 0:
            raise ValueError('fields should not be an empty list')

        self.table = table
        self.fields = fields

    def sql(self):
        fields_q = ''
        for field1, field2 in self.fields:
            fields_q += ' {} = {} AND'.format(field1, field2)

        return 'JOIN {} ON{}'.format(self.table, fields_q[:-4])


class Trigger:
    """A SQL trigger"""
    def __init__(self, sql_table, name):
        self.table = sql_table
        self.name = name

    def sql_disable(self):
        return 'DROP TRIGGER {} ON {};'.formato(self.name, self.table)

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
        pyargs_marshalled = marshal.dumps(args)

        if not func_name.startswith('copiste__'):
            raise ValueError(
                '"{}" does not seem to be a copiste function'.format(func_name))

        sql = ("CREATE TRIGGER {} BEFORE INSERT OR UPDATE OR DELETE ON {} "+
               "FOR EACH ROW EXECUTE PROCEDURE {}('{}');"
        ).format(self.db_name(), self.table, func_name, pyargs_marshalled)

        return sql
