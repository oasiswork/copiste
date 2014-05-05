Copiste : realtime Postgre → whatyouwant replication
====================================================



Copiste is a python framework to write pg to whatever-your-want trigger-based
  replication, handling all the assle of mainting source code in database and
  passing arbitrary python data to those functions.

- flexible rules (more than just copying fields)
- included functions for LDAP replication
- `copiste` script handles (un)installing triggers/functions in PostgreSQL
- handles the replication of the data that was inside the db before you install
  the hooks (*data initialization*)
- written for replication but can be used for bare notification.

Installing
----------

You can see two different machines in the install/use process :

 - *db* : the host running the database
 - *control* : the host running the copiste commands

 They can be the same host of course.

### Install on *db* ###

    # apt-get install postgresql-plpython-9.1
    # ./setup.py install

Note that you have to install it *outside virtualenvs* so that PostgreSQL can
load it from stored functions.

### Install on *control* ###

You may install everything in virtualenv if you wish

    $ pip install psycopg2

(that may require your root to install postgresql-server-dev-all  package)

Then

	$ ./setup.py install


Writting your manifest
---------------------

Your manifest defines bindings between thos two components :

* **SQL triggers** (a type of event on a specific table)
* **Function** : what is called on trigger

The couple of those two is called a `binding`.

A *Function* can do pretty much anything you want. Several LDAP Writing functions
are included, look at `tests` to know how to use them.

### What you can do with a binding ###

* 'install it' function is stored in db, and trigger is configured to call it
* 'uninstall it' function and trigger are removed from the table
* 'initialize it' the trigger is replayed for each row already existing in the
  table, that's meant to be done right after you install the binding

### Manifest syntax ###

A *Manifest* is a declarative-style python script you store and name as you
want, it sould defines two variables (at least):

* *bindings* a python list of bindings
* *pg_credentials* : a python dict with informations to connec to to your DB.
   Keys are `host`, `user`, `database`, you can also specify `password`, but
   it's recommended not to do so:  you will be prompted at run-time. If you
   don't specify `host`, then, local unix socket will be used.

Here is a minimal manifest.

    import copiste.functions.base
	import copiste.sql
	import copiste.bindings

	pg_credentials =  {
        'host'     : "localhost",
        'user'     : "postgres",
        'database' : "manutest"
    }

	bindings = [
		copiste.binding.Bind(
		    copiste.sql.WriteTrigger(
			    sql_table = 'funky_table',
			    name      = 'on_funky_write'
			),
			copiste.functions.base.LogWarn(msg='Artchung !')
		)
	]

It writes *'Artchung !'* in postgres files each time you write something in the
table `funky_table`.

A *manifest* is meant to be used by the **copiste** command-line tool…

#### Note for ldap-related manifests ####

**Always** use the primary name for ldap field names. Using for eg, using "gn"
  instead of "givenName" may lead to unpredictable results.

You can define a *ldap_credentials*
dict. Like for *pg_credentials*, you may not define the *bind_pw*, it will be
prompted.

Using copiste
-------------

Copiste sets up realtime replication once it's enabled and let you "replay" the
replication against the data that is already in your db to *initialize* your
replica.

Once your *manifest* is written (let's say in `manifest.py`):

Load it into *PostgreSQL* and enable triggers with

    $ copiste install manifest.py

Each time you change something in manifest.py you have to run

	$ copiste uninstall manifest.py
	$ copiste install manifest.py

… to push the modifications into the db.

Initial data
------------

Maybe you had data in your PostgreSQL base before you installed copiste. There
is a mechanism to "replay" the replication triggers on existing data.

    $ copiste init manifest.py

Note that the result of this command might not be idempotent, so if you think
your replicated data is screwed, clear it totally by yourself before you issue
`init`.


Testing
-------

That part is for developpers tests.

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
    $ vagrant provision

Then you can run functional tests :

    $ python -m unittest tests.tests_functional
    $ python -m unittest tests.tests_ldap


You can also run everything (*unit+functional*):

    $ python -m unittest discover


Limitations
-----------

LDAP has no support for transactions and python-ldap has no support of locks, so
it means no support for lock operations.

You can use only one *copiste* *manifest* with a given database, using several
ones is likely to mess it up.
