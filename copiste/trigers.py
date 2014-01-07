class AbstractSQLTrigger:
    def __init__(self, table):
        self.table = table

class WriteTrigger(AbstractSQLTrigger):
    requests = ('CREATE', 'UPDATE', 'DELETE')

