#!/bin/bash

#kill all java processes

killall -v java
sleep 1

#run IDD

cd IDD-DNS/IDD

java -jar IDD.jar idd.properties &
sleep 1

#run DNS

cd ../DNS

java -jar RINADNSServer.jar dns.properties &
sleep 1

cd ../../


# run RINA controller app
sleep 1
java -jar controller.jar controller.properties



