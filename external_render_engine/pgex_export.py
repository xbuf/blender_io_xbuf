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

import mathutils
import pgex
import pgex.datas_pb2
import pgex.cmds_pb2
import pgex_ext
import pgex_ext.custom_params_pb2
import pgex_ext.animations_kf_pb2
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
    # src0 = src.copy()
    # q = mathutils.Quaternion((-1, 1, 0, 0))
    # q.normalize()
    # src0.rotate(q)
    # dst.x = src0[0]
    # dst.y = src0[1]
    # dst.z = src0[2]
    dst.x = src[0]
    dst.y = src[2]
    dst.z = -src[1]
    return dst


def cnv_toVec3ZupToYup(src):
    # same as src.rotate(Quaternion((1,1,0,0))) # 90 deg CW axis X
    # dst = src.copy()
    # q = mathutils.Quaternion((1, 1, 0, 0))
    # q.normalize()
    # dst.rotate(q)
    dst = [src[0], src[2], -src[1]]
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


def cnv_quat2(src, dst):
    # dst = pgex.math_pb2.Quaternion()
    dst.w = src.w  # [0]
    dst.x = src.x  # [1]
    dst.y = src.z  # [2]
    dst.z = -src.y  # [3]
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


class ExportCfg:
    def __init__(self, is_preview=False, assets_path="/tmp"):
        self.is_preview = is_preview
        self.assets_path = assets_path
        self._modified = {}
        self._ids = {}

    def _k_of(self, v):
        # hash(v) or id(v) ?
        return str(hash(v))

    def id_of(self, v):
        k = self._k_of(v)
        if k in self._ids:
            out = self._ids[k]
        else:
            # out = str(uuid.uuid4().clock_seq)
            out = str(hash(v))
            self._ids[k] = out
        return out

    def need_update(self, v, modified=False):
        k = self._k_of(v)
        old = (k in self._modified) and self._modified[k]
        self._modified[k] = modified
        # print("modified : %r (%r)/ %r / %r /%r / %r" % (v, k, self._modified[k], old, modified, hash(self)))
        return old

    def info(self, txt):
        print("INFO: " + txt)

    def warning(self, txt):
        print("WARNING: " + txt)

    def error(self, txt):
        print("ERROR: " + txt)


# TODO avoid export obj with same id
# TODO optimize unify vertex with (same position, color, normal, texcoord,...)
def export(scene, data, cfg):
    export_all_tobjects(scene, data, cfg)
    export_all_geometries(scene, data, cfg)
    export_all_materials(scene, data, cfg)
    export_all_lights(scene, data, cfg)
    export_all_skeletons(scene, data, cfg)
    export_all_actions(scene, data, cfg)


def export_all_tobjects(scene, data, cfg):
    for obj in scene.objects:
        if obj.hide_render:
            continue
        if cfg.need_update(obj):
            tobject = data.tobjects.add()
            tobject.id = cfg.id_of(obj)
            tobject.name = obj.name
            transform = tobject.transform
            cnv_vec3(obj.scale, transform.scale)
            # convert zup only for direct child of root (no parent)
            cnv_vec3ZupToYup(obj.location, transform.translation)
            #cnv_quatZupToYup(helpers.rot_quat(obj), transform.rotation)
            #if obj.type == 'MESH':
            #    cnv_vec3ZupToYup(obj.location, transform.translation)
            #    cnv_quatZupToYup(helpers.rot_quat(obj), transform.rotation)
            # if obj.parent is None:
            #     cnv_vec3ZupToYup(obj.location, transform.translation)
            #     cnv_quatZupToYup(helpers.rot_quat(obj), transform.rotation)
            #else:
            if obj.type == 'MESH':
                #cnv_quatZupToYup(helpers.rot_quat(obj), transform.rotation)
                cnv_quat2(helpers.rot_quat(obj), transform.rotation)
            elif obj.type == 'Armature':
                cnv_quat2(helpers.rot_quat(obj), transform.rotation)
            elif obj.type == 'LAMP':
                rot = helpers.z_backward_to_forward(helpers.rot_quat(obj))
                cnv_quatZupToYup(rot, transform.rotation)
            else:
                cnv_quat2(helpers.rot_quat(obj), transform.rotation)
            if obj.parent is not None:
                #    tobject.parentId = cfg.id_of(obj.parent)
                add_relation_raw(data.relations, pgex.datas_pb2.TObject.__name__, cfg.id_of(obj.parent), pgex.datas_pb2.TObject.__name__, cfg.id_of(obj))
            export_obj_customproperties(obj, tobject, data, cfg)


