# This file is part of external_render_engine.  external_render_engine is free software: you can
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
import pgex
import pgex.datas_pb2
import pgex.cmds_pb2

from . import pgex_export  # pylint: disable=W0406

# TODO better management off the event loop (eg  on unregister)
loop = asyncio.get_event_loop()
atexit.register(loop.close)


class Kind:
    pingpong = 0x01
    logs = 0x02
    ask_screenshot = 0x03
    raw_screenshot = 0x04
    msgpack = 0x05
    pgex_cmd = 0x06


class Client:

    def __init__(self):
        self.writer = None
        self.reader = None
        self.host = None
        self.port = None

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


def setEye(writer, location, rotation, projection_matrix, near, far):
    # sendCmd(writer, 'updateCamera', (_encode_vec3(location), _encode_quat(rotation), _encode_mat4(projection_matrix)))
    cmd = pgex.cmds_pb2.Cmd()
    # cmd.setCamera = pgex.cmds_pb2.SetCamera()
    pgex_export.cnv_vec3ZupToYup(location, cmd.setEye.location)
    pgex_export.cnv_quatZupToYup(rotation, cmd.setEye.rotation)
    pgex_export.cnv_mat4(projection_matrix, cmd.setEye.projection)
    cmd.setEye.near = near
    cmd.setEye.far = far
    writeMessage(writer, Kind.pgex_cmd, cmd.SerializeToString())


def setData(writer, scene, cfg):
    cmd = pgex.cmds_pb2.Cmd()
    pgex_export.export(scene, cmd.setData, cfg)
    writeMessage(writer, Kind.pgex_cmd, cmd.SerializeToString())


def changeAssetFolders(writer, cfg):
    cmd = pgex.cmds_pb2.Cmd()
    cmd.changeAssetFolders.path.append(cfg.assets_path)
    cmd.changeAssetFolders.register = True
    cmd.changeAssetFolders.unregisterOther = True
    writeMessage(writer, Kind.pgex_cmd, cmd.SerializeToString())


def run_until_complete(f, *args, **kwargs):
    if asyncio.iscoroutine(f):
        loop.run_until_complete(f)
    else:
        coro = asyncio.coroutine(f)
        future = coro(*args, **kwargs)
        loop.run_until_complete(future)
