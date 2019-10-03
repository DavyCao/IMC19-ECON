# Get iperf entries from the tcpprobe log

> test.txt
for tcp_num in `seq 1 10`
do
    echo TCP_num: $tcp_num
    for client_index in `seq 1 10`
    do
        echo Client_index: $client_index
        head -n 10000 /home/yi/hdisk/zclient${client_index}_${tcp_num}.log | awk '{print $2}' | awk 'length($0)==14' | cut -c 10-14 | sort | uniq > test.txt
        lines=$(echo $a | wc -l < test.txt)
        echo Total Ports: $lines
        # Check if involves other ports
        while [ "$lines" -gt "$tcp_num" ]
        do
            val1=$(echo $b | sed "1q;d" test.txt)
            val2=$(echo $c | sed "2q;d" test.txt)
            if [ $((val2-val1)) -ne 2 ] ; then
            sed '1d' test.txt > temp.txt
            mv temp.txt test.txt
            else
            sed '$d' test.txt > temp.txt
            mv temp.txt test.txt
            fi
            lines=$(echo $d | wc -l < test.txt)
        done
        # Finish checking
        for port_index in `seq 1 ${tcp_num}`
            do
            port=$(echo $e | sed "${port_index}q;d" test.txt)
            echo $port
            cat /home/yi/hdisk/zclient${client_index}_${tcp_num}.log | grep $port > /home/yi/hdisk/zclient${client_index}_${tcp_num}_${port}.log 
        done
        echo
    done
done
