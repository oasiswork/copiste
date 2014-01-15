import ldap
import ldap.modlist
import unittest
import copiste.ldapsync
import time

import copiste.functions.ldapfuncs

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
            'uid': '42',
            'mail': 'jane@doe.tld'
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
            base='ou=users,dc=foo,dc=bar',
            dn = 'uid={uid},ou=users,dc=foo,dc=bar',
        )
        result_dn, result_fields = mod.get(self.ldap_c, {'uid':'42'})
        self.assertEqual(result_dn, 'cn=jdoe,ou=users,dc=foo,dc=bar')
        expected_attrs = {'telephoneNumber': ['+1 408 555 9445'],
                    'cn': ['jdoe'], 'mail': ['jane@doe.tld'],
                    'objectClass': ['inetOrgPerson', 'top'],
                    'sn': ['Barnes'], 'givenName': ['Jane'], 'uid': ['42']}
        self.assertEqual(result_fields, expected_attrs)

    def test_get_noentry(self):
        mod = copiste.ldapsync.LDAPModel(
            query='(&(objectClass=inetOrgPerson)(uid={uid}))',
            base='ou=users,dc=foo,dc=bar',
            dn = 'uid={uid},ou=users,dc=foo,dc=bar',
        )
        result_dn, result_fields = mod.get(self.ldap_c, {'uid':'43'})
        self.assertEqual(result_dn, None)
        self.assertEqual(result_fields, None)

    def test_get_multiple_entries(self):
        mod = copiste.ldapsync.LDAPModel(
            query='(objectClass=*)',
            base='ou=users,dc=foo,dc=bar',
            dn = 'uid={uid},ou=users,dc=foo,dc=bar',
        )
        with self.assertRaises(copiste.ldapsync.LDAPDataError):
            mod.get(self.ldap_c, {})

    def test_delete_succeeds(self):
        mod = copiste.ldapsync.LDAPModel(
            query='(&(objectClass=inetOrgPerson)(uid={uid}))',
            base='ou=users,dc=foo,dc=bar',
            dn = 'uid={uid},ou=users,dc=foo,dc=bar',
        )
        mod.delete(self.ldap_c, {'uid':'42'})
        ldap_dn, _ = mod.get(self.ldap_c, {'uid':'42'})

        self.assertEqual(ldap_dn, None)

    def test_delete_noentry(self):
        mod = copiste.ldapsync.LDAPModel(
            query='(&(objectClass=inetOrgPerson)(uid={uid}))',
            base='ou=users,dc=foo,dc=bar',
            dn = 'uid={uid},ou=users,dc=foo,dc=bar',
        )
        with self.assertRaises(copiste.ldapsync.LDAPDataError):
            mod.delete(self.ldap_c, {'uid':'43'})

    def test_modify_succeeds(self):
        mod = copiste.ldapsync.LDAPModel(
            query='(&(objectClass=inetOrgPerson)(uid={uid}))',
            base='ou=users,dc=foo,dc=bar',
            dn = 'uid={uid},ou=users,dc=foo,dc=bar',
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
            base='ou=users,dc=foo,dc=bar',
            dn = 'uid={uid},ou=users,dc=foo,dc=bar',
        )
        get_attrs = {'uid':'45'}
        changed_attrs = {'sn': 'Changed'}

        with self.assertRaises(copiste.ldapsync.LDAPDataError):
            mod.modify(self.ldap_c, get_attrs, changed_attrs)

    def test_modify_deleteattr(self):
        mod = copiste.ldapsync.LDAPModel(
            query='(&(objectClass=inetOrgPerson)(uid={uid}))',
            base='ou=users,dc=foo,dc=bar',
            dn = 'uid={uid},ou=users,dc=foo,dc=bar',
        )
        get_attrs = {'uid':'42'}
        changed_attrs = {'telephoneNumber': []}

        mod.modify(self.ldap_c, get_attrs, changed_attrs)

        ldap_dn, ldap_attrs = mod.get(self.ldap_c, {'uid':'42'})

        self.assertEqual(ldap_dn, 'cn=jdoe,ou=users,dc=foo,dc=bar')
        self.assertFalse(ldap_attrs.has_key('telephoneNumber'))


    def test_add_succeeds(self):
        jmalkovitch = {
            'objectClass': ['inetOrgPerson', 'top'],
            'cn': 'jmalkovitch',
            'givenName' : 'John',
            'telephoneNumber': '+1 408 ',
            'sn': 'Malkovitch',
            'uid': '43',
            'mail': 'john@Malkovitch.tld'
        }

        def uniqfy(d):
            """ Transforms the single-valued properties into simple types
            instead of lists.
            """
            out = {}
            for k,v in d.items():
                if len(v) == 1:
                    out[k] = v[0]
                else:
                    out[k] = v

            return out

        mod = copiste.ldapsync.LDAPModel(
            query='(&(objectClass=inetOrgPerson)(uid={uid}))',
            base='ou=users,dc=foo,dc=bar',
            dn = 'uid={uid},ou=users,dc=foo,dc=bar',
        )
        mod.create(self.ldap_c, jmalkovitch)

        ldap_dn, ldap_attrs = mod.get(self.ldap_c, {'uid': '43'})

        self.assertEqual(ldap_dn, 'uid=43,ou=users,dc=foo,dc=bar')
        self.assertEqual(uniqfy(ldap_attrs), jmalkovitch)


    def tearDown(self):
        LDAPSampleData.delete(self.ldap_c)
        self.ldap_c.unbind_s()


