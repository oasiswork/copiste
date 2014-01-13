import inspect
import marshal
import uuid

import ldap

from copiste.ldapsync import LDAPModel

class PlPythonFunction(object):
    def __init__(self, **kwargs):
        self.args = kwargs

        # builds a uuid withou '-' sign which is forbidden in SQL functions names
        self.uuid = ''
        for f in uuid.uuid4().fields:
            self.uuid += str(f)

    def func_name(self):
        class_name = self.__class__.__name__
        return 'copiste__{}__{}'.format(class_name.lower(), self.uuid)

    def sql_install(self):
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
    def call(self, TD, plpy):
        plpy.warning(self.args['message'])


class Copy2LDAP(PlPythonFunction):
    def __init__(self, attrs_map, ldap_model, ldap_creds):
        if not isinstance(ldap_model, dict):
            ldap_model = ldap_model.to_dict()

        kwargs = {
            'attrs_map': attrs_map,
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

            self.get_ldap_model().modify(ldap_c, old_ldap_attrs, new_ldap_attrs)

    def handle_DELETE(self, TD, plpy, ldap_c):
        ldap_attrs = self.ldap_data(TD['old'])
        self.get_ldap_model().delete(ldap_c, ldap_attrs)

    def handle_CREATE(self, TD, plpy, ldap_c):
        ldap_attrs = self.ldap_data(TD['new'])
        plpy.log('creating an entry from SQL with values {}'.format(
                str(ldap_attrs)))
        self.get_ldap_model().create(ldap_c, ldap_attrs)

    def ldap_data(self, sql_data):
        o = {}
        # LDAP requires even numbres to be surrounded by quotes, so we str()
        # everything
        for ldap_k, sql_k in self.args['attrs_map'].items():
            if sql_data.has_key(sql_k):
                o[ldap_k] = str(sql_data[sql_k])
        return o

