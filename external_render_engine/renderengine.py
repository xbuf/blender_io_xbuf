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

import bpy
import bgl
# from mathutils import Vector, Matrix
import asyncio
from external_render_engine import bl_info


# gloop = external_render_engine.gloop

# http://wiki.blender.org/index.php/Dev:2.6/Source/Render/RenderEngineAPI
# http://wiki.blender.org/index.php/Dev:2.6/Source/Render/UpdateAPI
# http://www.blender.org/api/blender_python_api_2_72_release/bpy.types.RenderEngine.html


class ExternalRenderEngine(bpy.types.RenderEngine):
    # These three members are used by blender to set up the
    # RenderEngine; define its internal name, visible name and capabilities.
    bl_idname = bl_info["name"]
    bl_label = "External Renderer"
    bl_use_preview = True

    # moved assignment from execute() to the body of the class...
    port = bpy.props.IntProperty(name="port", default=4242, min=1024)
    host = bpy.props.StringProperty(name="host", default="127.0.0.1")

    # TODO better management off the event loop (eg close on unregister)
    loop = asyncio.get_event_loop()

    def __init__(self):
        print("__init__")

    def __del__(self):
        print("__del__")

    @asyncio.coroutine
    def remote_render(self, width, height, flocal):
        # import msgpack
        import struct
        reader, writer = yield from asyncio.open_connection(self.host, self.port, loop=self.loop)
        message = '%rx%s' % (width, height)
        print('Send: %r' % message)
        b = bytearray()
        b.extend((width).to_bytes(4, byteorder='big'))
        b.extend((height).to_bytes(4, byteorder='big'))
        # packed = msgpack.packb([width, height], use_bin_type=True)
        writer.write((len(b)).to_bytes(4, byteorder='big'))
        writer.write((1).to_bytes(1, byteorder='big'))
        writer.write(b)
        # yield from writer.drain()

        header = yield from reader.readexactly(5)
        (size, kind) = struct.unpack('>iB', header)
        # kind = header[4]
        raw = yield from reader.readexactly(size)

        # data = yield from reader.read(-1)
        print('Received %r + %r' % (len(header), len(raw)))

        # raw = [[128, 255, 0, 255]] * (width * height)
        if kind == 2:
            print('draw local image %r' % kind)
            flocal(width, height, raw)

        print('Close the socket')
        writer.close()

    def render(self, scene):
        print("render 55")
        scale = scene.render.resolution_percentage / 100.0
        width = int(scene.render.resolution_x * scale)
        height = int(scene.render.resolution_y * scale)
        coro = self.remote_render(width, height, self.render_image)
        self.loop.run_until_complete(coro)

    def update(self, data, scene):
        """Export scene data for render"""
        print("update")
        if data.objects.is_updated:
            print("One or more objects were updated!")
            for ob in data.objects:
                if ob.is_updated:
                    print("=>", ob.name)

    def view_update(self, context):
        print("view_update")
        # exp = MemoryOpenGexExporter()
        # b = exp.exportToBytes(context)
        # print(b)

    def view_draw(self, context):
        # from http://blender.stackexchange.com/questions/5035/moving-user-perspective-in-blender-with-python
        screen = context.screen.areas[2]
        # r3d = screen.spaces[0].region_3d # region_3d of 3D View
        r3d = context.space_data.region_3d
        # loc = r3d.view_matrix.col[3][1:4]  # translation part of the view matrix
        rot = r3d.view_rotation  # quaternion
        loc = r3d.view_location  # vec3
        projection = r3d.perspective_matrix  # mat4
        width = int(screen.width)
        height = int(screen.height)
        print("view_draw {!r} :: {!r} :: {!r} ::{!r}x{!r}".format(rot, loc, projection, width, height))

        coro = self.remote_render(width, height, self.view_draw_image)
        self.loop.run_until_complete(coro)

    def render_image(self, width, height, raw):
        # TODO optimize the loading/convertion of raw (other renderegine use load_from_file instead of rect)
        # do benchmark array vs list
        data = list()
        for p in range(width * height):
            i = p * 4
            data.append([float(raw[i + 2])/255.0, float(raw[i + 1])/255.0, float(raw[i + 0])/255.0, float(raw[i + 3])/255.0])
            # data.append([float(raw[i + 0]), float(raw[i + 1]), float(raw[i + 2]), float(raw[i + 3])]) # crash

        result = self.begin_result(0, 0, width, height)
        layer = result.layers[0]
        # layer.rect = list(map(lambda i : list(map(lambda c: c/255.0, i)), raw))
        # layer.rect = list(map(lambda c: c/255.0, raw))
        layer.rect = data
        self.end_result(result)

    def view_draw_image(self, width, height, raw):
        # raw = [[0, 255, 0, 255]] * (width * height)
        pixel_count = width * height
        bitmap = bgl.Buffer(bgl.GL_BYTE, [pixel_count * 4], raw)
        # bgl.glBitmap(self.size_x, self.size_y, 0, 0, 0, 0, bitmap)
        bgl.glRasterPos2i(0, 0)
        bgl.glDrawPixels(width, height,
                         # Blender.BGL.GL_BGRA, Blender.BGL.GL_UNSIGNED_BYTE,
                         0x80E1, 0x1401,
                         # bgl.GL_BGRA, bgl.GL_UNSIGNED_BYTE,
                         bitmap
                         )
