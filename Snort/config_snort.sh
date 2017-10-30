#!/bin/bash

wget https://raw.githubusercontent.com/akhtarnabeel/public/master/Snort/snort.conf

sudo mv snort.conf /etc/snort

sudo touch /etc/snort/rules/my.rules

sudo chmod 755 /etc/snort/snort.conf

sudo chmod 755 /etc/snort/rules/my.rules
