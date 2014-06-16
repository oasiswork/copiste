#!/usr/bin/env python
"""
Just a script to create/destroy a manual testing environment to play with the
copiste binary.

DB name is "manutest", db layout is just bellow :
"""

import sys

import ldap
import ldap.modlist

def ldap_recursive_delete_s(con, base_dn):
    search = con.search_s(base_dn, ldap.SCOPE_SUBTREE)
    delete_list = [dn for dn, _ in search]
    delete_list.reverse()

    for dn in delete_list:
        con.delete_s(dn)


def create_empty_ldap(c):
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


def destroy_db(con):
    con.cursor().execute('DROP DATABASE manutest')

def destroy_ldap(c):
    ldap_recursive_delete_s(c, 'dc=foo,dc=bar')


if __name__ == '__main__':
    ldap_c = ldap.initialize('ldap://localhost:3389')
    ldap_c.simple_bind_s('cn=admin,dc=foo,dc=bar', 'password')

    try:
        cmd = sys.argv[1]
    except IndexError:
        print 'you should provide a cmd a sargument "create" or "destroy"'
        exit(1)

    if cmd ==  'create':
        create_empty_ldap(ldap_c)

    elif cmd == 'destroy':
        try:
            destroy_ldap(ldap_c)
        except Exception, e:
            print 'LDAP destroy failed :'+str(e)

    else:
        print 'unkwon command "{}"'.format(cmd)

    # cleanup

    ldap_c.unbind_s()
    try:
        sql_c.close()
    except:
        pass