class AbstractLDAPPostgresBinding(AbstractPgEnviron):
    def setUp(self):
        super(AbstractLDAPPostgresBinding, self).setUp()
        self.cur.execute('CREATE LANGUAGE plpythonu')
        try:
            self.ldap_c = ldap.initialize('ldap://localhost:3389')
            self.ldap_c.simple_bind_s('cn=admin,dc=foo,dc=bar', 'password')
            try:
                LDAPSampleData.delete(self.ldap_c)
            except:
                pass

            LDAPSampleData.create_base(self.ldap_c)

            self.creds = {
                "host"     : 'ldap://localhost:389',
                "bind_dn"  : 'cn=admin,dc=foo,dc=bar',
                "bind_pw"  : 'password'
            }
        except Exception, e:
            try:
                super(AbstractLDAPPostgresBinding, self).tearDown()
            except:
                pass
            raise

        self.ldap_user_model = copiste.ldapsync.LDAPModel(
            query='(&(objectClass=inetOrgPerson)(uid={uid}))',
            base='ou=users,dc=foo,dc=bar',
            dn = 'uid={uid},ou=users,dc=foo,dc=bar',
            static_attrs={'objectClass': ['top', 'inetOrgPerson']}
        )

    def tearDown(self):
        super(AbstractLDAPPostgresBinding, self).tearDown()
        LDAPSampleData.delete(self.ldap_c)
        self.ldap_c.unbind_s()