def export_all_geometries(scene, data, cfg):
    for obj in scene.objects:
        if obj.hide_render:
            continue
        if obj.type == 'MESH':
            if len(obj.data.polygons) != 0 and cfg.need_update(obj.data):
                geometry = data.geometries.add()
                export_geometry(obj, geometry, scene, cfg)
                add_relation_raw(data.relations, pgex.datas_pb2.TObject.__name__, cfg.id_of(obj), pgex.datas_pb2.Geometry.__name__, cfg.id_of(obj.data))
        elif obj.type == 'LAMP':
            src_light = obj.data
            if cfg.need_update(src_light):
                dst_light = data.lights.add()
                export_light(src_light, dst_light, cfg)
            add_relation_raw(data.relations, pgex.datas_pb2.TObject.__name__, cfg.id_of(obj), pgex.datas_pb2.Light.__name__, cfg.id_of(src_light))


def export_all_materials(scene, data, cfg):
    for obj in scene.objects:
        if obj.hide_render:
            continue
        if obj.type == 'MESH':
            for i in range(len(obj.material_slots)):
                src_mat = obj.material_slots[i].material
                if cfg.need_update(src_mat):
                    dst_mat = data.materials.add()
                    export_material(src_mat, dst_mat, cfg)
                add_relation_raw(data.relations, pgex.datas_pb2.TObject.__name__, cfg.id_of(obj), pgex.datas_pb2.Material.__name__, cfg.id_of(src_mat))


def export_all_lights(scene, data, cfg):
    for obj in scene.objects:
        if obj.hide_render:
            continue
        if obj.type == 'LAMP':
            src_light = obj.data
            if cfg.need_update(src_light):
                dst_light = data.lights.add()
                export_light(src_light, dst_light, cfg)
            add_relation_raw(data.relations, pgex.datas_pb2.TObject.__name__, cfg.id_of(obj), pgex.datas_pb2.Light.__name__, cfg.id_of(src_light))


def add_relation(relations, e1, e2):
    add_relation_raw(relations, type(e1).__name__, e1.id, type(e2).__name__, e2.id)


def add_relation_raw(relations, t1, ref1, t2, ref2):
    rel = relations.add()
    if t1 <= t2:
        rel.ref1 = ref1
        rel.ref2 = ref2
    else:
        rel.ref1 = ref2
        rel.ref2 = ref1


def export_geometry(src, dst, scene, cfg):
    dst.id = cfg.id_of(src.data)
    dst.name = src.name
    mesh = dst.meshes.add()
    mesh.primitive = pgex.datas_pb2.Mesh.triangles
    mode = 'PREVIEW' if cfg.is_preview else 'RENDER'
    src_mesh = src.to_mesh(scene, True, mode, True, False)
    mesh.id = cfg.id_of(src_mesh)
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
    faces = src_mesh.tessfaces
    for face in faces:
        floats.extend(cnv_toVec3ZupToYup(vertices[face.vertices[0]].co))
        floats.extend(cnv_toVec3ZupToYup(vertices[face.vertices[1]].co))
        floats.extend(cnv_toVec3ZupToYup(vertices[face.vertices[2]].co))
        if (len(face.vertices) == 4):
            floats.extend(cnv_toVec3ZupToYup(vertices[face.vertices[3]].co))

    # for v in vertices:
    #     floats.extend(v.co)
    dst.floats.values.extend(floats)


