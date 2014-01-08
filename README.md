Copiste : realtime Postgre → LDAP replication
=============================================

- framework to write PostgreSQL to LDAP replication rules
- flexible rules (more than just copying fields)
- handles (un)installing triggers/functions in PostgreSQL

Installing
----------

You can see two different machines in the install/use process :

 - *db* : the host running the database
 - *control* : the host running the copiste commands

 They can be the same host of course.

### Install on *db* ###

    # ./setup.py install

Note that you have to install it *outside virtualenvs* so that PostgreSQL can
load it from stored functions.

### Install on *remote* ###

You may install everything in virtualenv if you wish

    $ pip install psycopg2

(that may require your root to install postgresql-server-dev-all and
postgresql-plpython-9.1 packages)

Then

	$ ./setup.py install


Testing
-------

You just have to install psycopg2 on any machine (no system-wide install), to go
for tests.

### Unit tests ###

    $ python -m unittest tests.tests_unit

### Functional tests ###

Functional tests test the code against a reference virtual platform handled
by vagrant.

Prerequisite is to have vagrant installed :

    # apt-get install vagrant virtualbox

and to set it up

    $ vagrant up

Then you can run functional tests :

    $ python -m unittest tests.tests_functional

Getting started
---------------

**NOTICE: that part is not ready right now, those instructions won't work.**

    ./setup.py install

Then you have to write your manifest, let's say it's `manifest.py`
Load it into PostgreSQL with

    $ copiste install manifest.py

Each time you change something in manifest.py you have to run

	$ copiste update manifest.py

… to push the modifications into the db.

