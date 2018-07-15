import argparse
import asyncio
import logging
from aiortc import RTCPeerConnection
from signaling import CopyAndPasteSignaling
import tuntap
import sys
import functools


def channel_log(channel, t, message):
    logging.info('channel(%s) %s %s' % (channel.label, t, repr(message)))


def create_pc():
    pc = RTCPeerConnection()

    @pc.on('datachannel')
    def on_datachannel(channel):
        channel_log(channel, '-', 'created by remote party')
    return pc


def tun_reader(channel, tap):
    data = tap.fd.read(tap.mtu)
    if data:
        channel.send(data)


def line_reader(channel, fd):
    data = fd.readline()
    if data:
        channel.send(data)


def on_message(message):
    sys.stdout.write('\r< ')
    sys.stdout.write(message)
    sys.stdout.write('> ')
    sys.stdout.flush()


def on_packet(tap, data):
    tap.fd.write(data)


async def run_answer(pc, tap):
    done = asyncio.Event()

    @pc.on('datachannel')
    def on_datachannel(channel):
        loop = asyncio.get_event_loop()
        if channel.label == 'vpntap':
            tap.connected()
            loop.add_reader(
                tap.fd, functools.partial(tun_reader, channel, tap)
                )
            channel.on('message')(functools.partial(on_packet, tap))

        elif channel.label == 'chat':
            loop.add_reader(
                sys.stdin, functools.partial(line_reader, channel, sys.stdin)
                )
            channel.on('message')(on_message)
            print('> ', end='')


    # receive offer
    offer = await signaling.receive()
    await pc.setRemoteDescription(offer)

    # send answer
    await pc.setLocalDescription(await pc.createAnswer())
    await signaling.send(pc.localDescription)
    return done


async def run_offer(pc, tap):
    done = asyncio.Event()

    channel = pc.createDataChannel('vpntap')
    channel_log(channel, '-', 'created by local party')
    channel.on('message')(functools.partial(on_packet, tap))

    chat = pc.createDataChannel('chat')
    channel_log(chat, '-', 'created by local party')
    chat.on('message')(on_message)

    # send offer
    await pc.setLocalDescription(await pc.createOffer())
    await signaling.send(pc.localDescription)

    # receive answer
    answer = await signaling.receive()
    await pc.setRemoteDescription(answer)

    tap.connected()

    # send message
    loop = asyncio.get_event_loop()
    loop.add_reader(tap.fd, functools.partial(tun_reader, channel, tap))
    loop.add_reader(
        sys.stdin, functools.partial(line_reader, chat, sys.stdin)
        )
    print('> ', end='')
    return done


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Data channels with copy-and-paste signaling')
    parser.add_argument('role', choices=['offer', 'answer'])
    parser.add_argument('--verbose', '-v', action='count')
    parser.add_argument('--persist', '-p', action='count')
    parser.add_argument('--mode', '-m', choices=['tap', 'tun'], default="tap")
    args = parser.parse_args()

    if args.verbose and args.verbose > 1:
        logging.basicConfig(level=logging.DEBUG)
    elif args.verbose:
        logging.basicConfig(level=logging.INFO)

    tap = tuntap.Tun(name="revpn-%s" % args.role, mode=args.mode, persist=args.persist)
    tap.open()

    pc = create_pc()
    signaling = CopyAndPasteSignaling()
    if args.role == 'offer':
        coro = run_offer(pc, tap)
    else:
        coro = run_answer(pc, tap)

    # run event loop
    loop = asyncio.get_event_loop()
    done = loop.run_until_complete(coro)

    tap.up()
    try:
        loop.run_until_complete(done.wait())
    except KeyboardInterrupt:
        done.set()
    finally:
        loop.run_until_complete(pc.close())
        tap.close()
