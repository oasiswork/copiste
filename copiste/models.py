
class LDAPModel(object):
    def __init__(self, base, query, key='uid'):
        self.base = base
        self.query = query
        self.key = key

