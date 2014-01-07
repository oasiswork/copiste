Copiste : realtime Postgre → LDAP replication
=============================================

- framework to write PostgreSQL to LDAP replication rules
- flexible rules (more than just copying fields)
- handles (un)installing triggers/functions in PostgreSQL

Getting started
---------------

    ./setup.py install

Then you have to write your manifest, let's say it's `manifest.py`
Load it into PostgreSQL with

    $ copiste install manifest.py

Each time you change something in manifest.py you have to run

	$ copiste update manifest.py

… to push the modifications in the db.

