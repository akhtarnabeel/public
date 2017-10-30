#!/bin/bash

wget http://csr.bu.edu/rina/grw-bu2016/nfv_ryu/snort/snort.conf

sudo mv snort.conf /etc/snort

sudo touch /etc/snort/rules/my.rules

sudo chmod 755 /etc/snort/snort.conf

sudo chmod 755 /etc/snort/rules/my.rules
