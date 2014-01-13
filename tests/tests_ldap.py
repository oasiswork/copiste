import ldap
import ldap.modlist
import unittest

def ldap_recursive_delete_s(con, base_dn):
    search = con.search_s(base_dn, ldap.SCOPE_SUBTREE)
    delete_list = [dn for dn, _ in search]
    delete_list.reverse()

    for dn in delete_list:
        con.delete_s(dn)

class LDAPSampleData:
    @staticmethod
    def create(c):
        jdoe = {
            'objectClass': ['inetOrgPerson', 'top'],
            'cn': 'jdoe',
            'givenname' : 'Jane',
            'cn': 'Jane Doe',
            'telephonenumber': '+1 408 555 9445',
            'sn': 'Barnes'
        }

        ou_users = {
            'objectclass': ['organizationalUnit', 'top'],
            'ou': 'users'
        }


        base = {
            'objectclass': ['organization', 'top', 'dcObject'],
            'dc': 'foo',
            'o': 'foo.bar'
        }
        c.add_s('dc=foo,dc=bar', ldap.modlist.addModlist(base))
        c.add_s('ou=users,dc=foo,dc=bar', ldap.modlist.addModlist(ou_users))
        c.add_s('cn=jdoe,ou=users,dc=foo,dc=bar', ldap.modlist.addModlist(jdoe))

    @staticmethod
    def delete(c):
        ldap_recursive_delete_s(c, 'dc=foo,dc=bar')


class LDAPServer(unittest.TestCase):
    def test_serverok(self):
        c = ldap.initialize('ldap://localhost:3389')
        c.simple_bind_s('cn=admin,dc=foo,dc=bar', 'password')

    def test_add_delete(self):
        c = ldap.initialize('ldap://localhost:3389')
        c.simple_bind_s('cn=admin,dc=foo,dc=bar', 'password')
        LDAPSampleData.create(c)
        LDAPSampleData.delete(c)
