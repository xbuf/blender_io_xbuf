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

import uuid
import struct
import mathutils
import pgex
import pgex.datas_pb2
import pgex.cmds_pb2
import pgex_ext
import pgex_ext.customparams_pb2
from . import helpers  # pylint: disable=W0406


def cnv_vec3(src, dst):
    # dst = pgex.math_pb2.Vec3()
    # dst.x = src.x
    # dst.y = src.y
    # dst.z = src.z
    dst.x = src[0]
    dst.y = src[1]
    dst.z = src[2]
    return dst


def cnv_vec3ZupToYup(src, dst):
    # same as src.rotate(Quaternion((1,1,0,0))) # 90 deg CW axis X
    src0 = src.copy()
    q = mathutils.Quaternion((-1, 1, 0, 0))
    q.normalize()
    src0.rotate(q)
    dst.x = src0[0]
    dst.y = src0[1]
    dst.z = src0[2]
    return dst


def cnv_quatZupToYup(src, dst):
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
    return dst


def cnv_quat(src, dst):
    # dst = pgex.math_pb2.Quaternion()
    dst.w = src.w  # [0]
    dst.x = src.x  # [1]
    dst.y = src.y  # [2]
    dst.z = src.z  # [3]
    return dst


def cnv_mat4(src, dst):
    # dst = pgex.math_pb2.Quaternion()
    dst.c00 = src[0][0]
    dst.c10 = src[1][0]
    dst.c20 = src[2][0]
    dst.c30 = src[3][0]
    dst.c01 = src[0][1]
    dst.c11 = src[1][1]
    dst.c21 = src[2][1]
    dst.c31 = src[3][1]
    dst.c02 = src[0][2]
    dst.c12 = src[1][2]
    dst.c22 = src[2][2]
    dst.c32 = src[3][2]
    dst.c03 = src[0][3]
    dst.c13 = src[1][3]
    dst.c23 = src[2][3]
    dst.c33 = src[3][3]
    return dst


def cnv_color(src, dst):
    dst.r = src[0]
    dst.g = src[1]
    dst.b = src[2]
    dst.a = 1.0 if len(src) < 4 else src[3]
    return dst


def id_of(v):
    if not ('pgex_id' in v.keys()):
        v['pgex_id'] = str(uuid.uuid4().clock_seq)
    return v['pgex_id']


# TODO avoid export obj with same id
def export(scene, data, isPreview):
    for obj in scene.objects:
        tobject = data.tobjects.add()
        tobject.id = id_of(obj)
        tobject.name = obj.name
        transform = tobject.transforms.add()
        # TODO convert zup only for child of root
        cnv_vec3ZupToYup(obj.location, transform.translation)
        cnv_quatZupToYup(helpers.rot_quat(obj), transform.rotation)
        cnv_vec3(obj.scale, transform.scale)
        if obj.parent is not None:
            tobject.parent = obj.parent.name
        if obj.type == 'MESH':
            if len(obj.data.polygons) != 0:
                geometry = data.geometries.add()
                export_geometry(obj, geometry, scene, isPreview)
                add_relation(data.relations, tobject, geometry)
            for i in range(len(obj.material_slots)):
                dst_mat = data.materials.add()
                export_material(obj.material_slots[i].material, dst_mat)
                add_relation(data.relations, tobject, dst_mat)
        elif obj.type == 'LAMP':
            rot = helpers.z_backward_to_forward(helpers.rot_quat(obj))
            cnv_quatZupToYup(rot, transform.rotation)
            light = data.lights.add()
            export_light(obj.data, light)
            add_relation(data.relations, tobject, light)
        export_obj_customproperties(obj, tobject, data)


def add_relation(relations, e1, e2):
    rel = relations.add()
    if type(e1).__name__ < type(e2).__name__:
        rel.ref1 = e1.id
        rel.ref2 = e2.id
    else:
        rel.ref1 = e2.id
        rel.ref2 = e1.id


def export_geometry(src, dst, scene, isPreview):
    dst.id = 'G' + id_of(src)
    dst.name = src.name
    mesh = dst.meshes.add()
    mesh.primitive = pgex.datas_pb2.Mesh.triangles
    mode = 'PREVIEW' if isPreview else 'RENDER'
    src_mesh = src.to_mesh(scene, True, mode, True, False)
    mesh.id = id_of(src_mesh)
    mesh.name = src_mesh.name
    # unified_vertex_array = unify_vertices(vertex_array, index_table)
    export_positions(src_mesh, mesh)
    export_normals(src_mesh, mesh)
    export_index(src_mesh, mesh)
    export_colors(src_mesh, mesh)
    export_texcoords(src_mesh, mesh)


def export_positions(src_mesh, dst_mesh):
    vertices = src_mesh.vertices
    dst = dst_mesh.vertexArrays.add()
    dst.attrib = pgex.datas_pb2.VertexArray.position
    dst.floats.step = 3
    floats = []
    for v in vertices:
        floats.extend(v.co)
    dst.floats.values.extend(floats)


