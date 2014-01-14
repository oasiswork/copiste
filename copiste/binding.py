from copiste.settings import SETTINGS

class Bind:
    """ A bind is an association between a trigger and a function.
    """
    def __init__(self, trigger, function, connection):
        self.trigger = trigger
        self.function = function
        self.settings = SETTINGS
        self.con = connection

    def install(self):
        """Store the trigger and the function inside the db"""
        cur = self.con.cursor()
        pg_funcname = self.function.func_name()
        cur.execute(self.function.sql_install())
        cur.execute(self.trigger.sql_enable(pg_funcname))

    def uninstall(self):
        """Remove the trigger and the function from the db"""
        cur = self.con.cursor()
        cur.execute(self.trigger.sql_disable())
        cur.execute(self.function.sql_uninstall())


