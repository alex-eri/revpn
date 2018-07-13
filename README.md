# revpn

It is an prototype of layer2 vpn over webrtc.

Install
-------

```
git clone https://github.com/alex-eri/revpn.git
pip3 install -r requrements.txt
sudo setcap CAP_NET_ADMIN=ep $(readlink -f /usr/bin/python3)
```

Running
-------

One peer:

```
python3 cli.py offer
```

Another peer:

```
python3 cli.py answer
```

Copy-paste json from offer One to Another, after copy-paste answer from Another to One.

Then setup network with system instruments. I.e.:

```
ip a a 172.16.0.1/24 dev revpn-offer
```

and

```
ip a a 172.16.0.2/24 dev revpn-answer
```

Revpn can run with bridges or dhcp-server, dhcp-client.
