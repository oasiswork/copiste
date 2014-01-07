class AbstractModel:
    pass

class SQLModel(AbstractModel):
    def __init__(self, table, key='id'):
        self.table = table
        self.key = key

class LDAPModel(AbstractModel):
    def __init__(self, base, query, key='uid'):
        self.base = base
        self.query = query
        self.key = key

