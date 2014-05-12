FROM oasis/base:14.04
MAINTAINER Oasiswork <dev@oasiswork.fr>

RUN apt-get install -y python python-setuptools python-psycopg2 python-ldap postgresql-server-dev-all openssh-server
RUN apt-get clean

# Restrict SSH access and avoid locale related warnings
RUN mkdir /var/run/sshd
RUN locale-gen en_US.UTF-8
RUN echo 'LANG="en_US.UTF-8"' > /etc/default/locale
RUN sed -i 's/^AcceptEnv LANG LC_\*$//g' /etc/ssh/sshd_config
RUN echo 'PasswordAuthentication no' >> /etc/ssh/sshd_config
RUN echo 'PubkeyAuthentication yes' >> /etc/ssh/sshd_config
RUN echo 'AllowUsers copiste' >> /etc/ssh/sshd_config

# Install copiste and cleanup after ourselves
RUN mkdir /tmp/copiste
ADD bin /tmp/copiste/bin
ADD copiste /tmp/copiste/copiste
ADD setup.py /tmp/copiste/setup.py
RUN cd /tmp/copiste && python -m unittest tests.tests_unit
RUN cd /tmp/copiste && python setup.py install
RUN rm -rf /tmp/copiste

# Add copiste user and run script
RUN adduser --disabled-password copiste
ADD docker_run.sh /scripts/run
RUN chmod +x /script/run

CMD /script/run
