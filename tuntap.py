import os
import fcntl
import struct
import socket
import asyncio

TUNSETIFF = 0x400454ca
TUNSETOWNER = TUNSETIFF + 2
IFF_TUN = 0x0001
IFF_TAP = 0x0002
IFF_NAPI = 0x0010
IFF_NAPI_FRAGS = 0x0020
IFF_NO_PI = 0x1000
IFF_PERSIST = 0x0800
IFF_NOFILTER = 0x1000

# net/if.h
IFF_UP = 0x1
IFF_RUNNING = 0x40
IFNAMSIZ = 16

# From linux/sockios.h
SIOCGIFCONF = 0x8912
SIOCGIFINDEX = 0x8933
SIOCGIFFLAGS = 0x8913
SIOCSIFFLAGS = 0x8914
SIOCGIFHWADDR = 0x8927
SIOCSIFHWADDR = 0x8924
SIOCGIFADDR = 0x8915
SIOCSIFADDR = 0x8916
SIOCGIFNETMASK = 0x891B
SIOCSIFNETMASK = 0x891C
SIOCETHTOOL = 0x8946

SIOCGIFMTU = 0x8921           # get MTU size
SIOCSIFMTU = 0x8922           # set MTU size


class Tun:
    mtu = 1500
    fd = None

    def __init__(self, name, mode="tap", persist=True):
        self.name = name.encode()
        self.tun_flags = IFF_NO_PI
        if persist:
            self.tun_flags |= IFF_PERSIST
        if mode == "tap":
            self.tun_flags |= IFF_TAP
        elif mode == "tun":
            self.tun_flags |= IFF_TUN
        else:
            raise Exception('mode must be tap or tun')
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sockfd = sock

    @property
    def ifflags(self):
        # Get existing device flags
        ifreq = struct.pack('16sh', self.name, 0)
        flags = struct.unpack(
            '16sh',
            fcntl.ioctl(self.sockfd, SIOCGIFFLAGS, ifreq)
            )[1]
        return flags

    @ifflags.setter
    def ifflags(self, flags):
        ifreq = struct.pack('16sh', self.name, flags)
        fcntl.ioctl(self.sockfd, SIOCSIFFLAGS, ifreq)

    def get_mtu(self):
        ifreq = struct.pack('16sh', self.name, 0)
        self.mtu = struct.unpack(
            '16sh',
            fcntl.ioctl(self.sockfd, SIOCGIFMTU, ifreq)
            )[1]

    def up(self):
        ''' Bring up interface. Equivalent to ifconfig [iface] up. '''
        # Set new flags
        flags = self.ifflags | IFF_UP
        self.ifflags = flags
        self.get_mtu()

    def down(self):
        ''' Bring down interface. Equivalent to ifconfig [iface] down. '''
        # Set new flags
        flags = self.ifflags & ~IFF_UP
        self.ifflags = flags

    def is_up(self):
        ''' Return True if the interface is up, False otherwise. '''

        if self.ifflags & IFF_UP:
            return True
        else:
            return False

    def open(self):
        ''' Open file corresponding to the TUN device. '''
        self.fd = open('/dev/net/tun', 'rb+', buffering=0)
        ifr = struct.pack('16sH', self.name, self.tun_flags)
        fcntl.ioctl(self.fd, TUNSETIFF, ifr)
        fcntl.ioctl(self.fd, TUNSETOWNER, os.getuid())

    def connected(self):
        self.ifflags = self.ifflags | IFF_RUNNING

    def disconnected(self):
        self.ifflags = self.ifflags & ~IFF_RUNNING

    def close(self):
        if self.fd:
            self.disconnected()
            self.fd.close()


class TunProtocol(asyncio.Protocol):
    def __init__(self, channel):
        self._channel = channel
        super().__init__()

    def connection_made(self, transport):
        self.transport = transport

    def data_received(self, data):
        self._channel.send(data)
