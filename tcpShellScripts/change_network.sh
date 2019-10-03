# Test for dynamic network conditions

#===Increase p===
sudo tc qdisc del dev enp6s0 root
sudo tc qdisc add dev enp6s0 root netem delay 100ms loss 0.01%

modprobe -r tcp_probe
modprobe tcp_probe port=0 full=1
chmod 444 /proc/net/tcpprobe

IP="xxx.xxx.xxx.xxx"

cat /proc/net/tcpprobe | grep ${IP} > /media/yi/change_network.txt &
TCPCAP=$!
iperf -f m -c ${IP} -p5001 -i 10 -t 3600 &
IPERF=$!
time=0

while true; do
    sleep 5
    time=$((time + 5))
    if [ $time -gt 120 ]; then
        # Increase P
	    sudo tc qdisc change dev enp6s0 root netem delay 100ms loss 0.1%
    fi

    if [ $time -gt 240 ]; then
        # Decrease P
        sudo tc qdisc change dev enp6s0 root netem delay 100ms loss 0.001%
    fi

    if [ $time -gt 360 ]; then
        # Increase RTT
        sudo tc qdisc change dev enp6s0 root netem delay 200ms loss 0.01%
        flag=0
    fi
    
    if [ $time -gt 480 ]; then
        # Decrease RTT
        sudo tc qdisc change dev enp6s0 root netem delay 50ms loss 0.01%
        flag=0
    fi

    if [ $time -gt 600 ]; then
        echo Timeup!
        break;
    fi
done

sudo tc qdisc del dev enp6s0 root
kill $IPERF
kill $TCPCAP
