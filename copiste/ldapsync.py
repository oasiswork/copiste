import ldap
import ldap.modlist

class LDAPDataError(Exception):
    pass

class LDAPModel:
    """ Represents a "model" within LDAPD

    A model for example can be "the users" or "the groups" or "the clients".
    CRUD methods are provided to manipulate the model instances.
    """

    def __init__(self, query, base):
        """
        @param key the LDAP field owning the unique key for the model
        @param query the LDAP filter to match this model, you can use "{foo}" for
        subsitutions, where "foo" is an attr name, the value wil be substituted.
        @param base the LDAP base to search for this model
        """
        self.query = query
        self.base = base

    def get(self, ldap_con, attrs):
        """ Tries to fetch the model from LDAP

        @param ldap_con a LDAPObject, already bound
        @param attrs    a map of attrs, they should contain (at least) the
                        arguments used in the query (see __init__()).

        @return (dn, attrs) if found, None, None else.
        """
        query = self.query.format(**attrs)
        res = ldap_con.search_s(self.base, ldap.SCOPE_SUBTREE, query)
        if len(res) > 1:
            raise LDAPDataError(
                'More than one result for query "{}" on base "{}"'.format(
                    query, self.base))

        elif len(res) == 1:
            return res[0]
        else:
            return None, None

    def delete(self, ldap_con, attrs):
        """
        Delete a model instance (raise a LDAPDataError error if the model does
        not exists.)

        @param ldap_con a LDAPObject, already bound
        @param attrs    a map of attrs, they should contain (at least) the
                        arguments used in the query (see __init__()).
        """
        ldap_dn, ldap_attrs = self.get(ldap_con, attrs)
        if ldap_dn:
            ldap_con.delete_s(ldap_dn)
        else:
            raise LDAPDataError('cannot delete a non-existant model')


    def modify(self, ldap_con, attrs, changed_attrs):
        """
        Modify a model instance (raise a LDAPDataError error if the model does
        not exists.)

        @param ldap_con a LDAPObject, already bound
        @param attrs    a map of attrs, to retrieve the entrythey should contain
                        (at least) the  arguments used in the query (see
                        __init__()).
        @param changed_attrs a map containing only the attributes you want to
                             change, others won't be touched. Specify empty list
                             to blank an attribute.
        """

        ldap_dn, old_attrs = self.get(ldap_con, attrs)
        if not ldap_dn:
            raise LDAPDataError('cannot modify a non-existant model')
        new_attrs = old_attrs.copy()
        new_attrs.update(changed_attrs)

        if ldap_dn:
            delta = ldap.modlist.modifyModlist(old_attrs, new_attrs)
            ldap_con.modify_s(ldap_dn, delta)
        else:
            raise LDAPDataError('cannot delete a non-existant model')

