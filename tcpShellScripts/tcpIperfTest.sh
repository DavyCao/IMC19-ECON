#!/bin/sh
pkill iperf
pkill tcpprobe
pkill tcp_probe
pkill cat

IP="xxx.xxx.xxx.xxx"

for i in `seq 1 10`
do
for Counts in  `seq 1 10`
do
modprobe -r tcp_probe
modprobe tcp_probe port=0 full=1
chmod 444 /proc/net/tcpprobe
cat /proc/net/tcpprobe | grep ${IP} > /media/yi/tcpExp/tcpprobe_multiple_${Counts}_$i.txt &
iperf -f m -c ${IP} -p5001 -i 10 -t 100  -P ${Counts}
pkill cat
done
done
