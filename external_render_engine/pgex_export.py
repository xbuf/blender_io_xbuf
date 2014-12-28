import mathutils
import pgex


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


def export(context, data, isPreview):
    scene = context.scene
    for obj in scene.objects:
        node = data.nodes.add()
        node.id = obj.name
        transform = node.transforms.add()
        # TODO convert zup only for child of root
        cnv_vec3ZupToYup(obj.location, transform.translation)
        cnv_quatZupToYup(rot_quat(obj), transform.rotation)
        cnv_vec3(obj.scale, transform.scale)
        if obj.parent is not None:
            node.parent = obj.parent.name
        if (obj.type == "MESH"):
            if (len(obj.data.polygons) != 0):
                geometryObject = data.geometries.add()
                export_geometry(obj, geometryObject, scene, isPreview)
                add_relation(data.relations, node.id, geometryObject.id)


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


def add_relation(relations, src, dest):
    rel = relations.add()
    rel.src = src
    rel.dest = dest


def export_geometry(src, dst, scene, isPreview):
    dst.id = "geo_" + src.name
    mesh = dst.meshes.add()
    mesh.primitive = pgex.datas_pb2.Mesh.triangles
    mode = 'PREVIEW' if isPreview else 'RENDER'
    src_mesh = src.to_mesh(scene, True, mode, True, False)
    mesh.id = src_mesh.name
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
