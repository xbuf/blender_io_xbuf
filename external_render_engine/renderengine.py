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
import asyncio
from . import protocol  # pylint: disable=W0406
from . import helpers   # pylint: disable=W0406

# gloop = external_render_engine.gloop

# http://wiki.blender.org/index.php/Dev:2.6/Source/Render/RenderEngineAPI
# http://wiki.blender.org/index.php/Dev:2.6/Source/Render/UpdateAPI
# http://www.blender.org/api/blender_python_api_2_72_release/bpy.types.RenderEngine.html


class ExternalRenderEngine(bpy.types.RenderEngine):
    # These three members are used by blender to set up the
    # RenderEngine; define its internal name, visible name and capabilities.
    bl_idname = "external_render"
    bl_label = "External Render"
    bl_use_preview = False

    # moved assignment from execute() to the body of the class...
    port = bpy.props.IntProperty(name="port", default=4242, min=1024)
    host = bpy.props.StringProperty(name="host", default="127.0.0.1")

    def __init__(self):
        print("__init__")
        self.client = protocol.Client()

    def __del__(self):
        print("__del__")
        if hasattr(self, 'client'):
            self.client.close()

    def external_render(self, context_or_camera, width, height, flocal):
        (loc, rot, projection, near, far) = helpers.extractEye(context_or_camera)

        @asyncio.coroutine
        def my_render():
            try:
                self.report({'WARNING'}, "test remote host (%r:%r)" % (self.host, self.port))
                yield from self.client.connect(self.host, self.port)
                print('Send: %rx%r' % (width, height))
                protocol.setEye(self.client.writer, loc, rot, projection, near, far)
                protocol.askScreenshot(self.client.writer, width, height)
                # yield from writer.drain()

                (kind, raw) = yield from protocol.readMessage(self.client.reader)
                # raw = [[128, 255, 0, 255]] * (width * height)
                if kind == protocol.Kind.raw_screenshot:
                    flocal(width, height, raw)
            except BrokenPipeError:
                self.report({'WARNING'}, "failed to connect to remote host (%r:%r)" % (self.host, self.port))
                self.client.close()
        protocol.run_until_complete(my_render())

    def render(self, scene):
        scale = scene.render.resolution_percentage / 100.0
        width = int(scene.render.resolution_x * scale)
        height = int(scene.render.resolution_y * scale)
        # context.space_data.camera
        # self.external_render(scene.camera, width, height, self.render_image)

    def update(self, data, scene):
        """Export scene data for render"""
        self.report({'DEBUG'}, "update")
        self.external_update(scene)

    def view_update(self, context):
        self.report({'DEBUG'}, "view_update")
        self.external_update(context.scene)

    def external_update(self, scene):
        self.report({'DEBUG'}, "external_update")
        for ob in scene.objects:
            if ob.is_updated:
                print("updated =>", ob.name)

        @asyncio.coroutine
        def my_update():
            try:
                yield from self.client.connect(self.host, self.port)
                protocol.setData(self.client.writer, scene, False)
            except BrokenPipeError:
                self.report({'WARNING'}, "failed to connect to remote host (%r:%r)" % (self.host, self.port))
                self.client.close()
        protocol.run_until_complete(my_update())

    def view_draw(self, context):
        self.report({'DEBUG'}, "view_draw")
        # self.view_update(context)
        # from http://blender.stackexchange.com/questions/5035/moving-user-perspective-in-blender-with-python
        # area = context.area
        # area = context.screen.areas[2]
        # r3d = area.spaces[0].region_3d # region_3d of 3D View
        # for area in bpy.context.screen.areas:
        # if area.type=='VIEW_3D':
        #         break
        #
        # space = area.spaces[0]
        # region = area.regions[4]
        # rv3d = context.space_data.region_3d
        # loc = r3d.view_matrix.col[3][1:4]  # translation part of the view matrix
        region = context.region  # area.regions[4]
        width = int(region.width)
        height = int(region.height)
        self.external_render(context, width, height, self.view_draw_image)

    def render_image(self, width, height, raw):
        # TODO optimize the loading/convertion of raw (other renderegine use load_from_file instead of rect)
        # do benchmark array vs list
        # convert raw (1D,brga, byte) into rect (2D, rgba, float [0,1])

        # data = list()
        # for p in range(width * height):
        #     i = p * 4
        #     data.append([float(raw[i + 2])/255.0, float(raw[i + 1])/255.0, float(raw[i + 0])/255.0, float(raw[i + 3])/255.0])
        #     # data.append([float(raw[i + 0]), float(raw[i + 1]), float(raw[i + 2]), float(raw[i + 3])]) # crash
        #
        # # data = [[float(raw[i + 2])/255.0, float(raw[i + 1])/255.0, float(raw[i + 0])/255.0, float(raw[i + 3])/255.0] for p in range(width * height) i = p * 4]
        # pylint: disable=E1103
        import numpy
        # print("w * h : %r   len/4 : %s" % (width*height, len(raw)/4))
        data = numpy.fromstring(raw, dtype=numpy.byte).astype(numpy.float)
        data = numpy.reshape(data, (len(raw)/4, 4))
        reorder = numpy.array([2, 1, 0, 3])
        data = data[:, reorder]
        divfunc = numpy.vectorize(lambda a: a / 255.0)
        data = divfunc(data)
        # pylint: enable=E1103

        result = self.begin_result(0, 0, width, height)
        layer = result.layers[0]
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
