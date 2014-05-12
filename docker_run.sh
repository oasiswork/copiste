#!/bin/bash

PIPEWORK=${PIPEWORK:-false}
SSH_KEYS=${SSH_KEYS:-''}

[ -n "$SSH_KEY" ] && {
    mkdir -p /home/copiste/.ssh
    IFS=';'; for key in $SSH_KEYS; do
        echo "$key" >> /home/copiste/.ssh/authorized_keys
    done
    chown -R copiste.copiste /home/copiste/.ssh
}

$PIPEWORK && {
    echo 'Waiting for pipework interface...'
    /scripts/pipework --wait
}

/usr/sbin/sshd -D