def export_normals(src_mesh, dst_mesh):
    vertices = src_mesh.vertices
    dst = dst_mesh.vertexArrays.add()
    dst.attrib = pgex.datas_pb2.VertexArray.normal
    dst.floats.step = 3
    floats = []
    for v in vertices:
        floats.extend(v.normal)
    dst.floats.values.extend(floats)


def export_index(src_mesh, dst_mesh):
    faces = src_mesh.tessfaces
    dst = dst_mesh.indexArrays.add()
    dst.ints.step = 3
    ints = []
    for face in faces:
        ints.append(face.vertices[0])
        ints.append(face.vertices[1])
        ints.append(face.vertices[2])
        if (len(face.vertices) == 4):
            ints.append(face.vertices[0])
            ints.append(face.vertices[2])
            ints.append(face.vertices[3])
    dst.ints.values.extend(ints)


def export_colors(src_mesh, dst_mesh):
    colorCount = len(src_mesh.tessface_vertex_colors)
    if (colorCount < 1):
        return
    faces = src_mesh.tessfaces
    face_colors = src_mesh.tessface_vertex_colors[0].data
    dst = dst_mesh.vertexArrays.add()
    dst.attrib = pgex.datas_pb2.VertexArray.color
    dst.floats.step = 4
    floats = []
    faceIndex = 0
    for face in faces:
        fc = face_colors[faceIndex]
        floats.extend(fc.color1)
        floats.extend(fc.color2)
        floats.extend(fc.color3)
        if (len(face.vertices) == 4):
            floats.extend(fc.color1)
            floats.extend(fc.color3)
            floats.extend(fc.color4)
        faceIndex += 1
    dst.floats.values.extend(floats)


def export_texcoords(src_mesh, dst_mesh):
    texcoordCount = len(src_mesh.tessface_uv_textures)
    if (texcoordCount < 1):
        return
    faces = src_mesh.tessfaces
    for uvI in range(min(9, len(src_mesh.tessface_uv_textures))):
        texcoordFace = src_mesh.tessface_uv_textures[uvI].data
        dst = dst_mesh.vertexArrays.add()
        dst.attrib = pgex.datas_pb2.VertexArray.texcoord + uvI
        dst.floats.step = 2
        floats = []
        faceIndex = 0
        for face in faces:
            ftc = texcoordFace[faceIndex]
            floats.extend(ftc.uv1)
            floats.extend(ftc.uv2)
            floats.extend(ftc.uv3)
            if (len(face.vertices) == 4):
                floats.extend(ftc.uv1)
                floats.extend(ftc.uv3)
                floats.extend(ftc.uv4)
            faceIndex += 1
        dst.floats.values.extend(floats)


def export_material(src_mat, dst_mat):
    dst_mat.id = id_of(src_mat)
    dst_mat.name = src_mat.name

    intensity = src_mat.diffuse_intensity
    diffuse = [src_mat.diffuse_color[0] * intensity, src_mat.diffuse_color[1] * intensity, src_mat.diffuse_color[2] * intensity]

    p = dst_mat.params.add()
    p.attrib = pgex.datas_pb2.MaterialParam.color
    cnv_color(diffuse, p.vcolor)

    intensity = src_mat.specular_intensity
    specular = [src_mat.specular_color[0] * intensity, src_mat.specular_color[1] * intensity, src_mat.specular_color[2] * intensity]

    if ((specular[0] > 0.0) or (specular[1] > 0.0) or (specular[2] > 0.0)):
        p = dst_mat.params.add()
        p.attrib = pgex.datas_pb2.MaterialParam.specular
        cnv_color(specular, p.vcolor)
        p = dst_mat.params.add()
        p.attrib = pgex.datas_pb2.MaterialParam.specular_power
        p.vfloat = src_mat.specular_hardness

    emission = src_mat.emit
    if (emission > 0.0):
        p = dst_mat.params.add()
        p.attrib = pgex.datas_pb2.MaterialParam.emission
        cnv_color([emission, emission, emission], p.vcolor)

    for textureSlot in src_mat.texture_slots:
        if ((textureSlot) and (textureSlot.use) and (textureSlot.texture.type == "IMAGE")):
            if (((textureSlot.use_map_color_diffuse) or (textureSlot.use_map_diffuse))):
                p = dst_mat.params.add()
                p.attrib = pgex.datas_pb2.MaterialParam.color
                export_tex(textureSlot, p.vtexture)
            elif (((textureSlot.use_map_color_spec) or (textureSlot.use_map_specular))):
                p = dst_mat.params.add()
                p.attrib = pgex.datas_pb2.MaterialParam.specular
                export_tex(textureSlot, p.vtexture)
            elif ((textureSlot.use_map_emit)):
                p = dst_mat.params.add()
                p.attrib = pgex.datas_pb2.MaterialParam.emission
                export_tex(textureSlot, p.vtexture)
            elif ((textureSlot.use_map_translucency)):
                p = dst_mat.params.add()
                p.attrib = pgex.datas_pb2.MaterialParam.transparency
                export_tex(textureSlot, p.vtexture)
            elif ((textureSlot.use_map_normal)):
                p = dst_mat.params.add()
                p.attrib = pgex.datas_pb2.MaterialParam.normal
                export_tex(textureSlot, p.vtexture)


