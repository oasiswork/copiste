import copiste.functions
import copiste.functions.ldapfuncs
import copiste.sql
import copiste.ldapsync
import copiste.binding

import psycopg2

#### CREDENTIALS ####

ldap_credentials = {
    "host"     : 'ldap://localhost:389',
    "bind_dn"  : 'cn=admin,dc=foo,dc=bar',
    "bind_pw"  : 'password'
}

pg_credentials = {
    'host'     : "localhost",
    'user'     : "postgres",
    'database' : "manutest"
}

#### FUNCTIONS ####

ldap_user_model = copiste.ldapsync.LDAPModel(
    query='(&(objectClass=inetOrgPerson)(uid={uid}))',
    base='ou=users,dc=foo,dc=bar',
    dn = 'uid={uid},ou=users,dc=foo,dc=bar',
    static_attrs={'objectClass': ['top', 'inetOrgPerson']}
)

sync_ldap = copiste.functions.ldapfuncs.Copy2LDAP(
    attrs_map = {
        'uid' : 'id',
        'mail': 'mail',
        'sn'  : 'mail',
        'cn'  : 'mail',
    },
    dyn_attrs_map = {
        'mail': "SELECT mail from unittest_alias WHERE user_id = '{id}'"
    },
    ldap_model = ldap_user_model,
    ldap_creds = ldap_credentials,
)

#### TRIGGERS ####

on_write_user = copiste.sql.WriteTrigger(
    sql_table = 'unittest_table',
    name      = 'sync_users'
)


#### BINDINGS ####

bindings = [
    copiste.binding.Bind(on_write_user, sync_ldap)
]

