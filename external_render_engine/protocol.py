import struct
import asyncio
import atexit
import pgex
import mathutils

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


def setEye(writer, location, rotation, projection_matrix):
    # sendCmd(writer, 'updateCamera', (_encode_vec3(location), _encode_quat(rotation), _encode_mat4(projection_matrix)))
    cmd = pgex.cmds_pb2.Cmd()
    # cmd.setCamera = pgex.cmds_pb2.SetCamera()
    _cnv_vec3ZupToYup(location, cmd.setEye.location)
    _cnv_quatZupToYup(rotation, cmd.setEye.rotation)
    _cnv_mat4(projection_matrix, cmd.setEye.projection)
    writeMessage(writer, Kind.pgex_cmd, cmd.SerializeToString())


def setData(writer, context):
    cmd = pgex.cmds_pb2.Cmd()
    cmd.setData.version = 1
    scene = context.scene
    for obj in scene.objects:
        node = cmd.setData.nodes.add()
        node.id = obj.name
        transform = node.transforms.add()
        #TODO convert zup only for child of root
        _cnv_vec3ZupToYup(obj.location, transform.translation)
        _cnv_quatZupToYup(obj.rotation_quaternion, transform.rotation)
        _cnv_vec3(obj.scale, transform.scale)
    writeMessage(writer, Kind.pgex_cmd, cmd.SerializeToString())


def _cnv_vec3(src, dst):
    # dst = pgex.math_pb2.Vec3()
    # dst.x = src.x
    # dst.y = src.y
    # dst.z = src.z
    dst.x = src[0]
    dst.y = src[1]
    dst.z = src[2]
    return dst


def _cnv_vec3ZupToYup(src, dst):
    # same as src.rotate(Quaternion((1,1,0,0))) # 90 deg CW axis X
    src0 = src.copy()
    q = mathutils.Quaternion((-1, 1, 0, 0))
    q.normalize()
    src0.rotate(q)
    # dst = pgex.math_pb2.Vec3()
    # dst.x = src.x
    # dst.y = src.y
    # dst.z = src.z
    dst.x = src0[0]
    dst.y = src0[1]
    dst.z = src0[2]
    print("_cnv_vec3ZupToYup %r -> %r" % (src, src0))
    return dst


def _cnv_quatZupToYup(src, dst):
    # dst = pgex.math_pb2.Quaternion()
    src0 = src.copy()
    q = mathutils.Quaternion((-1, 1, 0, 0))
    q.normalize()
    src0.rotate(q)
    # orig = src
    # src = mathutils.Quaternion((-1, 1, 0, 0))
    # src.normalize()
    # src.rotate(orig)
    dst.w = src0.w  # [0]
    dst.x = src0.x  # [1]
    dst.y = src0.y  # [2]
    dst.z = src0.z  # [3]
    # dst.x = src[0]
    # dst.y = src[1]
    # dst.z = src[2]
    # dst.w = src[3]
    print("_cnv_quatZupToYup %r -> %r" % (src, src0))
    return dst


def _cnv_quat(src, dst):
    # dst = pgex.math_pb2.Quaternion()
    dst.x = src.x  # [1]
    dst.y = src.y  # [2]
    dst.z = src.z  # [3]
    dst.w = src.w  # [0]
    # dst.x = src[0]
    # dst.y = src[1]
    # dst.z = src[2]
    # dst.w = src[3]
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
