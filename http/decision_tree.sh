# Get data to generate the HTTP decision tree

sudo pkill dd

declare -a size_arr=("10KB" "1MB")
declare -a p_arr=(0.001 0.01)
declare -a rtt_arr=(50 200)
declare -a num_arr=(10 500)

uptime=0
last_time=0

IP="xxx.xxx.xxx.xxx"

index=0
threshold=0

for rtt in "${rtt_arr[@]}"; do
    for filesize in "${size_arr[@]}"; do
        for num in "${num_arr[@]}"; do
            for p in "${p_arr[@]}"; do
                index=$((index + 1))
                if [ $index -lt $threshold ]; then
                    continue
                fi
                echo $filesize
                echo $p

                # Change TC config
                sudo tc qdisc del dev enp6s0 root
                sudo tc qdisc add dev enp6s0 root netem delay ${rtt}ms loss ${p}%
                dd if=/proc/net/tcpprobe ibs=128 obs=128 | grep ${IP} > /var/www/html/http_test/test.txt &
                TCPPROBE=$!

                sleep 3
                echo '' > /var/www/html/http_test/php.txt
                touch /var/www/html/http_test/finished.txt
                chown www-data:www-data /var/www/html/http_test/test.txt
                chown www-data:www-data /var/www/html/http_test/php.txt
                chown www-data:www-data /var/www/html/http_test/finished.txt
                time=0
                flag=1
                while [ $flag -eq 1 ]; do
                    lines=$(echo $d | cat /var/www/html/http_test/finished.txt | wc -l)
                    if [ $lines -eq 1 ]; then
                        break;
                    fi
                    sleep 3
                    time=$((time + 3))
                    uptime=$((uptime + 3))
                    if [ $time -gt 3600 ]; then
                        sudo tc qdisc del dev enp6s0 root
                        echo WRONG!
                        flag=0
                        break;
                    fi
                done
                echo Job finished!
                kill $TCPPROBE
                sleep 1

                # Save tcpprobe and timing logs
                mv /var/www/html/http_test/test.txt /var/www/html/http_test/$filesize-$p-$rtt-$num.txt
                mv /var/www/html/http_test/php.txt /var/www/html/http_test/$filesize-$p-$rtt-$num-start.txt

                # Create a folder and mv the files
                mkdir /var/www/html/http_test/$filesize-$p-$rtt-$num
                mv /var/www/html/http_test/$filesize-$p-$rtt-$num.txt /var/www/html/http_test/$filesize-$p-$rtt-$num-start.txt /var/www/html/http_test/$filesize-$p-$rtt-$num

                rm /var/www/html/http_test/finished.txt
            done
        done
    done
done
sudo tc qdisc del dev enp6s0 root
