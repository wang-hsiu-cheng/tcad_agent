#!/bin/bash

mkdir -p /root/.ssh
chmod 700 /root/.ssh

cp /mnt/config /root/.ssh/config
chmod 600 /root/.ssh/*

exec "$@"