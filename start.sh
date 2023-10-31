#! /bin/bash
touch test.txt
mkdir -p /dev/net 
mknod /dev/net/tun c 10 200
chmod 600 /dev/net/tun

ufw enable
service openvpn start
sleep 30
counter=0
timeout=3
echo "awaiting curl to succeed"
while true; do
    echo "Not yet connected"
    counter=$((counter+1))
    result=$(curl -s --max-time $timeout ifconfig.me)
    if [ -n "$result" ]; then
        echo -e "\nConnected (Attempt $counter)"
        echo "Current IP address: $result"
        break  # Exit the loop if 'curl ifconfig.me' returns a result
    else
        
        echo -ne "Not yet connected (Attempt $counter)\r"
    fi

    
    sleep 5  # Adjust the interval as needed
done
echo "starting python script"
python3 rabbitmq_server.py  