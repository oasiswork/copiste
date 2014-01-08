from copiste.settings import SETTINGS

class Bind:
    def __init__(self, trigger, function, connection):
        self.trigger = trigger
        self.function = function
        self.settings = SETTINGS
        self.con = connection

    def install(self):
        cur = self.con.cursor()
        pg_funcname = self.function.func_name()
        cur.execute(self.function.sql_install())
        cur.execute(self.trigger.sql_enable(pg_funcname))

    def uninstall(self):
        cur = self.con.cursor()
        cur.execute(self.trigger.sql_disable())
        cur.execute(self.function.sql_uninstall())
