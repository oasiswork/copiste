file {'/etc/resolv.conf':
  content => "nameserver 8.8.8.8\n"
}

package { "postgresql-plpython-9.1":
    ensure => "latest"
}
package { "python-psycopg2":
    ensure => "present"
}


# node default {
#   class { 'ldap':
#     server => true,
#     ssl => false,
#   }
# }
# ldap::define::domain {'puppetlabs.test':
#   basedn => 'dc=puppetlabs,dc=test',
#   rootdn => 'cn=admin',
#   rootpw => 'test',
#   auth_who => 'anonymous'
# }
class {'ldap::server::master':
    suffix      => 'dc=foo,dc=bar',
    rootpw      => '{SSHA}R+o6Ty6/ZbjWFfh31/ut/L+mn0fyHqPU', # "password"
}