def export_normals(src_mesh, dst_mesh):
    vertices = src_mesh.vertices
    dst = dst_mesh.vertexArrays.add()
    dst.attrib = pgex.datas_pb2.VertexArray.normal
    dst.floats.step = 3
    floats = []
    faces = src_mesh.tessfaces
    for face in faces:
        floats.extend(cnv_toVec3ZupToYup(vertices[face.vertices[0]].normal))
        floats.extend(cnv_toVec3ZupToYup(vertices[face.vertices[1]].normal))
        floats.extend(cnv_toVec3ZupToYup(vertices[face.vertices[2]].normal))
        if (len(face.vertices) == 4):
            floats.extend(cnv_toVec3ZupToYup(vertices[face.vertices[3]].normal))
    # for v in vertices:
    #     floats.extend(v.normal)
    dst.floats.values.extend(floats)


def export_index(src_mesh, dst_mesh):
    faces = src_mesh.tessfaces
    dst = dst_mesh.indexArrays.add()
    dst.ints.step = 3
    ints = []
    idx = 0
    for face in faces:
        ints.append(idx)
        idx += 1
        ints.append(idx)
        idx += 1
        ints.append(idx)
        idx += 1
        if (len(face.vertices) == 4):
            ints.append(idx - 3)
            ints.append(idx - 1)
            ints.append(idx)
            idx += 1
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
    for face in faces:
        fc = face_colors[face.index]
        floats.extend(fc.color1)
        floats.extend(fc.color2)
        floats.extend(fc.color3)
        if (len(face.vertices) == 4):
            floats.extend(fc.color1)
            floats.extend(fc.color3)
            floats.extend(fc.color4)
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
        for face in faces:
            ftc = texcoordFace[face.index]
            floats.extend(ftc.uv1)
            floats.extend(ftc.uv2)
            floats.extend(ftc.uv3)
            if (len(face.vertices) == 4):
                # floats.extend(ftc.uv1)
                # floats.extend(ftc.uv3)
                floats.extend(ftc.uv4)
        dst.floats.values.extend(floats)


def export_material(src_mat, dst_mat, cfg):
    dst_mat.id = cfg.id_of(src_mat)
    dst_mat.name = src_mat.name

    dst_mat.shadeless = src_mat.use_shadeless
    intensity = src_mat.diffuse_intensity
    diffuse = [src_mat.diffuse_color[0] * intensity, src_mat.diffuse_color[1] * intensity, src_mat.diffuse_color[2] * intensity]

    cnv_color(diffuse, dst_mat.color)

    intensity = src_mat.specular_intensity
    specular = [src_mat.specular_color[0] * intensity, src_mat.specular_color[1] * intensity, src_mat.specular_color[2] * intensity]

    if ((specular[0] > 0.0) or (specular[1] > 0.0) or (specular[2] > 0.0)):
        cnv_color(specular, dst_mat.specular)
        dst_mat.specular_power = src_mat.specular_hardness

    emission = src_mat.emit
    if (emission > 0.0):
        cnv_color([emission, emission, emission], dst_mat.emission)

    for textureSlot in src_mat.texture_slots:
        if ((textureSlot) and (textureSlot.use) and (textureSlot.texture.type == "IMAGE")):
            if (((textureSlot.use_map_color_diffuse) or (textureSlot.use_map_diffuse))):
                export_tex(textureSlot, dst_mat.color_map, cfg)
            elif (((textureSlot.use_map_color_spec) or (textureSlot.use_map_specular))):
                export_tex(textureSlot, dst_mat.speculat_map, cfg)
            elif ((textureSlot.use_map_emit)):
                export_tex(textureSlot, dst_mat.emission_map, cfg)
            elif ((textureSlot.use_map_translucency)):
                export_tex(textureSlot, dst_mat.opacity_map, cfg)
            elif ((textureSlot.use_map_normal)):
                export_tex(textureSlot, dst_mat.normal_map, cfg)


