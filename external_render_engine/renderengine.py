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
import math
import mathutils
from . import protocol
from . import pgex_export

# gloop = external_render_engine.gloop

# http://wiki.blender.org/index.php/Dev:2.6/Source/Render/RenderEngineAPI
# http://wiki.blender.org/index.php/Dev:2.6/Source/Render/UpdateAPI
# http://www.blender.org/api/blender_python_api_2_72_release/bpy.types.RenderEngine.html


class ExternalRenderEngine(bpy.types.RenderEngine):
    # These three members are used by blender to set up the
    # RenderEngine; define its internal name, visible name and capabilities.
    bl_idname = "external_render"
    bl_label = "External Render"
    bl_use_preview = True

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
        (loc, rot, projection, near, far) = extractEye(context_or_camera)

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
        self.external_render(scene.camera, width, height, self.render_image)

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

        import numpy  # np is not define on blender
        np = numpy
        # print("w * h : %r   len/4 : %s" % (width*height, len(raw)/4))
        data = np.fromstring(raw, dtype=np.byte).astype(np.float)
        data = np.reshape(data, (len(raw)/4, 4))
        reorder = np.array([2, 1, 0, 3])
        data = data[:, reorder]
        divfunc = np.vectorize(lambda a: a / 255.0)
        #data = divfunc(data)

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


def extractEye(context_or_camera):
    (loc, rot, projection, near, far) = (None, None, None, None, None)
    if hasattr(context_or_camera, 'region_data'):
        context = context_or_camera
        # screen = context.screen.areas[2]
        # r3d = screen.spaces[0].region_3d # region_3d of 3D View
        # rv3d = context.space_data.region_3d
        rv3d = context.region_data
        # loc = r3d.view_matrix.col[3][1:4]  # translation part of the view matrix
        loc = mathutils.Vector(camera_position(context.space_data))
        rot = camera_rotation_adjust(rv3d.view_rotation)
        projection = rv3d.perspective_matrix * rv3d.view_matrix.inverted()
        near = context.space_data.clip_start
        far = context.space_data.clip_end
    else:
        camera = context_or_camera
        loc = camera.location
        rot = camera_rotation_adjust(pgex_export.rot_quat(camera))
        near = camera.data.clip_start
        far = camera.data.clip_end
        projection = projection_matrix(camera.data)
        print(projection)
    print("%r | %r | %r | %r |%r" % (loc, rot, projection, near, far))
    return (loc, rot, projection, near, far)


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


def camera_rotation_adjust(rot_quat):
    # rotate the camera to be Zup and Ybackward like other blender object
    # in blender camera and spotlight are face -Z
    # see http://blender.stackexchange.com/questions/8999/convert-from-blender-rotations-to-right-handed-y-up-rotations-maya-houdini
    # rot = r3d.view_rotation.copy()
    # rot = mathutils.Quaternion((0, 0, 1, 1))
    # rot = mathutils.Quaternion((-1, 1, 0, 0))  # -PI/2 axis x
    # rot.rotate(mathutils.Quaternion((0, 0, 0, 1)))   # PI axis z
    qr0 = mathutils.Quaternion((0, 0, 1, 0))  # z forward
    qr0.normalize()
    qr0.rotate(rot_quat)
    qr0.normalize()
    rot = qr0
    # why we don't need to make z up and -y forward ?
    # qr1 = mathutils.Quaternion((-1, -1, 0, 0))
    # qr1.normalize()
    # qr1.rotate(qr0)
    # qr1.normalize()
    # rot = qr1
    print("%r --> %r" % (rot_quat, rot))
    return rot


# from http://jmonkeyengine.googlecode.com/svn/trunk/engine/src/blender/com/jme3/scene/plugins/blender/cameras/CameraHelper.java
def camera_fov(space_data):
    fov = 2 * math.atan(16/space_data.lens)  # fov in radian, lens in mm, 16 is sensor_height (default: 32.0) / 2
    return fov


# from http://blender.stackexchange.com/questions/16472/how-can-i-get-the-cameras-projection-matrix
def view_plane(camd, winx, winy, xasp, yasp):
    # fields rendering
    ycor = yasp / xasp
    use_fields = False
    if (use_fields):
        ycor *= 2

    def BKE_camera_sensor_size(p_sensor_fit, sensor_x, sensor_y):
        # sensor size used to fit to. for auto, sensor_x is both x and y.
        if (p_sensor_fit == 'VERTICAL'):
            return sensor_y

        return sensor_x

    if (camd.type == 'ORTHO'):
        # orthographic camera
        # scale == 1.0 means exact 1 to 1 mapping
        pixsize = camd.ortho_scale
    else:
        # perspective camera
        sensor_size = BKE_camera_sensor_size(camd.sensor_fit, camd.sensor_width, camd.sensor_height)
        pixsize = (sensor_size * camd.clip_start) / camd.lens

        # determine sensor fit
        def BKE_camera_sensor_fit(p_sensor_fit, sizex, sizey):
            if (p_sensor_fit == 'AUTO'):
                if (sizex >= sizey):
                    return 'HORIZONTAL'
                else:
                    return 'VERTICAL'

            return p_sensor_fit

    sensor_fit = BKE_camera_sensor_fit(camd.sensor_fit, xasp * winx, yasp * winy)

    if (sensor_fit == 'HORIZONTAL'):
        viewfac = winx
    else:
        viewfac = ycor * winy

    pixsize /= viewfac

    # extra zoom factor
    pixsize *= 1  # params->zoom

    # compute view plane:
    # fully centered, zbuffer fills in jittered between -.5 and +.5
    xmin = -0.5 * winx
    ymin = -0.5 * ycor * winy
    xmax = 0.5 * winx
    ymax = 0.5 * ycor * winy

    # lens shift and offset
    dx = camd.shift_x * viewfac  # + winx * params->offsetx
    dy = camd.shift_y * viewfac  # + winy * params->offsety

    xmin += dx
    ymin += dy
    xmax += dx
    ymax += dy

    # fields offset
    # if (params->field_second):
    #    if (params->field_odd):
    #        ymin -= 0.5 * ycor
    #        ymax -= 0.5 * ycor
    #    else:
    #        ymin += 0.5 * ycor
    #        ymax += 0.5 * ycor

    # the window matrix is used for clipping, and not changed during OSA steps
    # using an offset of +0.5 here would give clip errors on edges
    xmin *= pixsize
    xmax *= pixsize
    ymin *= pixsize
    ymax *= pixsize

    return xmin, xmax, ymin, ymax


# from http://blender.stackexchange.com/questions/16472/how-can-i-get-the-cameras-projection-matrix
def projection_matrix(camd):
    r = bpy.context.scene.render
    left, right, bottom, top = view_plane(camd, r.resolution_x, r.resolution_y, 1, 1)

    farClip, nearClip = camd.clip_end, camd.clip_start

    Xdelta = right - left
    Ydelta = top - bottom
    Zdelta = farClip - nearClip

    mat = [[0]*4 for i in range(4)]

    mat[0][0] = nearClip * 2 / Xdelta
    mat[1][1] = nearClip * 2 / Ydelta
    #mat[2][0] = (right + left) / Xdelta  # note: negate Z
    #mat[2][1] = (top + bottom) / Ydelta
    mat[2][2] = -(farClip + nearClip) / Zdelta
    mat[3][2] = -1
    mat[2][3] = (-2 * nearClip * farClip) / Zdelta

    # return sum([c for c in mat], [])
    return mat
