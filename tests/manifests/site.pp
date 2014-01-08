file {'/etc/resolv.conf':
  content => "nameserver 8.8.8.8\n"
}

package { "postgresql-plpython-9.1":
    ensure => "latest"
}
package { "python-psycopg2":
    ensure => "present"
}

