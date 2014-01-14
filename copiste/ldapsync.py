import ldap
import ldap.modlist

import copy

class LDAPUtils:
    @staticmethod
    def build_AND_filter(keyval):
        """" Builds a LDAP AND filter

        @param keyval a dict of key-value, all of them should match
        @returns      a string : the LDAP filter
        """
        filters = ['({}={})'.format(k, v) for k, v in keyval.items()]
        if len(filters) == 1:
            return filters[0]
        elif len(filters) == 0:
            return ''
        else:
            return '&({})'.format(''.join(filters))


class LDAPDataError(Exception):
    pass

class LDAPModel:
    """ Represents a "model" within LDAPD

    A model for example can be "the users" or "the groups" or "the clients".
    CRUD methods are provided to manipulate the model instances.
    """

    def __init__(self, query, base, dn, static_attrs={}):
        """
        @param dn is a template to generate the dn, fields are handled as for
               the query
        @param query the LDAP filter to match this model, you can use "{foo}" for
               subsitutions, where "foo" is an attr name, the value wil be
               substituted.
        @param base the LDAP base to search for this model
        @param static_attrs: a dict containing attributes that will always
               be the same for a givenModel (think about objectClass).
        """
        self.dn = dn
        self.query = query
        self.base = base
        self.static_attrs = static_attrs

    def to_dict(self):
        d = {}
        for k in ('dn', 'query', 'base', 'static_attrs'):
            d[k] = getattr(self, k)
        return d

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


    def modify(self, ldap_con, attrs, changed_attrs, accumulate=False):
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
        @param accumulate  add element to multi-valued attr instead of
                           overwritting existing attrs
        """

        ldap_dn, old_attrs = self.get(ldap_con, attrs)
        if not ldap_dn:
            raise LDAPDataError('cannot modify a non-existant model')
        new_attrs = copy.deepcopy(old_attrs)
        print old_attrs

        if accumulate:
            # add element to multi-valued attr instead of overwritting
            for k,v in changed_attrs.items():
                if not new_attrs.has_key(k):
                    new_attrs[k] = []
                elif not isinstance(new_attrs[k], (list, tuple)):
                    new_attrs[k] = [new_attrs[k]]
                # avoid duplicates
                if not v in new_attrs[k]:
                    new_attrs[k].append(v)
        else:
            new_attrs.update(changed_attrs)

        if ldap_dn:
            delta = ldap.modlist.modifyModlist(old_attrs, new_attrs)
            print 'DELTA', delta
            ldap_con.modify_s(ldap_dn, delta)
        else:
            raise LDAPDataError('cannot delete a non-existant model')

    def remove_from_attr(self, ldap_con, attrs, attr, val):
        """ For a specific LDAP attribute, remove a value from a multi-valued
        attr.
        """
        ldap_dn, old_attrs = self.get(ldap_con, attrs)
        new_attrs = copy.deepcopy(old_attrs)

        if val in new_attrs[attr]:
            new_attrs = new_attrs.copy()
            new_attrs[attr].remove(val)

        if ldap_dn:
            delta = ldap.modlist.modifyModlist(old_attrs, new_attrs)
            ldap_con.modify_s(ldap_dn, delta)

        else:
            raise LDAPDataError('cannot modify a non-existant model')


    def create(self, ldap_con, attrs):
        """ Tries to create the object from LDAP

        @param ldap_con a LDAPObject, already bound
        @param attrs    all the attrs for the new object, you should ommit dn,
                        it will be computed from self.dn
        """
        dn = self.dn.format(**attrs)
        all_attrs = self.static_attrs.copy()
        all_attrs.update(attrs)

        ldif = ldap.modlist.addModlist(all_attrs)

        try:
            res = ldap_con.add_s(dn, ldif)
        except ldap.LDAPError, e:
            raise LDAPDataError('LDAP Error: {}'.format(str(e)))


