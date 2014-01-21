
class Bind:
    """ A bind is an association between a trigger and a function.
    """
    def __init__(self, trigger, function):
        self.trigger = trigger
        self.function = function

    def install(self, con):
        """Store the trigger and the function inside the db"""
        cur = con.cursor()
        pg_funcname = self.function.func_name()
        cur.execute(self.function.sql_create_pyargs_table())
        cur.execute(self.function.sql_insert_args())
        cur.execute(self.function.sql_install())
        cur.execute(self.trigger.sql_enable(pg_funcname))

    def uninstall(self, con):
        """Remove the trigger and the function from the db"""
        cur = con.cursor()
        cur.execute(self.trigger.sql_disable())
        cur.execute(self.function.sql_uninstall())
        cur.execute(self.function.sql_remove_args())

    def initial_sync(self, con):
        cur = con.cursor()
        cur.execute(self.function.sql_install_init(self.trigger.table))
        cur.execute('SELECT * FROM {}'.format(self.trigger.table))
        for row in cur.fetchall():
            cur.callproc(self.function.init_func_name(), [row])

        cur.execute(self.function.sql_uninstall_init(self.trigger.table))