class LDAPSync(AbstractLDAPPostgresBinding):
    def setUp(self):
        super(LDAPSync, self).setUp()

        # mapping is ldap -> sql
        self.attrmap = {
            'uid': 'id',
            'mail': 'mail',
            'sn': 'mail',
            'cn': 'mail',
        }

        self.sql_insert = \
            "INSERT INTO unittest_table (id, mail) VALUES ('1', 'foo@bar.com')"
        self.sql_delete = "DELETE FROM unittest_table WHERE (id=1)"
        self.sql_update_email = \
            "UPDATE unittest_table set mail='updated@bar.tld' WHERE (id=1)"

        sync_ldap = copiste.functions.ldapfuncs.Copy2LDAP(
            attrs_map  = self.attrmap,
            ldap_model = self.ldap_user_model,
            ldap_creds = self.creds
        )

        trigger = copiste.sql.WriteTrigger(
            sql_table = 'unittest_table',
            name      = 'sync_users'
        )

        bind = copiste.binding.Bind(trigger, sync_ldap, self.con)
        bind.install()

    def test_sync_create(self):
        self.cur.execute(self.sql_insert)

        # we check that the user has been created in ldap
        dn, attrs = self.ldap_user_model.get(self.ldap_c, {'uid':'1'})

        expected_attrs = {'objectClass': ['top', 'inetOrgPerson'],
                          'mail': ['foo@bar.com'], 'sn': ['foo@bar.com'],
                          'cn': ['foo@bar.com'], 'uid': ['1']}

        self.assertEqual(dn,'uid=1,ou=users,dc=foo,dc=bar')
        self.assertEqual(attrs, expected_attrs)

    def test_sync_delete(self):
        self.cur.execute(self.sql_insert)
        self.cur.execute(self.sql_delete)

        # we check that the user has been removed in ldap
        dn, _ = self.ldap_user_model.get(self.ldap_c, {'uid':'1'})

        self.assertEqual(dn, None)

    def test_sync_update(self):
        self.cur.execute(self.sql_insert)
        self.cur.execute(self.sql_update_email)

        # we check that the user has been updated in ldap
        dn, attrs = self.ldap_user_model.get(self.ldap_c, {'uid':'1'})

        expected_attrs = {'objectClass': ['top', 'inetOrgPerson'],
                          'mail': ['updated@bar.tld'], 'sn': ['updated@bar.tld'],
                          'cn': ['updated@bar.tld'], 'uid': ['1']}

        self.assertEqual(dn, 'uid=1,ou=users,dc=foo,dc=bar')
        self.assertEqual(attrs, expected_attrs)

class LDAPSyncWithDynAttr(AbstractLDAPPostgresBinding):
    def setUp(self):
        super(LDAPSyncWithDynAttr, self).setUp()

        # mapping is ldap -> sql
        self.attrmap = {
            'uid': 'id',
            'sn': 'mail',
            'cn': 'mail',
            'mail': 'mail'
        }

        self.dyn_attrs_map = {
            'mail': ("SELECT mail from unittest_alias WHERE user_id = '{id}'")
        }

        self.sql_insert = \
            "INSERT INTO unittest_table (id, mail) VALUES ('1', 'foo@bar.com')"
        self.sql_delete = "DELETE FROM unittest_table WHERE (id=1)"
        self.sql_update_email = \
            "UPDATE unittest_table set mail='updated@bar.tld' WHERE (id=1)"
        self.sql_insert_alias = \
            "INSERT INTO unittest_alias values(1, 'alias@alias.tld')"

        # we create a second table
        self.cur.execute(
            'CREATE TABLE unittest_alias (user_id INT, mail VARCHAR(100))')

        sync_ldap = copiste.functions.ldapfuncs.Copy2LDAP(
            attrs_map  = self.attrmap,
            ldap_model = self.ldap_user_model,
            ldap_creds = self.creds,
            dyn_attrs_map = self.dyn_attrs_map
        )

        trigger = copiste.sql.WriteTrigger(
            sql_table = 'unittest_table',
            name      = 'sync_users'
        )

        bind = copiste.binding.Bind(trigger, sync_ldap, self.con)
        bind.install()

    def test_sync_create(self):
        self.cur.execute(self.sql_insert_alias)
        self.cur.execute(self.sql_insert)

        # we check that the user has been created in ldap
        dn, attrs = self.ldap_user_model.get(self.ldap_c, {'uid':'1'})

        self.assertEqual(attrs['mail'], ['foo@bar.com', 'alias@alias.tld'])

    def test_sync_update(self):
        self.cur.execute(self.sql_insert)
        self.cur.execute(self.sql_insert_alias)
        self.cur.execute(self.sql_update_email)

        # we check that the user has been updated in ldap
        dn, attrs = self.ldap_user_model.get(self.ldap_c, {'uid':'1'})

        self.assertEqual(attrs['mail'], ['updated@bar.tld', 'alias@alias.tld'])


