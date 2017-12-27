#!/bin/bash

sleep 3

#kill all java
killall -v java
sleep 1

#run VNF1
java -jar vnf1.jar VNF1.properties


