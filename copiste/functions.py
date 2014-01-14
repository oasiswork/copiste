import inspect
import marshal
import uuid

import ldap

from copiste.ldapsync import LDAPModel, LDAPUtils

class PlPythonFunction(object):
    """ An abstract plpython object

    This class handles (un)installation, calling and naming of the stored
    functions.

    One should extend it, overriding call() and optionally __init__()
    """
    def __init__(self, **kwargs):
        self.args = kwargs

        # builds a uuid withou '-' sign which is forbidden in SQL functions names
        self.uuid = ''
        for f in uuid.uuid4().fields:
            self.uuid += str(f)

    def func_name(self):
        """ Generates the func_name used for storage in Postgre.

        This name is prefixed by "copiste__" and contains a random UUID.
        """
        class_name = self.__class__.__name__
        return 'copiste__{}__{}'.format(class_name.lower(), self.uuid)

    def sql_install(self):
        """ Stores the function inside the db. Actually stores only a stub,
        which will call the function. """
        pyargs_marshalled = marshal.dumps(self.args).encode('base64').strip()
        sql = """
CREATE FUNCTION {}()
RETURNS TRIGGER
AS
$$
  import copiste
  import copiste.functions
  import marshal
  pyargs_marshalled = \"""{}\"""
  pyargs = marshal.loads(pyargs_marshalled.decode('base64'))
  f = copiste.functions.{}(**pyargs)
  return f.call(TD, plpy)
$$
LANGUAGE plpythonu;
        """.format(self.func_name(), pyargs_marshalled, self.__class__.__name__)
        return sql

    def sql_uninstall(self):
        return 'DROP FUNCTION {}()'.format(self.func_name())

class LogWarn(PlPythonFunction):
    """ Just a functions which prints something in postgres LOG
    """
    def call(self, TD, plpy):
        plpy.warning(self.args['message'])

class Copy2LDAP(PlPythonFunction):
    """ This function will keep in sync a LDAPModel with the DB, updating it
    according an attributes map on each CREATE/UPDATE/DELETE/TRUNCATE.
    """
    def __init__(self, attrs_map, ldap_model, ldap_creds, dyn_attrs_map={}):
        """
        @param dyn_attrs_map : a map containing ldap_attr->SQL_REQUEST, the
        requests is a string and can be parametrized using sql columns (ex:
        "{name}"), they will be replaced at query-time.
        """
        # as models are marshalled for db storage, we can't store objects, but
        # only basic types.
        if not isinstance(ldap_model, dict):
            ldap_model = ldap_model.to_dict()

        kwargs = {
            'attrs_map': attrs_map,
            'dyn_attrs_map': dyn_attrs_map,
            'ldap_model': ldap_model,
            'ldap_creds': ldap_creds
        }
        super(Copy2LDAP, self).__init__(**kwargs)

    def get_ldap_model(self):
        return LDAPModel(**(self.args['ldap_model']))

    def call(self, TD, plpy):
        creds = self.args['ldap_creds']
        event = TD['event']

        c = ldap.initialize(creds['host'])
        c.simple_bind_s(creds['bind_dn'], creds['bind_pw'])
        try:
            if event == 'DELETE':
                self.handle_DELETE(TD, plpy, c)
            elif event == 'UPDATE':
                self.handle_UPDATE(TD, plpy, c)
            elif event == 'INSERT':
                self.handle_CREATE(TD, plpy, c)
            else:
                raise ValueError('unknown event : '+event )
        except:
            c.unbind_s()
            raise

        else:
            c.unbind_s()


    def handle_UPDATE(self, TD, plpy, ldap_c):
        old_ldap_attrs = self.ldap_data(TD['old'])
        new_ldap_attrs = self.ldap_data(TD['new'])

        # There are cases where a MODIFY does not imply a LDAP change
        if old_ldap_attrs != new_ldap_attrs:
            added_attrs = set(new_ldap_attrs.keys()) - set(old_ldap_attrs.keys())
            rmed_attrs = set(old_ldap_attrs.keys()) - set(new_ldap_attrs.keys())

            diff = {}

            for k in added_attrs:
                diff[k] = new_ldap_attrs[k]

            for k in rmed_attrs:
                diff[k] = []

            for k, v in new_ldap_attrs.items():
                if (old_ldap_attrs.has_key(k) and
                    (old_ldap_attrs[k] != new_ldap_attrs[k])):
                    diff[k] = v

            self.process_dyn_attrs(new_ldap_attrs, plpy, TD['new'])
            self.get_ldap_model().modify(ldap_c, old_ldap_attrs, new_ldap_attrs)

    def handle_DELETE(self, TD, plpy, ldap_c):
        ldap_attrs = self.ldap_data(TD['old'])
        self.get_ldap_model().delete(ldap_c, ldap_attrs)

    def handle_CREATE(self, TD, plpy, ldap_c):
        ldap_attrs = self.ldap_data(TD['new'])
        plpy.log('creating an entry from SQL with values {}'.format(
                str(ldap_attrs)))
        self.process_dyn_attrs(ldap_attrs, plpy, TD['new'])
        self.get_ldap_model().create(ldap_c, ldap_attrs)

    def ldap_data(self, sql_data):
        """ Transforms a SQL row into a dict of attributes ready for LDAP use.

        Mapping is done according the provided attributes map.

        @param sql_data : a dict representing a SQL row.
        @returns a dict representing ldap attributes.
        """
        o = {}
        # LDAP requires even numbers to be surrounded by quotes, so we str()
        # everything
        for ldap_k, sql_k in self.args['attrs_map'].items():
            if sql_data.has_key(sql_k):
                o[ldap_k] = str(sql_data[sql_k])
        return o

    def process_dyn_attrs(self, ldap_attrs, plpy, new_row):
        """ Process the dynamic attributes,

        Updates (inplace) the ldap_attrs dict accordingly.
        if an attr is already specified, and have to be computed dynamically
        also, its content will *not* be replaced, but a multivalued LDAP
        attribute will be used.

        @param ldap_attrs the ldap_attrs, already populated
        """
        for k, sql_request in self.args['dyn_attrs_map'].items():
            res = plpy.execute(sql_request.format(**new_row))

            if len(res) > 0:
                if not ldap_attrs.has_key(k):
                    ldap_attrs[k] = []
                elif not isinstance(ldap_attrs[k], (list, tuple)):
                    ldap_attrs[k] = [ldap_attrs[k]]
                ldap_attrs[k] += [i[k] for i in res]
                # remove duplicates:
                ldap_attrs = list(set(ldap_attrs))