class LDAPAccumulate(AbstractLDAPPostgresBinding):
    def setUp(self):
        super(LDAPAccumulate, self).setUp()

        # sample data
        self.cur.execute(
            "INSERT INTO unittest_table (id, mail) VALUES ('1', 'foo@bar.com')")
        sample_user = {'objectClass': ['top', 'inetOrgPerson'],
                       'mail': ['foo@bar.com'], 'sn': ['foo@bar.com'],
                       'cn': ['foo@bar.com'], 'uid': ['1']}
        self.ldap_c.add_s('uid=1,ou=users,dc=foo,dc=bar',
                          ldap.modlist.addModlist(sample_user))

        # we create a second table
        self.cur.execute(
            'CREATE TABLE unittest_alias (user_id INT, mail VARCHAR(100))')

        # SQL queries
        self.sql_insert = \
            "INSERT INTO unittest_alias (user_id, mail) "+\
            "VALUES ('1', 'foo2@bar.com')"
        self.sql_delete = "DELETE FROM unittest_alias WHERE (user_id=1)"
        self.sql_update = \
            "UPDATE unittest_alias set mail='foo2updated@bar.tld' "+\
            "WHERE (user_id=1)"

        accumulate_aliases = copiste.functions.ldapfuncs.Accumulate2LDAPField(
            ldap_field = 'mail',
            keys_map   = {'uid': 'user_id'},
            ldap_model = self.ldap_user_model,
            ldap_creds = self.creds
        )

        trigger = copiste.sql.WriteTrigger(
            sql_table = 'unittest_alias',
            name      = 'accumulate_mail_aliases'
        )

        bind = copiste.binding.Bind(trigger, accumulate_aliases, self.con)
        bind.install()

    def test_insert(self):
        self.cur.execute(self.sql_insert)

        # we check that the user has been created in ldap
        dn, attrs = self.ldap_user_model.get(self.ldap_c, {'uid':'1'})

        expected_attrs = {'objectClass': ['top', 'inetOrgPerson'],
                          'mail': ['foo@bar.com', 'foo2@bar.com'],
                          'sn': ['foo@bar.com'],
                          'cn': ['foo@bar.com'], 'uid': ['1']}

        self.assertEqual(dn,'uid=1,ou=users,dc=foo,dc=bar')
        self.assertEqual(attrs, expected_attrs)


    def test_delete(self):
        self.cur.execute(self.sql_insert)
        self.cur.execute(self.sql_delete)

        # we check that the user has been created in ldap
        dn, attrs = self.ldap_user_model.get(self.ldap_c, {'uid':'1'})

        expected_attrs = {'objectClass': ['top', 'inetOrgPerson'],
                          'mail': ['foo@bar.com'],
                          'sn': ['foo@bar.com'],
                          'cn': ['foo@bar.com'], 'uid': ['1']}

        self.assertEqual(dn,'uid=1,ou=users,dc=foo,dc=bar')
        self.assertEqual(attrs, expected_attrs)


    def test_update(self):
        self.cur.execute(self.sql_insert)
        self.cur.execute(self.sql_update)

        # we check that the user has been created in ldap
        dn, attrs = self.ldap_user_model.get(self.ldap_c, {'uid':'1'})

        expected_attrs = {'objectClass': ['top', 'inetOrgPerson'],
                          'mail': ['foo@bar.com', 'foo2updated@bar.tld'],
                          'sn': ['foo@bar.com'],
                          'cn': ['foo@bar.com'], 'uid': ['1']}

        self.assertEqual(dn,'uid=1,ou=users,dc=foo,dc=bar')
        self.assertEqual(attrs, expected_attrs)



