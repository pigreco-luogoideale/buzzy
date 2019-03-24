#!/bin/sh

# Start the redis server in daemon mode
echo "Starting redis..."
REDIS=$(sudo docker run -d --rm --network=host redis:alpine)

# Start hotspot with customized dnsmasq
nmcli conn up Hotspot

# Stop firewall
sudo systemctl stop firewalld.service

# Start game server
sudo ./ambiente/bin/uvicorn --host=0.0.0.0 --port=80 buzzy.main:app

# Kill redis
sudo docker stop $REDIS