def export_tex(src, dst, cfg):
    from pathlib import PurePath, Path
    ispacked = src.texture.image.filepath.startswith('//')
    dst.id = cfg.id_of(src.texture)

    if ispacked:
        rpath = PurePath("Textures") / PurePath(src.texture.image.filepath[2:])
        if not cfg.need_update(src.texture):
            abspath = Path(cfg.assets_path) / rpath
            if not abspath.parent.exists():
                abspath.parent.mkdir(parents=True)
            print("path %r => %r " % (rpath, abspath))
            with abspath.open('wb') as f:
                f.write(src.texture.image.packed_file.data)
        dst.rpath = str.join('/', rpath.parts)
    # TODO use md5 (hashlib.md5().update(...)) to name or to check change ??
    # TODO If the texture has a scale and/or offset, then export a coordinate transform.
    # uscale = textureSlot.scale[0]
    # vscale = textureSlot.scale[1]
    # uoffset = textureSlot.offset[0]
    # voffset = textureSlot.offset[1]


# TODO redo Light, more clear definition,...
def export_light(src, dst, cfg):
    dst.id = cfg.id_of(src)
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


def export_all_skeletons(scene, data, cfg):
    for obj in scene.objects:
        if obj.type == 'ARMATURE':
            src_skeleton = obj.data
            if cfg.need_update(src_skeleton):
                dst_skeleton = data.skeletons.add()
                export_skeleton(src_skeleton, dst_skeleton, obj, cfg)
            add_relation_raw(data.relations, pgex.datas_pb2.TObject.__name__, cfg.id_of(obj), pgex.datas_pb2.Skeleton.__name__, cfg.id_of(src_skeleton))


def export_skeleton(src, dst, armature, cfg):
    dst.id = cfg.id_of(src)
    dst.name = src.name
    # for src_bone in armature.pose.bones:
    for src_bone in src.bones:
        dst_bone = dst.bones.add()
        dst_bone.id = cfg.id_of(src_bone)
        dst_bone.name = src_bone.name
        transform = dst_bone.transform

        # retreive transform local to parent
        boneMat = src_bone.matrix_local
        if src_bone.parent:
            boneMat = src_bone.parent.matrix_local.inverted() * src_bone.matrix_local
        loc, quat, sca = boneMat.decompose()

        # Can't use armature.convert_space
        # boneMat = armature.convert_space(pose_bone=src_bone, matrix=src_bone.matrix, from_space='POSE', to_space='LOCAL_WITH_PARENT')
        # loc, quat, sca = boneMat.decompose()

        cnv_vec3(sca, transform.scale)
        cnv_vec3ZupToYup(loc, transform.translation)
        # cnv_vec3(loc, transform.translation)
        cnv_quat2(quat, transform.rotation)
        # cnv_quatZupToYup(quat, transform.rotation)
        # cnv_quat(quat, transform.rotation)
        # print("%s (%s) : %s" % (dst_bone.name, dst_bone.id, transform))
        if src_bone.parent:
            rel = dst.bones_graph.add()
            rel.ref1 = cfg.id_of(src_bone.parent)
            rel.ref2 = dst_bone.id


def export_all_actions(scene, dst_data, cfg):
    fps = max(1.0, float(scene.render.fps))
    for action in bpy.data.actions:
        # if cfg.need_update(action):
        if True:
            dst = dst_data.Extensions[pgex_ext.animations_kf_pb2.animations_kf].add()
            export_action(action, dst, fps, cfg)
            print("exp action: %r" % (cfg.id_of(action)))
    print(len(dst_data.Extensions[pgex_ext.animations_kf_pb2.animations_kf]))
    for obj in scene.objects:
        if obj.animation_data:
            for tracks in obj.animation_data.nla_tracks:
                for strip in tracks.strips:
                    print("object action: %r" % (cfg.id_of(strip.action)))
                    add_relation_raw(
                        dst_data.relations,
                        pgex.datas_pb2.TObject.__name__, cfg.id_of(obj),
                        pgex_ext.animations_kf_pb2.AnimationKF.__name__, cfg.id_of(strip.action))


