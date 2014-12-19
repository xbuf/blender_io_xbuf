import struct
import asyncio
import atexit

# TODO better management off the event loop (eg close on unregister)
loop = asyncio.get_event_loop()
atexit.register(loop.close)

class Kind:
    pingpong = 0x01
    logs = 0x02
    askScreenshot = 0x03
    rawScreenshot = 0x04
    msgpack = 0x05


@asyncio.coroutine
def streams(host, port):
    """return (reader, writer)"""
    reader, writer = yield from asyncio.open_connection(host, port, loop=loop)
    return (reader, writer)


@asyncio.coroutine
def readHeader(reader):
    """return (size, kind)"""
    header = yield from reader.readexactly(5)
    return struct.unpack('>iB', header)


@asyncio.coroutine
def readMessage(reader):
    """return (kind, raw_message)"""
    (size, kind) = yield from readHeader(reader)
    # kind = header[4]
    raw = yield from reader.readexactly(size)
    return (kind, raw)


def askScreenshot(writer, width, height):
    b = bytearray()
    b.extend((width).to_bytes(4, byteorder='big'))
    b.extend((height).to_bytes(4, byteorder='big'))
    # packed = msgpack.packb([width, height], use_bin_type=True)
    writer.write((len(b)).to_bytes(4, byteorder='big'))
    writer.write((Kind.askScreenshot).to_bytes(1, byteorder='big'))
    writer.write(b)


def run_until_complete(f, *args, **kwargs):
    if asyncio.iscoroutine(f):
        loop.run_until_complete(f)
    else:
        coro = asyncio.coroutine(f)
        future = coro(*args, **kwargs)
        loop.run_until_complete(future)
