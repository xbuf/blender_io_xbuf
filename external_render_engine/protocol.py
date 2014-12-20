import struct
import asyncio
import atexit
import pgex

# TODO better management off the event loop (eg close on unregister)
loop = asyncio.get_event_loop()
atexit.register(loop.close)


class Kind:
    pingpong = 0x01
    logs = 0x02
    askScreenshot = 0x03
    rawScreenshot = 0x04
    msgpack = 0x05
    pgex_cmd = 0x06


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


def setCamera(writer, location, rotation, projection_matrix):
    # sendCmd(writer, 'updateCamera', (_encode_vec3(location), _encode_quat(rotation), _encode_mat4(projection_matrix)))
    cmd = pgex.cmds_pb2.Cmd()
    # cmd.setCamera = pgex.cmds_pb2.SetCamera()
    _cnv_vec3(location, cmd.setCamera.location)
    _cnv_quat(rotation, cmd.setCamera.rotation)
    _cnv_mat4(projection_matrix, cmd.setCamera.projection)
    writeMessage(writer, Kind.pgex_cmd, cmd.SerializeToString())


def _cnv_vec3(src, dst):
    # dst = pgex.math_pb2.Vec3()
    dst.x = src.x
    dst.y = src.y
    dst.z = src.z
    return dst


def _cnv_quat(src, dst):
    # dst = pgex.math_pb2.Quaternion()
    dst.x = src.x
    dst.y = src.y
    dst.z = src.z
    dst.w = src.w
    return dst


def _cnv_mat4(src, dst):
    # dst = pgex.math_pb2.Quaternion()
    dst.c00 = src.col[0][0]
    dst.c10 = src.col[1][0]
    dst.c20 = src.col[2][0]
    dst.c30 = src.col[3][0]
    dst.c01 = src.col[0][1]
    dst.c11 = src.col[1][1]
    dst.c21 = src.col[2][1]
    dst.c31 = src.col[3][1]
    dst.c02 = src.col[0][2]
    dst.c12 = src.col[1][2]
    dst.c22 = src.col[2][2]
    dst.c32 = src.col[3][2]
    dst.c03 = src.col[0][3]
    dst.c13 = src.col[1][3]
    dst.c23 = src.col[2][3]
    dst.c33 = src.col[3][3]
    return dst

def run_until_complete(f, *args, **kwargs):
    if asyncio.iscoroutine(f):
        loop.run_until_complete(f)
    else:
        coro = asyncio.coroutine(f)
        future = coro(*args, **kwargs)
        loop.run_until_complete(future)
