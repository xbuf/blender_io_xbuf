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

import math
import mathutils
import bpy  # TODO to remove


def rot_quat(obj):
    """ return the rotation of the object as quaternion"""
    if obj.rotation_mode == 'QUATERNION':
        return obj.rotation_quaternion
    elif obj.rotation_mode == 'AXIS_ANGLE':
        aa = obj.rotation_axis_angle
        return mathutils.Quaternion((aa[1], aa[2], aa[3]), aa[0])
    else:
        # eurler
        return obj.rotation_euler.to_quaternion()


def extractEye(context_or_camera):
    (loc, rot, projection, near, far, is_ortho) = (None, None, None, None, None, False)
    if hasattr(context_or_camera, 'region_data'):
        context = context_or_camera
        # screen = context.screen.areas[2]
        # r3d = screen.spaces[0].region_3d # region_3d of 3D View
        # rv3d = context.space_data.region_3d
        rv3d = context.region_data
        loc = mathutils.Vector(camera_position(context.space_data))
        # why we don't need to make z up and -y forward ?
        rot = z_backward_to_forward(rv3d.view_rotation)
        projection = rv3d.perspective_matrix * rv3d.view_matrix.inverted()
        near = context.space_data.clip_start
        far = context.space_data.clip_end
        is_ortho = rv3d.view_perspective == 'ORTHO'  # enum in [‘PERSP’, ‘ORTHO’, ‘CAMERA’]
    else:
        camera = context_or_camera
        loc = camera.location
        rot = z_backward_to_forward(rot_quat(camera))
        near = camera.data.clip_start
        far = camera.data.clip_end
        projection = projection_matrix(camera.data)
        is_ortho = camera.type == 'ORTHO'  # enum in [‘PERSP’, ‘ORTHO’, ‘PANO’]
    # print("%r | %r | %r | %r |%r" % (loc, rot, projection, near, far))
    return (loc, rot, projection, near, far, is_ortho)


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


def z_backward_to_forward(quat):
    """rotate around local Y (180deg) to move from z backward to z forward"""
    # rotate the camera to be Zup and Ybackward like other blender object
    # in blender camera and spotlight are face -Z
    # see http://blender.stackexchange.com/questions/8999/convert-from-blender-rotations-to-right-handed-y-up-rotations-maya-houdini
    # rot = r3d.view_rotation.copy()
    # rot = mathutils.Quaternion((0, 0, 1, 1))
    # rot = mathutils.Quaternion((-1, 1, 0, 0))  # -PI/2 axis x
    # rot.rotate(mathutils.Quaternion((0, 0, 0, 1)))   # PI axis z
    qr0 = mathutils.Quaternion((0, 0, 1, 0))  # z forward
    qr0.normalize()
    qr0.rotate(quat)
    qr0.normalize()
    # print("z_backward_to_forward : %r --> %r" % (quat, qr0))
    return qr0


def y_up_to_backward(quat):
    """rotate around local X (90deg) to move from y up to -y forward"""
    qr1 = mathutils.Quaternion((-1, -1, 0, 0))
    qr1.normalize()
    qr1.rotate(quat)
    qr1.normalize()
    # print("y_up_to_backward : %r --> %r" % (quat, qr1))
    return qr1


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
    

def blender_path_abs(path):
    from pathlib import Path
    return str(Path(bpy.path.abspath(str(path).replace("//../", "//../../"))).resolve())
