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
from . import protocol

# gloop = external_render_engine.gloop

# http://wiki.blender.org/index.php/Dev:2.6/Source/Render/RenderEngineAPI
# http://wiki.blender.org/index.php/Dev:2.6/Source/Render/UpdateAPI
# http://www.blender.org/api/blender_python_api_2_72_release/bpy.types.RenderEngine.html


class ExternalRenderEngine(bpy.types.RenderEngine):
    # These three members are used by blender to set up the
    # RenderEngine; define its internal name, visible name and capabilities.
    bl_idname = "external_renderer"
    bl_label = "External Renderer"
    bl_use_preview = True

    # moved assignment from execute() to the body of the class...
    port = bpy.props.IntProperty(name="port", default=4242, min=1024)
    host = bpy.props.StringProperty(name="host", default="127.0.0.1")

    def __init__(self):
        print("__init__")

    def __del__(self):
        print("__del__")

    @asyncio.coroutine
    def remote_render(self, width, height, flocal):
        (reader, writer) = yield from protocol.streams(self.host, self.port)
        print('Send: %rx%r' % (width, height))
        protocol.askScreenshot(writer, width, height)
        # yield from writer.drain()

        (kind, raw) = yield from protocol.readMessage(reader)
        # raw = [[128, 255, 0, 255]] * (width * height)
        if kind == protocol.Kind.rawScreenshot:
            print('draw local image %r' % kind)
            flocal(width, height, raw)

        print('Close the socket')
        writer.close()

    def render(self, scene):
        print("render 44")
        scale = scene.render.resolution_percentage / 100.0
        width = int(scene.render.resolution_x * scale)
        height = int(scene.render.resolution_y * scale)
        # context.space_data.camera
        protocol.run_until_complete(self.remote_render(width, height, self.render_image))

    def update(self, data, scene):
        """Export scene data for render"""
        print("update")
        if data.objects.is_updated:
            print("One or more objects were updated!")
            for ob in data.objects:
                if ob.is_updated:
                    print("=>", ob.name)

    def view_update(self, context):
        import mathutils
        print("view_update")
        # screen = context.screen.areas[2]
        # r3d = screen.spaces[0].region_3d # region_3d of 3D View
        r3d = context.space_data.region_3d
        # loc = r3d.view_matrix.col[3][1:4]  # translation part of the view matrix
        # rotate the camera to be Zup and Ybackward like other blender object
        # in blender camera and spotlight are face -Z
        # see http://blender.stackexchange.com/questions/8999/convert-from-blender-rotations-to-right-handed-y-up-rotations-maya-houdini
        rot = r3d.view_rotation.copy()
        # rot = mathutils.Quaternion((0, 0, 1, 1))
        # rot = mathutils.Quaternion((-1, 1, 0, 0))  # -PI/2 axis x
        # rot.rotate(mathutils.Quaternion((0, 0, 0, 1)))   # PI axis z
        q = mathutils.Quaternion((1, -1, 0, 0))
        q.normalize()
        rot.rotate(q)
        # rot.rotate(r3d.view_rotation)  # quaternion
        # rot = r3d.view_rotation
        # camera are Yup no more conversion needed
        # loc = r3d.view_location  # vec3
        loc = mathutils.Vector(camera_position(context.space_data))
        projection = r3d.perspective_matrix  # mat4
        print("view_draw {!r} :: {!r} :: {!r}".format(rot, loc, r3d.view_rotation))

        @asyncio.coroutine
        def update():
            (_, writer) = yield from protocol.streams(self.host, self.port)
            protocol.setCamera(writer, loc, rot, projection)
        protocol.run_until_complete(update())
        # exp = MemoryOpenGexExporter()
        # b = exp.exportToBytes(context)
        # print(b)

    def view_draw(self, context):
        self.view_update(context)
        # from http://blender.stackexchange.com/questions/5035/moving-user-perspective-in-blender-with-python
        area = context.screen.areas[2]
        # r3d = screen.spaces[0].region_3d # region_3d of 3D View
        r3d = context.space_data.region_3d
        # loc = r3d.view_matrix.col[3][1:4]  # translation part of the view matrix
        fov = context.space_data.lens
        near = context.space_data.clip_start
        far = context.space_data.clip_end
        rot = r3d.view_rotation  # quaternion
        width = int(area.regions[4].width)
        height = int(area.regions[4].height)
        print("view_info {!r} :: {!r} :: {!r} ::{!r}x{!r}".format(fov, near, far, width, height))
        print("view_quat {!r} :: {!r} :: {!r} ::{!r}".format(rot.x, rot.y, rot.z, r3d.view_matrix))
        protocol.run_until_complete(self.remote_render(width, height, self.view_draw_image))

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


# from http://stackoverflow.com/questions/9028398/change-viewport-angle-in-blender-using-python
def camera_position(space_data):
    """ From 4x4 matrix, calculate camera location """
    matrix = space_data.region_3d.view_matrix
    t = (matrix[0][3], matrix[1][3], matrix[2][3])
    r = (
        (matrix[0][0], matrix[0][1], matrix[0][2]),
        (matrix[1][0], matrix[1][1], matrix[1][2]),
        (matrix[2][0], matrix[2][1], matrix[2][2])
    )
    rp = (
        (-r[0][0], -r[1][0], -r[2][0]),
        (-r[0][1], -r[1][1], -r[2][1]),
        (-r[0][2], -r[1][2], -r[2][2])
    )
    output = (
        rp[0][0] * t[0] + rp[0][1] * t[1] + rp[0][2] * t[2],
        rp[1][0] * t[0] + rp[1][1] * t[1] + rp[1][2] * t[2],
        rp[2][0] * t[0] + rp[2][1] * t[1] + rp[2][2] * t[2],
    )
    return output


def camera_fov(space_data):
    return space_data.lens


def camera_nearfar(space_data):
    return (space_data.clip_start, space_data.clip_end)
