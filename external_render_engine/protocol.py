import struct
import asyncio
import atexit
import msgpack

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


def writeMessage(writer, kind, body):
    writer.write((len(body)).to_bytes(4, byteorder='big'))
    writer.write((kind).to_bytes(1, byteorder='big'))
    writer.write(body)


def askScreenshot(writer, width, height):
    b = bytearray()
    b.extend((width).to_bytes(4, byteorder='big'))
    b.extend((height).to_bytes(4, byteorder='big'))
    writeMessage(writer, Kind.askScreenshot, b)


def updateCamera(writer, location, rotation, projection_matrix):
    sendCmd(writer, 'updateCamera', (_encode_vec3(location), _encode_quat(rotation), _encode_mat4(projection_matrix)))


def sendCmd(writer, method, args):
    b = bytearray()
    b.extend(msgpack.packb(method, use_bin_type=True))
    b.extend(msgpack.packb(args, use_bin_type=True))
    writeMessage(writer, Kind.msgpack, b)


def _encode_vec3(v3):
    return (v3.x, v3.y, v3.z)


def _encode_quat(q):
    return (q.x, q.y, q.z, q.w)


def _encode_mat4(mat4):
    return (
        mat4.col[0][0], mat4.col[1][0], mat4.col[2][0], mat4.col[3][0],
        mat4.col[0][1], mat4.col[1][1], mat4.col[2][1], mat4.col[3][1],
        mat4.col[0][2], mat4.col[1][2], mat4.col[2][2], mat4.col[3][2],
        mat4.col[0][3], mat4.col[1][3], mat4.col[2][3], mat4.col[3][3],
    )


def run_until_complete(f, *args, **kwargs):
    if asyncio.iscoroutine(f):
        loop.run_until_complete(f)
    else:
        coro = asyncio.coroutine(f)
        future = coro(*args, **kwargs)
        loop.run_until_complete(future)
