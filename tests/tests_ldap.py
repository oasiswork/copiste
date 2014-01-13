import ldap
import ldap.modlist
import unittest
import copiste.ldapsync

from tests_functional import AbstractPgEnviron

def ldap_recursive_delete_s(con, base_dn):
    search = con.search_s(base_dn, ldap.SCOPE_SUBTREE)
    delete_list = [dn for dn, _ in search]
    delete_list.reverse()

    for dn in delete_list:
        con.delete_s(dn)

class LDAPSampleData:
    @staticmethod
    def create_base(c):
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


    @staticmethod
    def create(c):
        LDAPSampleData.create_base(c)
        jdoe = {
            'objectClass': ['inetOrgPerson', 'top'],
            'cn': 'jdoe',
            'givenname' : 'Jane',
            'telephonenumber': '+1 408 555 9445',
            'sn': 'Barnes',
            'uid': '42'
        }
        c.add_s('cn=jdoe,ou=users,dc=foo,dc=bar', ldap.modlist.addModlist(jdoe))

    @staticmethod
    def delete(c):
        ldap_recursive_delete_s(c, 'dc=foo,dc=bar')

class LDAPServer(unittest.TestCase):
    """ Just to check that the test infrastructure is ok
    """
    def tearDown(self):
        try:
            c = ldap.initialize('ldap://localhost:3389')
            c.simple_bind_s('cn=admin,dc=foo,dc=bar', 'password')
            LDAPSampleData.delete(c)
        except:
            pass

    def test_serverok(self):
        c = ldap.initialize('ldap://localhost:3389')
        c.simple_bind_s('cn=admin,dc=foo,dc=bar', 'password')

    def test_add_delete(self):
        c = ldap.initialize('ldap://localhost:3389')
        c.simple_bind_s('cn=admin,dc=foo,dc=bar', 'password')
        LDAPSampleData.create(c)
        LDAPSampleData.delete(c)

class TestLDAPModel(unittest.TestCase):
    def setUp(self):
        self.ldap_c = ldap.initialize('ldap://localhost:3389')
        self.ldap_c.simple_bind_s('cn=admin,dc=foo,dc=bar', 'password')
        LDAPSampleData.create(self.ldap_c)

    def test_get_suceeds(self):
        mod = copiste.ldapsync.LDAPModel(
            query='(&(objectClass=inetOrgPerson)(uid={uid}))',
            base='ou=users,dc=foo,dc=bar'
        )
        result_dn, result_fields = mod.get(self.ldap_c, {'uid':'42'})
        self.assertEqual(result_dn, 'cn=jdoe,ou=users,dc=foo,dc=bar')
        expected_attrs = {'telephoneNumber': ['+1 408 555 9445'],
                    'cn': ['jdoe'],
                    'objectClass': ['inetOrgPerson', 'top'],
                    'sn': ['Barnes'], 'givenName': ['Jane'], 'uid': ['42']}
        self.assertEqual(result_fields, expected_attrs)

    def test_get_noentry(self):
        mod = copiste.ldapsync.LDAPModel(
            query='(&(objectClass=inetOrgPerson)(uid={uid}))',
            #query='(objectClass=*)',
            base='ou=users,dc=foo,dc=bar'
        )
        result_dn, result_fields = mod.get(self.ldap_c, {'uid':'43'})
        self.assertEqual(result_dn, None)
        self.assertEqual(result_fields, None)

    def test_get_multiple_entries(self):
        mod = copiste.ldapsync.LDAPModel(
            query='(objectClass=*)',
            base='ou=users,dc=foo,dc=bar'
        )
        with self.assertRaises(copiste.ldapsync.LDAPDataError):
            mod.get(self.ldap_c, {})

    def test_delete_succeeds(self):
        mod = copiste.ldapsync.LDAPModel(
            query='(&(objectClass=inetOrgPerson)(uid={uid}))',
            base='ou=users,dc=foo,dc=bar'
        )
        mod.delete(self.ldap_c, {'uid':'42'})
        ldap_dn, _ = mod.get(self.ldap_c, {'uid':'42'})

        self.assertEqual(ldap_dn, None)

    def test_delete_noentry(self):
        mod = copiste.ldapsync.LDAPModel(
            query='(&(objectClass=inetOrgPerson)(uid={uid}))',
            base='ou=users,dc=foo,dc=bar'
        )
        with self.assertRaises(copiste.ldapsync.LDAPDataError):
            mod.delete(self.ldap_c, {'uid':'43'})

    def test_modify_succeeds(self):
        mod = copiste.ldapsync.LDAPModel(
            query='(&(objectClass=inetOrgPerson)(uid={uid}))',
            base='ou=users,dc=foo,dc=bar'
        )
        get_attrs = {'uid':'42'}
        changed_attrs = {'sn': 'Changed'}

        mod.modify(self.ldap_c, get_attrs, changed_attrs)

        ldap_dn, ldap_attrs = mod.get(self.ldap_c, {'uid':'42'})

        self.assertEqual(ldap_dn, 'cn=jdoe,ou=users,dc=foo,dc=bar')
        self.assertEqual(ldap_attrs['sn'], ['Changed'])
        self.assertEqual(ldap_attrs['telephoneNumber'], ['+1 408 555 9445'])


    def test_modify_noentry(self):
        mod = copiste.ldapsync.LDAPModel(
            query='(&(objectClass=inetOrgPerson)(uid={uid}))',
            base='ou=users,dc=foo,dc=bar'
        )
        get_attrs = {'uid':'45'}
        changed_attrs = {'sn': 'Changed'}

        with self.assertRaises(copiste.ldapsync.LDAPDataError):
            mod.modify(self.ldap_c, get_attrs, changed_attrs)

    def test_modify_deleteattr(self):
        mod = copiste.ldapsync.LDAPModel(
            query='(&(objectClass=inetOrgPerson)(uid={uid}))',
            base='ou=users,dc=foo,dc=bar'
        )
        get_attrs = {'uid':'42'}
        changed_attrs = {'telephoneNumber': []}

        mod.modify(self.ldap_c, get_attrs, changed_attrs)

        ldap_dn, ldap_attrs = mod.get(self.ldap_c, {'uid':'42'})

        self.assertEqual(ldap_dn, 'cn=jdoe,ou=users,dc=foo,dc=bar')
        self.assertFalse(ldap_attrs.has_key('telephoneNumber'))


    def tearDown(self):
        LDAPSampleData.delete(self.ldap_c)
        self.ldap_c.unbind_s()


# class LDAPSync(AbstractPgEnviron):
#     def setUp(self):
#         self.ldap_c = ldap.initialize('ldap://localhost:3389')
#         self.ldap_c.simple_bind_s('cn=admin,dc=foo,dc=bar', 'password')
#         LDAPSampleData.create_base(self.ldap_c)


#     def test_foo(self):
#         self.cur.execute('CREATE LANGUAGE plpythonu')

#         # maping is ldap -> sql
#         attrmap = {
#             'uid': 'id',
#             'mail': 'mail',
#         }

#         ldap_user_model = copiste.ldap.model(
#             query='(&(objectClass=inetOrgPerson)(uid={}))'
#         )

#         sync_ldap = copiste.ldap.sync_models(attrmap)

#     def tearDown(self):
#         LDAPSampleData.delete(self.ldap_c)
#         self.ldap_c.unbind_s()