class TestStoreIfExists(AbstractLDAPPostgresBinding):
    def setUp(self):
        super(TestStoreIfExists, self).setUp()

        self.sql_insert_a_thing = \
            "INSERT INTO unittest_things values(1, 'spoon')"

        self.sql_give_a_thing = \
            "UPDATE unittest_things SET owner_id= '2' WHERE thing = 'spoon'"

        self.sql_delete_a_thing = \
            "DELETE FROM unittest_things WHERE thing = 'spoon'"

        self.sql_insert_another_thing = \
            "INSERT INTO unittest_things values(1, 'fork')"
        self.sql_delete_another_thing = \
            "DELETE FROM unittest_things WHERE thing = 'fork'"

        self.sql_insert_someone_else_thing = \
            "INSERT INTO unittest_things values(2, 'a knife')"

        self.sql_take_someone_else_thing = \
            "UPDATE unittest_things SET owner_id= '1' WHERE thing = 'knife'"


        # we create a second table
        self.cur.execute(
            'CREATE TABLE unittest_things (owner_id INT, thing VARCHAR(100))')

        sample_user = {'objectClass': ['top', 'inetOrgPerson'],
                       'mail': ['foo@bar.com'], 'sn': ['foo@bar.com'],
                       'cn': ['foo@bar.com'], 'uid': ['1']}

        sample_user2 = {'objectClass': ['top', 'inetOrgPerson'],
                       'mail': ['other@bar.com'], 'sn': ['other@bar.com'],
                       'cn': ['other@bar.com'], 'uid': ['2']}

        self.ldap_c.add_s('uid=1,ou=users,dc=foo,dc=bar',
                          ldap.modlist.addModlist(sample_user))

        self.ldap_c.add_s('uid=2,ou=users,dc=foo,dc=bar',
                          ldap.modlist.addModlist(sample_user2))

        sync_ldap = copiste.functions.ldapfuncs.StoreIfExists(
            sql_test_attr  = 'owner_id',
            ldap_store_key = 'objectClass',
            ldap_store_val = 'bootableDevice', # arbitrary, IRL would be (thingOwner)
            key_map        = {'uid':'owner_id'},
            ldap_model = self.ldap_user_model,
            ldap_creds = self.creds,
        )

        trigger = copiste.sql.WriteTrigger(
            sql_table = 'unittest_things',
            name      = 'sync_owner_flag'
        )

        bind = copiste.binding.Bind(trigger, sync_ldap, self.con)
        bind.install()

    def test_insert(self):
        self.cur.execute(self.sql_insert_a_thing)

        # we check that the user has been created in ldap
        dn, attrs = self.ldap_user_model.get(self.ldap_c, {'uid':'1'})
        self.assertEqual(attrs['objectClass'],
                         ['top', 'inetOrgPerson', 'bootableDevice'])


    def test_insert_two(self):
        self.cur.execute(self.sql_insert_a_thing)
        self.cur.execute(self.sql_insert_another_thing)

        # we check that the user has been created in ldap
        dn, attrs = self.ldap_user_model.get(self.ldap_c, {'uid':'1'})
        self.assertEqual(attrs['objectClass'],
                         ['top', 'inetOrgPerson', 'bootableDevice'])

    def test_insert_remove(self):
        self.cur.execute(self.sql_insert_a_thing)
        self.cur.execute(self.sql_delete_a_thing)

        # we check that the user has been created in ldap
        dn, attrs = self.ldap_user_model.get(self.ldap_c, {'uid':'1'})
        self.assertEqual(attrs['objectClass'],
                         ['top', 'inetOrgPerson'])

    def test_insert_insert_remove(self):
        self.cur.execute(self.sql_insert_a_thing)
        self.cur.execute(self.sql_insert_another_thing)
        self.cur.execute(self.sql_delete_a_thing)

        # we check that the user has been created in ldap
        dn, attrs = self.ldap_user_model.get(self.ldap_c, {'uid':'1'})
        self.assertEqual(attrs['objectClass'],
                         ['top', 'inetOrgPerson', 'bootableDevice'])

    def test_update_become_true(self):
        self.cur.execute(self.sql_insert_a_thing)
        self.cur.execute(self.sql_insert_another_thing)
        self.cur.execute(self.sql_delete_a_thing)

        # we check that the user has been created in ldap
        dn, attrs = self.ldap_user_model.get(self.ldap_c, {'uid':'1'})
        self.assertEqual(attrs['objectClass'],
                         ['top', 'inetOrgPerson', 'bootableDevice'])

    def test_update_become_false(self):
        self.cur.execute(self.sql_insert_a_thing)
        self.cur.execute(self.sql_give_a_thing)

        dn1, attrs1 = self.ldap_user_model.get(self.ldap_c, {'uid':'1'})
        dn2, attrs2 = self.ldap_user_model.get(self.ldap_c, {'uid':'2'})

        self.assertEqual(attrs1['objectClass'],
                         ['top', 'inetOrgPerson'])

        self.assertEqual(attrs2['objectClass'],
                         ['top', 'inetOrgPerson', 'bootableDevice'])
