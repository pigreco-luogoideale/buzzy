# Buzzy

Multi-player buzzers in Python and Websocket!

## Running

These instructions are for the following setup:

 - your computer (server) will expose a WiFi Hotspot network and run buzzy;
 - other computers/smartphones will connect to your network for easy play.

This software has been built and tested on a Fedora 29 Linux box, but should
work similarly on any Linux box using NetworkManager. Docker is used for
easier setup of the required servers (redis).

Providing a WiFi hotspot is not required and any player can join as long as
your box is reachable in the same network (e.g. same WiFi SSID).

NetwokManager (on Fedora and likely on Ubuntu as well) will run dnsmasq  when
sharing a network connection to provide a dhcp server to connected clients.
To make life easier for the player, we will setup your dnsmasq so that users
will not have to type `http://10.42.0.1:8000` on their phone, but will just
type `http://game`. This helps a lot when the audience is non-technical.

1. First, [create and a wifi hotspot](https://gist.github.com/narate/d3f001c97e1c981a59f94cd76f041140)
   and make sure it is working. People will have to connect to it if you don't
   want to use a 3rd party network.

2. Configure NetworkManager's dnsmasq by creating the following file:

    # /etc/NetworkManager/dnsmasq-shared.d/hosts.conf
    address=/game/10.42.0.1

where `game` is the host name that will be redirected to `10.42.0.1`. Be sure
to check that `10.42.0.1` is your ip address as well when you run a WiFi
hotspot, or this will not work.

3. Start your hotspot connection:

	nmcli conn up Hotspot

4. To run your game on port 80 and have users to connect without writing the
   port, ensure your firewall let incoming traffic on port 80, or disable it

	sudo systemctl stop firewalld.service

5. Now, we are ready to start the actual server (optionally in a virtualenv):

	REDIS=$(sudo docker run -d --rm --network=host redis:alpine)
	sudo uvicorn --host=0.0.0.0 --port=80 buzzy.main:app
	sudo docker stop $REDIS