def export_action(src, dst, fps, cfg):
    dst.id = cfg.id_of(src)
    dst.name = src.name
    frames_duration = max(0.001, float(src.frame_range.y - src.frame_range.x))
    dst.duration = frames_duration / fps
    clip = dst.clips.add()

    def frame_to_duration_ratio(f):
        return float(f - src.frame_range.x) / frames_duration
    for fcurve in src.fcurves:
        target_name = fcurve.data_path
        dst_kf = None
        dst_kfs_coef = 1.0
        if target_name == "location":
            dst_kf, dst_kfs_coef = vec3_array_index(clip.transforms.translation, fcurve.array_index)
        elif target_name == "scale":
            dst_kf, dst_kfs_coef = vec3_array_index(clip.transforms.scale, fcurve.array_index)
        elif target_name == "rotation_quaternion":
            dst_kf, dst_kfs_coef = quat_array_index(clip.transforms.rotation, fcurve.array_index)
        elif target_name == "rotation_euler":
            cfg.warning("unsupported : rotation_euler , use rotation_quaternion")
            continue
        else:
            cfg.warning("unsupported : " + target_name)
            continue
        if dst_kf is not None:
            has_bezier = False
            # curve.x => duration in [0,1] 1 is animation duration
            durations = []
            # values should be in ref Yup Zforward
            values = []
            # parameter of interpolation
            interpolations = []
            for src_kf in fcurve.keyframe_points:
                durations.append(frame_to_duration_ratio(src_kf.co[0]))
                values.append(src_kf.co[1] * dst_kfs_coef)
                interpolations.append(cnv_interpolation(src_kf.interpolation))
                has_bezier = has_bezier or ('BEZIER' == src_kf.interpolation)
            dst_kf.duration_ratio.extend(durations)
            dst_kf.value.extend(values)
            dst_kf.interpolation.extend(interpolations)
            # each interpolation segment as  x in [0,1], y in same ref as values[]
            if has_bezier:
                kps = fcurve.keyframe_points
                for i in range(len(kps)):
                    bp = dst_kf.bezier_params.add()
                    if ('BEZIER' == kps[i].interpolation) and (i < (len(kps) - 1)):
                        p0 = kps[i]
                        p1 = kps[(i + 1)]
                        seg_duration = p1.co[0] - p0.co[0]
                        # print("kf co(%s) , left (%s), right(%s) : (%s, %s)" % ())
                        bp.h0_x = (p0.handle_right[0] - p0.co[0]) / seg_duration
                        bp.h0_y = p0.handle_right[1] * dst_kfs_coef
                        bp.h1_x = (p1.handle_left[0] - p0.co[0]) / seg_duration
                        bp.h1_y = p1.handle_left[1] * dst_kfs_coef
            print("res dst_kf %r" % (dst_kf))


def cnv_interpolation(inter):
    if 'CONSTANT' == inter:
        return pgex_ext.animations_kf_pb2.KeyPoints.constant
    elif 'BEZIER' == inter:
        return pgex_ext.animations_kf_pb2.KeyPoints.bezier
    return pgex_ext.animations_kf_pb2.KeyPoints.linear


def vec3_array_index(vec3, idx):
    "find the target vec3 and take care of the axis change (to Y up, Z forward)"
    if idx == 0:
        # x => x
        return (vec3.x, 1.0)
    if idx == 1:
        # y => -z
        return (vec3.z, -1.0)
    if idx == 2:
        return (vec3.y, 1.0)


def quat_array_index(vec3, idx):
    "find the target quat and take care of the axis change (to Y up, Z forward)"
    if idx == 0:
        return (vec3.w, 1.0)
    if idx == 1:
        return (vec3.x, 1.0)
    if idx == 2:
        return (vec3.z, -1.0)
    if idx == 3:
        return (vec3.y, 1.0)


def export_obj_customproperties(src, dst_node, dst_data, cfg):
    keys = [k for k in src.keys() if not (k.startswith('_') or k.startswith('cycles'))]
    if len(keys) > 0:
        custom_params = dst_data.Extensions[pgex_ext.custom_params_pb2.custom_params].add()
        custom_params.id = cfg.id_of(src)
        for key in keys:
            param = custom_params.params.add()
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
        add_relation(dst_data.relations, dst_node, custom_params)


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
        cfg = ExportCfg(is_preview=False, assets_path=scene.pgex.assets_path)
        export(scene, data, cfg)

        self.file = open(self.filepath, "wb")
        self.file.write(data.SerializeToString())
        self.file.close()

        if (self.restoreFrame):
            scene.frame_set(originalFrame, originalSubframe)

        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None)
