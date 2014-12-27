import struct
import asyncio
import atexit
import pgex
import mathutils

from . import pgex_export

# TODO better management off the event loop (eg close on unregister)
loop = asyncio.get_event_loop()
atexit.register(loop.close)


class Kind:
    pingpong = 0x01
    logs = 0x02
    ask_screenshot = 0x03
    raw_screenshot = 0x04
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
    writeMessage(writer, Kind.ask_screenshot, b)


def setEye(writer, location, rotation, projection_matrix):
    # sendCmd(writer, 'updateCamera', (_encode_vec3(location), _encode_quat(rotation), _encode_mat4(projection_matrix)))
    cmd = pgex.cmds_pb2.Cmd()
    # cmd.setCamera = pgex.cmds_pb2.SetCamera()
    pgex_export.cnv_vec3ZupToYup(location, cmd.setEye.location)
    pgex_export.cnv_quatZupToYup(rotation, cmd.setEye.rotation)
    pgex_export.cnv_mat4(projection_matrix, cmd.setEye.projection)
    writeMessage(writer, Kind.pgex_cmd, cmd.SerializeToString())


def setData(writer, context, isPreview):
    cmd = pgex.cmds_pb2.Cmd()
    pgex_export.export(context, cmd.setData, isPreview)
    writeMessage(writer, Kind.pgex_cmd, cmd.SerializeToString())


def run_until_complete(f, *args, **kwargs):
    if asyncio.iscoroutine(f):
        loop.run_until_complete(f)
    else:
        coro = asyncio.coroutine(f)
        future = coro(*args, **kwargs)
        loop.run_until_complete(future)
