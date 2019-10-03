#!/usr/bin/env bash

# Filter the http entries from the tcpprobe log
declare -a arr=("element1" "element2" "element3")
declare -a rtt=("50" "200")
declare -a size=("10KB" "1MB")
declare -a num=("10" "500")
declare -a p=("0.001" "0.01")

for y in "${rtt[@]}";
do
    for a in "${size[@]}";
    do
        for b in "${num[@]}";
        do
            for c in "${p[@]}";
            do
                > test.txt
                file=/var/www/html/http_test/$a-$c-$y-$b/$a-$c-$y-$b.txt
                echo $file
                tcp_num=7
                head -1000 $file | awk '{print $3}' | awk 'length($0)==20' | cut -c 16-20 | sort | uniq > test.txt
                lines=$(echo $a | wc -l < test.txt)
                echo Total Ports: $lines
                tcp_num=$lines
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
                    prefix=${file%????}
                    cat $file | grep $port > $prefix-port$port.txt
                done
                echo
                sed -i '$d' $prefix-port$port.txt
            done
        done
    done
done