class Accumulate2LDAPField(PlPythonFunction):
    """ This function will store the result of a query in a multi-value
        attribute from a ldap model.
    """
    def __init__(self, ldap_field, keys_map, ldap_model, ldap_creds):
        # as models are marshalled for db storage, we can't store objects, but
        # only basic types.
        if not isinstance(ldap_model, dict):
            ldap_model = ldap_model.to_dict()

        kwargs = {
            'ldap_field': ldap_field,
            'keys_map'  : keys_map,
            'ldap_model': ldap_model,
            'ldap_creds': ldap_creds
        }
        super(Accumulate2LDAPField, self).__init__(**kwargs)

    def get_ldap_model(self):
        return LDAPModel(**(self.args['ldap_model']))


    def call(self, TD, plpy):
        creds = self.args['ldap_creds']
        event = TD['event']

        c = ldap.initialize(creds['host'])
        c.simple_bind_s(creds['bind_dn'], creds['bind_pw'])

        try:
            if event == 'DELETE':
                self.handle_DELETE(TD, plpy, c)
            elif event == 'UPDATE':
                self.handle_UPDATE(TD, plpy, c)
            elif event == 'INSERT':
                self.handle_INSERT(TD, plpy, c)
            else:
                raise ValueError('unknown event : '+event )
        except:
            c.unbind_s()
            raise

        else:
            c.unbind_s()

    def handle_INSERT(self, TD, plpy, ldap_c):
        field = self.args['ldap_field']
        new_row = TD['new']
        new_val = new_row[field]
        dn, previous_values = self.get_accumulator_list(ldap_c, new_row)

        if not new_val in previous_values:
            new_values = list(previous_values) # copy
            new_values.append(new_val)

            ldif = ldap.modlist.modifyModlist(
                {field : previous_values},
                {field: new_values}
            )
            ldap_c.modify_s(dn, ldif)

    def handle_DELETE(self, TD, plpy, ldap_c):
        field = self.args['ldap_field']
        old_row = TD['old']
        old_val = old_row[field]

        dn, previous_values = self.get_accumulator_list(ldap_c, old_row)
        new_values = list(previous_values) # copy
        new_values.remove(old_val)
        ldif = ldap.modlist.modifyModlist(
            {field : previous_values},
            {field: new_values}
        )
        ldap_c.modify_s(dn, ldif)

    def handle_UPDATE(self, TD, plpy, ldap_c):
        field = self.args['ldap_field']
        old_row = TD['old']
        new_row = TD['new']
        old_val = old_row[field]
        new_val = new_row[field]

        if new_val != old_val:
            dn, previous_values = self.get_accumulator_list(ldap_c, old_row)
            new_values = list(previous_values) # copy
            new_values.remove(old_val)
            if not new_val in new_values:
                new_values.append(new_val)
            ldif = ldap.modlist.modifyModlist(
                {field: previous_values},
                {field: new_values}
            )
            print ldif
            ldap_c.modify_s(dn, ldif)
            print ldif

    def get_accumulator_list(self, ldap_c, sql_data):
        keys_map = self.args['keys_map']
        ldap_model = self.get_ldap_model()
        field = self.args['ldap_field']

        matches = {}
        for ldap_key, sql_key in keys_map.items():
            matches[ldap_key] = sql_data[sql_key]

        dn, attrs = ldap_model.get(ldap_c, matches)

        return dn, attrs[field]
