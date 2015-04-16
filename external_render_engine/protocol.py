# This file is part of blender_io_xbuf.  blender_io_xbuf is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright David Bernard

# <pep8 compliant>

import struct
import asyncio
import atexit
import xbuf
import xbuf.datas_pb2
import xbuf.cmds_pb2

from . import xbuf_export  # pylint: disable=W0406

# TODO better management off the event loop (eg  on unregister)
loop = asyncio.get_event_loop()
atexit.register(loop.close)


class Kind:
    pingpong = 0x01
    logs = 0x02
    ask_screenshot = 0x03
    raw_screenshot = 0x04
    msgpack = 0x05
    xbuf_cmd = 0x06


class Client:

    def __init__(self):
        self.writer = None
        self.reader = None
        self.host = None
        self.port = None

    def __del__(self):
        self.close()

    def close(self):
        if self.writer is not None:
            print('Close the socket/writer')
            self.writer.write_eof()
            self.writer.close()
            self.writer = None
            self.reader = None

    @asyncio.coroutine
    def connect(self, host, port):
        if (host != self.host) or (port != self.port):
            self.close()
        if self.writer is None:
            self.host = host
            self.port = port
            (self.reader, self.writer) = yield from asyncio.open_connection(host, port, loop=loop)
        return self


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


def setEye(writer, location, rotation, projection_matrix, near, far, is_ortho):
    # sendCmd(writer, 'updateCamera', (_encode_vec3(location), _encode_quat(rotation), _encode_mat4(projection_matrix)))
    cmd = xbuf.cmds_pb2.Cmd()
    # cmd.setCamera = xbuf.cmds_pb2.SetCamera()
    xbuf_export.cnv_translation(location, cmd.setEye.location)
    xbuf_export.cnv_quatZupToYup(rotation, cmd.setEye.rotation)
    xbuf_export.cnv_mat4(projection_matrix, cmd.setEye.projection)
    cmd.setEye.near = near
    cmd.setEye.far = far
    cmd.setEye.projMode = xbuf.cmds_pb2.SetEye.orthographic if is_ortho else xbuf.cmds_pb2.SetEye.perspective
    writeMessage(writer, Kind.xbuf_cmd, cmd.SerializeToString())


def setData(writer, scene, cfg):
    cmd = xbuf.cmds_pb2.Cmd()
    xbuf_export.export(scene, cmd.setData, cfg)
    send = (len(cmd.setData.relations) > 0 or
            len(cmd.setData.tobjects) > 0 or
            len(cmd.setData.geometries) > 0 or
            len(cmd.setData.materials) > 0 or
            len(cmd.setData.lights) > 0
            )
    if send:
        # print("send setData")
        writeMessage(writer, Kind.xbuf_cmd, cmd.SerializeToString())


def changeAssetFolders(writer, cfg):
    cmd = xbuf.cmds_pb2.Cmd()
    cmd.changeAssetFolders.path.append(cfg.assets_path)
    cmd.changeAssetFolders.register = True
    cmd.changeAssetFolders.unregisterOther = True
    writeMessage(writer, Kind.xbuf_cmd, cmd.SerializeToString())


def playAnimation(writer, ref, anims):
    cmd = xbuf.cmds_pb2.Cmd()
    cmd.playAnimation.ref = ref
    cmd.playAnimation.animationsNames.extend(anims)
    writeMessage(writer, Kind.xbuf_cmd, cmd.SerializeToString())


def run_until_complete(f, *args, **kwargs):
    if asyncio.iscoroutine(f):
        loop.run_until_complete(f)
    else:
        coro = asyncio.coroutine(f)
        future = coro(*args, **kwargs)
        loop.run_until_complete(future)