def export_tex(src, dst):
    dst.rpath = src.texture.image.filepath
    # TODO If the texture has a scale and/or offset, then export a coordinate transform.
    # uscale = textureSlot.scale[0]
    # vscale = textureSlot.scale[1]
    # uoffset = textureSlot.offset[0]
    # voffset = textureSlot.offset[1]


# TODO redo Light, more clear definition,...
def export_light(src, dst):
    dst.id = id_of(src)
    dst.name = src.name
    kind = src.type
    if kind == 'SUN' or kind == 'AREA':
        dst.kind = pgex.datas_pb2.Light.directional
    elif kind == 'POINT':
        dst.kind = pgex.datas_pb2.Light.point
    elif kind == 'SPOT':
        dst.kind = pgex.datas_pb2.Light.spot
        dst.spot_angle.max = src.spot_size * 0.5
        dst.spot_angle.linear.begin = (1.0 - src.spot_blend)
    dst.cast_shadow = getattr(src, 'use_shadow', False)
    cnv_color(src.color, dst.color)
    dst.intensity = src.energy
    dst.radial_distance.max = src.distance
    if hasattr(src, 'falloff_type'):
        falloff = src.falloff_type
        if falloff == 'INVERSE_LINEAR':
            dst.radial_distance.max = src.distance
            dst.radial_distance.inverse.scale = 1.0
        elif falloff == 'INVERSE_SQUARE':
            dst.radial_distance.max = src.distance  # math.sqrt(src.distance)
            dst.radial_distance.inverse_square.scale = 1.0
        elif falloff == 'LINEAR_QUADRATIC_WEIGHTED':
            if src.quadratic_attenuation == 0.0:
                dst.radial_distance.max = src.distance
                dst.radial_distance.inverse.scale = 1.0
                dst.radial_distance.inverse.constant = 1.0
                dst.radial_distance.inverse.linear = src.linear_attenuation
            else:
                dst.radial_distance.max = src.distance
                dst.radial_distance.inverse_square.scale = 1.0
                dst.radial_distance.inverse_square.constant = 1.0
                dst.radial_distance.inverse_square.linear = src.linear_attenuation
                dst.radial_distance.inverse_square.linear = src.quadratic_attenuation
    if getattr(src, 'use_sphere', False):
        dst.radial_distance.linear.end = 1.0


def export_obj_customproperties(src, dst_node, dst_data):
    keys = [k for k in src.keys() if not (k.startswith('_') or k.startswith('cycles'))]
    if len(keys) > 0:
        customparams = dst_data.Extensions[pgex_ext.customparams_pb2.customParams].add()
        customparams.id = 'CP' + id_of(src)
        for key in keys:
            param = customparams.params.add()
            param.name = key
            value = src[key]
            if type(value) == bool:
                param.vbool = value
            elif type(value) == str:
                param.vstring = value
            elif type(value) == float:
                param.vfloat = value
            elif type(value) == int:
                param.vint = value
            elif type(value) == mathutils.Vector:
                cnv_vec3(value, param.vvec3)
            elif type(value) == mathutils.Quaternion:
                cnv_quat(value, param.vquat)
        add_relation(dst_data.relations, dst_node, customparams)


import bpy
from bpy_extras.io_utils import ExportHelper


class PgexExporter(bpy.types.Operator, ExportHelper):
    """Export to pgex format"""
    bl_idname = "export_scene.pgex"
    bl_label = "Export pgex"
    filename_ext = ".pgex"

    # option_export_selection = bpy.props.BoolProperty(name = "Export Selection", description = "Export only selected objects", default = False)

    def __init__(self):
        pass

    def execute(self, context):
        scene = context.scene
        originalFrame = scene.frame_current
        originalSubframe = scene.frame_subframe
        self.restoreFrame = False

        self.beginFrame = scene.frame_start
        self.endFrame = scene.frame_end
        self.frameTime = 1.0 / (scene.render.fps_base * scene.render.fps)

        # exportAllFlag = not self.option_export_selection
        data = pgex.datas_pb2.Data()
        export(scene, data, False)

        self.file = open(self.filepath, "wb")
        self.file.write(data.SerializeToString())
        self.file.close()

        if (self.restoreFrame):
            scene.frame_set(originalFrame, originalSubframe)

        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None)
