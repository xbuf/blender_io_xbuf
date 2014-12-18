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

gloop = asyncio.get_event_loop()
RE_NAME = "external_renderer"
# http://wiki.blender.org/index.php/Dev:2.6/Source/Render/RenderEngineAPI
# http://wiki.blender.org/index.php/Dev:2.6/Source/Render/UpdateAPI
# http://www.blender.org/api/blender_python_api_2_72_release/bpy.types.RenderEngine.html


class ExternalRenderEngine(bpy.types.RenderEngine):
    # These three members are used by blender to set up the
    # RenderEngine; define its internal name, visible name and capabilities.
    bl_idname = RE_NAME
    bl_label = "External Renderer"
    bl_use_preview = True

    # moved assignment from execute() to the body of the class...
    port = bpy.props.IntProperty(name="port", default=4242, min=1024)
    host = bpy.props.StringProperty(name="host", default="127.0.0.1")
    loop = gloop

    def __init__(self):
        print("__init__")

    def __del__(self):
        print("__del__")

    @asyncio.coroutine
    def remote_render(self, width, height, flocal):
        import msgpack
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
        print("render")
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
        exp = MemoryOpenGexExporter()
        b = exp.exportToBytes(context)
        print(b)

    def view_draw(self, context):
        # from http://blender.stackexchange.com/questions/5035/moving-user-perspective-in-blender-with-python
        screen = context.screen.areas[2]
        # r3d = screen.spaces[0].region_3d # region_3d of 3D View
        r3d = context.space_data.region_3d
        loc = r3d.view_matrix.col[3][1:4]  # translation part of the view matrix
        width = int(screen.width)
        height = int(screen.height)
        print("view_draw {!r} :: {!r}x{!r}".format(r3d.view_matrix, width, height))

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

import bpy
import math
from bpy_extras.io_utils import ExportHelper


kNodeTypeNode = 0
kNodeTypeBone = 1
kNodeTypeGeometry = 2
kNodeTypeLight = 3
kNodeTypeCamera = 4

kAnimationSampled = 0
kAnimationLinear = 1
kAnimationBezier = 2

kExportEpsilon = 1.0e-6


structIdentifier = [B"Node $", B"BoneNode $", B"GeometryNode $", B"LightNode $", B"CameraNode $"]


subtranslationName = [B"xpos", B"ypos", B"zpos"]
subrotationName = [B"xrot", B"yrot", B"zrot"]
subscaleName = [B"xscl", B"yscl", B"zscl"]
deltaSubtranslationName = [B"dxpos", B"dypos", B"dzpos"]
deltaSubrotationName = [B"dxrot", B"dyrot", B"dzrot"]
deltaSubscaleName = [B"dxscl", B"dyscl", B"dzscl"]
axisName = [B"x", B"y", B"z"]


class ExportVertex:
    __slots__ = ("hash", "index", "position", "normal", "color", "texcoord0", "texcoord1")

    def __init__(self):
        self.color = [1.0, 1.0, 1.0]
        self.texcoord0 = [0.0, 0.0]
        self.texcoord1 = [0.0, 0.0]

    def __eq__(self, v):
        if (self.hash != v.hash):
            return (False)
        if (self.position != v.position):
            return (False)
        if (self.normal != v.normal):
            return (False)
        if (self.color != v.color):
            return (False)
        if (self.texcoord0 != v.texcoord0):
            return (False)
        if (self.texcoord1 != v.texcoord1):
            return (False)
        return (True)

    def Hash(self):
        h = hash(self.position[0])
        h = h * 21737 + hash(self.position[1])
        h = h * 21737 + hash(self.position[2])
        h = h * 21737 + hash(self.normal[0])
        h = h * 21737 + hash(self.normal[1])
        h = h * 21737 + hash(self.normal[2])
        h = h * 21737 + hash(self.color[0])
        h = h * 21737 + hash(self.color[1])
        h = h * 21737 + hash(self.color[2])
        h = h * 21737 + hash(self.texcoord0[0])
        h = h * 21737 + hash(self.texcoord0[1])
        h = h * 21737 + hash(self.texcoord1[0])
        h = h * 21737 + hash(self.texcoord1[1])
        self.hash = h

class OpenGexExporterBase(ExportHelper):

    def Write(self, text):
        self.file.write(text)


    def IndentWrite(self, text, extra = 0, newline = False):
        if (newline):
            self.file.write(B"\n")
        for i in range(self.indentLevel + extra):
            self.file.write(B"\t")
        self.file.write(text)


    def WriteInt(self, i):
        self.file.write(bytes(str(i), "UTF-8"))


    def WriteFloat(self, f):
        self.file.write(bytes(str(f), "UTF-8"))


    def WriteMatrix(self, matrix):
        self.IndentWrite(B"{", 1)
        self.WriteFloat(matrix[0][0])
        self.Write(B", ")
        self.WriteFloat(matrix[1][0])
        self.Write(B", ")
        self.WriteFloat(matrix[2][0])
        self.Write(B", ")
        self.WriteFloat(matrix[3][0])
        self.Write(B",\n")

        self.IndentWrite(B" ", 1)
        self.WriteFloat(matrix[0][1])
        self.Write(B", ")
        self.WriteFloat(matrix[1][1])
        self.Write(B", ")
        self.WriteFloat(matrix[2][1])
        self.Write(B", ")
        self.WriteFloat(matrix[3][1])
        self.Write(B",\n")

        self.IndentWrite(B" ", 1)
        self.WriteFloat(matrix[0][2])
        self.Write(B", ")
        self.WriteFloat(matrix[1][2])
        self.Write(B", ")
        self.WriteFloat(matrix[2][2])
        self.Write(B", ")
        self.WriteFloat(matrix[3][2])
        self.Write(B",\n")

        self.IndentWrite(B" ", 1)
        self.WriteFloat(matrix[0][3])
        self.Write(B", ")
        self.WriteFloat(matrix[1][3])
        self.Write(B", ")
        self.WriteFloat(matrix[2][3])
        self.Write(B", ")
        self.WriteFloat(matrix[3][3])
        self.Write(B"}\n")


    def WriteMatrixFlat(self, matrix):
        self.IndentWrite(B"{", 1)
        self.WriteFloat(matrix[0][0])
        self.Write(B", ")
        self.WriteFloat(matrix[1][0])
        self.Write(B", ")
        self.WriteFloat(matrix[2][0])
        self.Write(B", ")
        self.WriteFloat(matrix[3][0])
        self.Write(B", ")
        self.WriteFloat(matrix[0][1])
        self.Write(B", ")
        self.WriteFloat(matrix[1][1])
        self.Write(B", ")
        self.WriteFloat(matrix[2][1])
        self.Write(B", ")
        self.WriteFloat(matrix[3][1])
        self.Write(B", ")
        self.WriteFloat(matrix[0][2])
        self.Write(B", ")
        self.WriteFloat(matrix[1][2])
        self.Write(B", ")
        self.WriteFloat(matrix[2][2])
        self.Write(B", ")
        self.WriteFloat(matrix[3][2])
        self.Write(B", ")
        self.WriteFloat(matrix[0][3])
        self.Write(B", ")
        self.WriteFloat(matrix[1][3])
        self.Write(B", ")
        self.WriteFloat(matrix[2][3])
        self.Write(B", ")
        self.WriteFloat(matrix[3][3])
        self.Write(B"}")


    def WriteColor(self, color):
        self.Write(B"{")
        self.WriteFloat(color[0])
        self.Write(B", ")
        self.WriteFloat(color[1])
        self.Write(B", ")
        self.WriteFloat(color[2])
        self.Write(B"}")


    def WriteFileName(self, filename):
        length = len(filename)
        if (length != 0):
            if ((length > 2) and (filename[1] == ":")):
                self.Write(B"//")
                self.Write(bytes(filename[0], "UTF-8"))
                self.Write(bytes(filename[2:length].replace("\\", "/"), "UTF-8"))
            else:
                self.Write(bytes(filename.replace("\\", "/"), "UTF-8"))


    def WriteIntArray(self, valueArray):
        count = len(valueArray)
        k = 0

        lineCount = count >> 6
        for i in range(lineCount):
            self.IndentWrite(B"", 1)
            for j in range(63):
                self.WriteInt(valueArray[k])
                self.Write(B", ")
                k += 1

            self.WriteInt(valueArray[k])
            k += 1

            if (i * 64 < count - 64):
                self.Write(B",\n")
            else:
                self.Write(B"\n")

        count &= 63
        if (count != 0):
            self.IndentWrite(B"", 1)
            for j in range(count - 1):
                self.WriteInt(valueArray[k])
                self.Write(B", ")
                k += 1

            self.WriteInt(valueArray[k])
            self.Write(B"\n")


    def WriteFloatArray(self, valueArray):
        count = len(valueArray)
        k = 0

        lineCount = count >> 4
        for i in range(lineCount):
            self.IndentWrite(B"", 1)
            for j in range(15):
                self.WriteFloat(valueArray[k])
                self.Write(B", ")
                k += 1

            self.WriteFloat(valueArray[k])
            k += 1

            if (i * 16 < count - 16):
                self.Write(B",\n")
            else:
                self.Write(B"\n")

        count &= 15
        if (count != 0):
            self.IndentWrite(B"", 1)
            for j in range(count - 1):
                self.WriteFloat(valueArray[k])
                self.Write(B", ")
                k += 1

            self.WriteFloat(valueArray[k])
            self.Write(B"\n")


    def WriteVector2D(self, vector):
        self.Write(B"{")
        self.WriteFloat(vector[0])
        self.Write(B", ")
        self.WriteFloat(vector[1])
        self.Write(B"}")


    def WriteVector3D(self, vector):
        self.Write(B"{")
        self.WriteFloat(vector[0])
        self.Write(B", ")
        self.WriteFloat(vector[1])
        self.Write(B", ")
        self.WriteFloat(vector[2])
        self.Write(B"}")


    def WriteVector4D(self, vector):
        self.Write(B"{")
        self.WriteFloat(vector[0])
        self.Write(B", ")
        self.WriteFloat(vector[1])
        self.Write(B", ")
        self.WriteFloat(vector[2])
        self.Write(B", ")
        self.WriteFloat(vector[3])
        self.Write(B"}")


    def WriteQuaternion(self, quaternion):
        self.Write(B"{")
        self.WriteFloat(quaternion[1])
        self.Write(B", ")
        self.WriteFloat(quaternion[2])
        self.Write(B", ")
        self.WriteFloat(quaternion[3])
        self.Write(B", ")
        self.WriteFloat(quaternion[0])
        self.Write(B"}")


    def WriteVertexArray2D(self, vertexArray, attrib):
        count = len(vertexArray)
        k = 0

        lineCount = count >> 3
        for i in range(lineCount):
            self.IndentWrite(B"", 1)
            for j in range(7):
                self.WriteVector2D(getattr(vertexArray[k], attrib))
                self.Write(B", ")
                k += 1

            self.WriteVector2D(getattr(vertexArray[k], attrib))
            k += 1

            if (i * 8 < count - 8):
                self.Write(B",\n")
            else:
                self.Write(B"\n")

        count &= 7
        if (count != 0):
            self.IndentWrite(B"", 1)
            for j in range(count - 1):
                self.WriteVector2D(getattr(vertexArray[k], attrib))
                self.Write(B", ")
                k += 1

            self.WriteVector2D(getattr(vertexArray[k], attrib))
            self.Write(B"\n")


    def WriteVertexArray3D(self, vertexArray, attrib):
        count = len(vertexArray)
        k = 0

        lineCount = count >> 3
        for i in range(lineCount):
            self.IndentWrite(B"", 1)
            for j in range(7):
                self.WriteVector3D(getattr(vertexArray[k], attrib))
                self.Write(B", ")
                k += 1

            self.WriteVector3D(getattr(vertexArray[k], attrib))
            k += 1

            if (i * 8 < count - 8):
                self.Write(B",\n")
            else:
                self.Write(B"\n")

        count &= 7
        if (count != 0):
            self.IndentWrite(B"", 1)
            for j in range(count - 1):
                self.WriteVector3D(getattr(vertexArray[k], attrib))
                self.Write(B", ")
                k += 1

            self.WriteVector3D(getattr(vertexArray[k], attrib))
            self.Write(B"\n")


    def WriteTriangle(self, triangleIndex, indexTable):
        i = triangleIndex * 3
        self.Write(B"{")
        self.WriteInt(indexTable[i])
        self.Write(B", ")
        self.WriteInt(indexTable[i + 1])
        self.Write(B", ")
        self.WriteInt(indexTable[i + 2])
        self.Write(B"}")


    def WriteTriangleArray(self, count, indexTable):
        triangleIndex = 0

        lineCount = count >> 4
        for i in range(lineCount):
            self.IndentWrite(B"", 1)
            for j in range(15):
                self.WriteTriangle(triangleIndex, indexTable)
                self.Write(B", ")
                triangleIndex += 1

            self.WriteTriangle(triangleIndex, indexTable)
            triangleIndex += 1

            if (i * 16 < count - 16):
                self.Write(B",\n")
            else:
                self.Write(B"\n")

        count &= 15
        if (count != 0):
            self.IndentWrite(B"", 1)
            for j in range(count - 1):
                self.WriteTriangle(triangleIndex, indexTable)
                self.Write(B", ")
                triangleIndex += 1

            self.WriteTriangle(triangleIndex, indexTable)
            self.Write(B"\n")


    def WriteNodeTable(self, objectRef):
        first = True
        for node in objectRef[1]["nodeTable"]:
            if (first):
                self.Write(B"\t\t// ")
            else:
                self.Write(B", ")
            self.Write(bytes(node.name, "UTF-8"))
            first = False


    @staticmethod
    def GetNodeType(node):
        if (node.type == "MESH"):
            if (len(node.data.polygons) != 0):
                return (kNodeTypeGeometry)
        elif (node.type == "LAMP"):
            return (kNodeTypeLight)
        elif (node.type == "CAMERA"):
            return (kNodeTypeCamera)

        return (kNodeTypeNode)


    def FindNode(self, name):
        for nodeRef in self.nodeArray.items():
            if (nodeRef[0].name == name):
                return (nodeRef)
        return (None)


    @staticmethod
    def DeindexMesh(mesh, materialTable):

        # This function deindexes all vertex positions, colors, and texcoords.
        # Three separate ExportVertex structures are created for each triangle.

        vertexArray = mesh.vertices
        exportVertexArray = []

        for face in mesh.tessfaces:
            k1 = face.vertices[0]
            k2 = face.vertices[1]
            k3 = face.vertices[2]

            v1 = vertexArray[k1]
            v2 = vertexArray[k2]
            v3 = vertexArray[k3]

            exportVertex = ExportVertex()
            exportVertex.index = k1
            exportVertex.position = v1.co
            exportVertex.normal = v1.normal
            exportVertexArray.append(exportVertex)

            exportVertex = ExportVertex()
            exportVertex.index = k2
            exportVertex.position = v2.co
            exportVertex.normal = v2.normal
            exportVertexArray.append(exportVertex)

            exportVertex = ExportVertex()
            exportVertex.index = k3
            exportVertex.position = v3.co
            exportVertex.normal = v3.normal
            exportVertexArray.append(exportVertex)

            materialTable.append(face.material_index)

            if (len(face.vertices) == 4):
                k1 = face.vertices[0]
                k2 = face.vertices[2]
                k3 = face.vertices[3]

                v1 = vertexArray[k1]
                v2 = vertexArray[k2]
                v3 = vertexArray[k3]

                exportVertex = ExportVertex()
                exportVertex.index = k1
                exportVertex.position = v1.co
                exportVertex.normal = v1.normal
                exportVertexArray.append(exportVertex)

                exportVertex = ExportVertex()
                exportVertex.index = k2
                exportVertex.position = v2.co
                exportVertex.normal = v2.normal
                exportVertexArray.append(exportVertex)

                exportVertex = ExportVertex()
                exportVertex.index = k3
                exportVertex.position = v3.co
                exportVertex.normal = v3.normal
                exportVertexArray.append(exportVertex)

                materialTable.append(face.material_index)

        colorCount = len(mesh.tessface_vertex_colors)
        if (colorCount > 0):
            colorFace = mesh.tessface_vertex_colors[0].data
            vertexIndex = 0
            faceIndex = 0

            for face in mesh.tessfaces:
                cf = colorFace[faceIndex]
                exportVertexArray[vertexIndex].color = cf.color1
                vertexIndex += 1
                exportVertexArray[vertexIndex].color = cf.color2
                vertexIndex += 1
                exportVertexArray[vertexIndex].color = cf.color3
                vertexIndex += 1

                if (len(face.vertices) == 4):
                    exportVertexArray[vertexIndex].color = cf.color1
                    vertexIndex += 1
                    exportVertexArray[vertexIndex].color = cf.color3
                    vertexIndex += 1
                    exportVertexArray[vertexIndex].color = cf.color4
                    vertexIndex += 1

                faceIndex += 1

        texcoordCount = len(mesh.tessface_uv_textures)
        if (texcoordCount > 0):
            texcoordFace = mesh.tessface_uv_textures[0].data
            vertexIndex = 0
            faceIndex = 0

            for face in mesh.tessfaces:
                tf = texcoordFace[faceIndex]
                exportVertexArray[vertexIndex].texcoord0 = tf.uv1
                vertexIndex += 1
                exportVertexArray[vertexIndex].texcoord0 = tf.uv2
                vertexIndex += 1
                exportVertexArray[vertexIndex].texcoord0 = tf.uv3
                vertexIndex += 1

                if (len(face.vertices) == 4):
                    exportVertexArray[vertexIndex].texcoord0 = tf.uv1
                    vertexIndex += 1
                    exportVertexArray[vertexIndex].texcoord0 = tf.uv3
                    vertexIndex += 1
                    exportVertexArray[vertexIndex].texcoord0 = tf.uv4
                    vertexIndex += 1

                faceIndex += 1

            if (texcoordCount > 1):
                texcoordFace = mesh.tessface_uv_textures[1].data
                vertexIndex = 0
                faceIndex = 0

                for face in mesh.tessfaces:
                    tf = texcoordFace[faceIndex]
                    exportVertexArray[vertexIndex].texcoord1 = tf.uv1
                    vertexIndex += 1
                    exportVertexArray[vertexIndex].texcoord1 = tf.uv2
                    vertexIndex += 1
                    exportVertexArray[vertexIndex].texcoord1 = tf.uv3
                    vertexIndex += 1

                    if (len(face.vertices) == 4):
                        exportVertexArray[vertexIndex].texcoord1 = tf.uv1
                        vertexIndex += 1
                        exportVertexArray[vertexIndex].texcoord1 = tf.uv3
                        vertexIndex += 1
                        exportVertexArray[vertexIndex].texcoord1 = tf.uv4
                        vertexIndex += 1

                    faceIndex += 1

        for ev in exportVertexArray:
            ev.Hash()

        return (exportVertexArray)


    @staticmethod
    def FindExportVertex(bucket, exportVertexArray, vertex):
        for index in bucket:
            if (exportVertexArray[index] == vertex):
                return (index)

        return (-1)


    @staticmethod
    def UnifyVertices(exportVertexArray, indexTable):

        # This function looks for identical vertices having exactly the same position, normal,
        # color, and texcoords. Duplicate vertices are unified, and a new index table is returned.

        bucketCount = len(exportVertexArray) >> 5
        if (bucketCount > 1):

            # Round down to nearest power of two.

            while True:
                count = bucketCount & (bucketCount - 1)
                if (count == 0):
                    break
                bucketCount = count
        else:
            bucketCount = 1

        hashTable = [[] for i in range(bucketCount)]
        unifiedVertexArray = []

        for i in range(len(exportVertexArray)):
            ev = exportVertexArray[i]
            bucket = ev.hash & (bucketCount - 1)
            index = OpenGexExporterBase.FindExportVertex(hashTable[bucket], exportVertexArray, ev)
            if (index < 0):
                indexTable.append(len(unifiedVertexArray))
                unifiedVertexArray.append(ev)
                hashTable[bucket].append(i)
            else:
                indexTable.append(indexTable[index])

        return (unifiedVertexArray)


    def ProcessBone(self, bone, exportAllFlag):
        if ((exportAllFlag) or (bone.select)):
            self.nodeArray[bone] = {"nodeType" : kNodeTypeBone, "structName" : bytes("node" + str(len(self.nodeArray) + 1), "UTF-8")}

        for subnode in bone.children:
            self.ProcessBone(subnode, exportAllFlag)


    def ProcessNode(self, node, exportAllFlag):
        if ((exportAllFlag) or (node.select)):
            type = OpenGexExporter.GetNodeType(node)
            self.nodeArray[node] = {"nodeType" : type, "structName" : bytes("node" + str(len(self.nodeArray) + 1), "UTF-8")}

            if (node.parent_type == "BONE"):
                boneSubnodeArray = self.boneParentArray.get(node.parent_bone)
                if (boneSubnodeArray):
                    boneSubnodeArray.append(node)
                else:
                    self.boneParentArray[node.parent_bone] = [node]

            if (node.type == "ARMATURE"):
                skeleton = node.data
                if (skeleton):
                    for bone in skeleton.bones:
                        if (bone.parent == None):
                            self.ProcessBone(bone, exportAllFlag)

        for subnode in node.children:
            self.ProcessNode(subnode, exportAllFlag)


    @staticmethod
    def ClassifyAnimationCurve(fcurve):
        linearCount = 0
        bezierCount = 0

        for key in fcurve.keyframe_points:
            interp = key.interpolation
            if (interp == "LINEAR"):
                linearCount += 1
            elif (interp == "BEZIER"):
                bezierCount += 1
            else:
                return (kAnimationSampled)

        if (bezierCount == 0):
            return (kAnimationLinear)
        elif (linearCount == 0):
            return (kAnimationBezier)

        return (kAnimationSampled)


    @staticmethod
    def AnimationKeysDifferent(fcurve):
        keyCount = len(fcurve.keyframe_points)
        if (keyCount > 0):
            key1 = fcurve.keyframe_points[0].co[1]

            for i in range(1, keyCount):
                key2 = fcurve.keyframe_points[i].co[1]
                if (math.fabs(key2 - key1) > kExportEpsilon):
                    return (True)

        return (False)


    @staticmethod
    def AnimationTangentsNonzero(fcurve):
        keyCount = len(fcurve.keyframe_points)
        if (keyCount > 0):
            key = fcurve.keyframe_points[0].co[1]
            left = fcurve.keyframe_points[0].handle_left[1]
            right = fcurve.keyframe_points[0].handle_right[1]
            if ((math.fabs(key - left) > kExportEpsilon) or (math.fabs(right - key) > kExportEpsilon)):
                return (True)

            for i in range(1, keyCount):
                key = fcurve.keyframe_points[i].co[1]
                left = fcurve.keyframe_points[i].handle_left[1]
                right = fcurve.keyframe_points[i].handle_right[1]
                if ((math.fabs(key - left) > kExportEpsilon) or (math.fabs(right - key) > kExportEpsilon)):
                    return (True)

        return (False)


    @staticmethod
    def AnimationPresent(fcurve, kind):
        if (kind != kAnimationBezier):
            return (OpenGexExporter.AnimationKeysDifferent(fcurve))
        return ((OpenGexExporter.AnimationKeysDifferent(fcurve)) or (OpenGexExporter.AnimationTangentsNonzero(fcurve)))


    @staticmethod
    def CollectBoneAnimation(armature, name):
        path = "pose.bones[\"" + name + "\"]."
        curveArray = []

        if (armature.animation_data):
            action = armature.animation_data.action
            if (action):
                for fcurve in action.fcurves:
                    if (fcurve.data_path.startswith(path)):
                        curveArray.append(fcurve)

        return (curveArray)


    def ExportKeyTimes(self, fcurve):
        self.IndentWrite(B"Key {float {")

        keyCount = len(fcurve.keyframe_points)
        for i in range(keyCount):
            if (i > 0):
                self.Write(B", ")

            time = fcurve.keyframe_points[i].co[0] - self.beginFrame
            self.WriteFloat(time * self.frameTime)

        self.Write(B"}}\n")


    def ExportKeyTimeControlPoints(self, fcurve):
        self.IndentWrite(B"Key (kind = \"-control\") {float {")

        keyCount = len(fcurve.keyframe_points)
        for i in range(keyCount):
            if (i > 0):
                self.Write(B", ")

            ctrl = fcurve.keyframe_points[i].handle_left[0] - self.beginFrame
            self.WriteFloat(ctrl * self.frameTime)

        self.Write(B"}}\n")
        self.IndentWrite(B"Key (kind = \"+control\") {float {")

        for i in range(keyCount):
            if (i > 0):
                self.Write(B", ")

            ctrl = fcurve.keyframe_points[i].handle_right[0] - self.beginFrame
            self.WriteFloat(ctrl * self.frameTime)

        self.Write(B"}}\n")


    def ExportKeyValues(self, fcurve):
        self.IndentWrite(B"Key {float {")

        keyCount = len(fcurve.keyframe_points)
        for i in range(keyCount):
            if (i > 0):
                self.Write(B", ")

            value = fcurve.keyframe_points[i].co[1]
            self.WriteFloat(value)

        self.Write(B"}}\n")


    def ExportKeyValueControlPoints(self, fcurve):
        self.IndentWrite(B"Key (kind = \"-control\") {float {")

        keyCount = len(fcurve.keyframe_points)
        for i in range(keyCount):
            if (i > 0):
                self.Write(B", ")

            ctrl = fcurve.keyframe_points[i].handle_left[1]
            self.WriteFloat(ctrl)

        self.Write(B"}}\n")
        self.IndentWrite(B"Key (kind = \"+control\") {float {")

        for i in range(keyCount):
            if (i > 0):
                self.Write(B", ")

            ctrl = fcurve.keyframe_points[i].handle_right[1]
            self.WriteFloat(ctrl)

        self.Write(B"}}\n")


    def ExportAnimationTrack(self, fcurve, kind, target, newline):

        # This function exports a single animation track. The curve types for the
        # Time and Value structures are given by the kind parameter.

        self.IndentWrite(B"Track (target = %", 0, newline)
        self.Write(target)
        self.Write(B")\n")
        self.IndentWrite(B"{\n")
        self.indentLevel += 1

        if (kind != kAnimationBezier):
            self.IndentWrite(B"Time\n")
            self.IndentWrite(B"{\n")
            self.indentLevel += 1

            self.ExportKeyTimes(fcurve)

            self.IndentWrite(B"}\n\n", -1)
            self.IndentWrite(B"Value\n", -1)
            self.IndentWrite(B"{\n", -1)

            self.ExportKeyValues(fcurve)

            self.indentLevel -= 1
            self.IndentWrite(B"}\n")

        else:
            self.IndentWrite(B"Time (curve = \"bezier\")\n")
            self.IndentWrite(B"{\n")
            self.indentLevel += 1

            self.ExportKeyTimes(fcurve)
            self.ExportKeyTimeControlPoints(fcurve)

            self.IndentWrite(B"}\n\n", -1)
            self.IndentWrite(B"Value (curve = \"bezier\")\n", -1)
            self.IndentWrite(B"{\n", -1)

            self.ExportKeyValues(fcurve)
            self.ExportKeyValueControlPoints(fcurve)

            self.indentLevel -= 1
            self.IndentWrite(B"}\n")

        self.indentLevel -= 1
        self.IndentWrite(B"}\n")


    def ExportSampledAnimationTrack(self, node, scene):

        # This function exports animation as full 4x4 matrices for each frame.

        self.IndentWrite(B"Animation\n", 0, True)
        self.IndentWrite(B"{\n")
        self.indentLevel += 1

        self.IndentWrite(B"Track (target = %transform)\n")
        self.IndentWrite(B"{\n")
        self.indentLevel += 1

        self.IndentWrite(B"Time\n")
        self.IndentWrite(B"{\n")
        self.indentLevel += 1

        self.IndentWrite(B"Key {float {")

        for i in range(self.beginFrame, self.endFrame):
            self.WriteFloat((i - self.beginFrame) * self.frameTime)
            self.Write(B", ")

        self.WriteFloat(self.endFrame * self.frameTime)
        self.Write(B"}}\n")

        self.IndentWrite(B"}\n\n", -1)
        self.IndentWrite(B"Value\n", -1)
        self.IndentWrite(B"{\n", -1)

        self.IndentWrite(B"Key\n")
        self.IndentWrite(B"{\n")
        self.indentLevel += 1

        self.IndentWrite(B"float[16]\n")
        self.IndentWrite(B"{\n")

        currentFrame = scene.frame_current
        currentSubframe = scene.frame_subframe

        for i in range(self.beginFrame, self.endFrame):
            scene.frame_set(i)
            self.WriteMatrixFlat(node.matrix_local)
            self.Write(B",\n")

        scene.frame_set(self.endFrame)
        self.WriteMatrixFlat(node.matrix_local)
        self.IndentWrite(B"}\n", 0, True)

        scene.frame_set(currentFrame, currentSubframe)

        self.indentLevel -= 1
        self.IndentWrite(B"}\n")

        self.indentLevel -= 1
        self.IndentWrite(B"}\n")

        self.indentLevel -= 1
        self.IndentWrite(B"}\n")

        self.indentLevel -= 1
        self.IndentWrite(B"}\n")


    def ExportBoneSampledAnimationTrack(self, poseBone, scene):

        # This function exports bone animation as full 4x4 matrices for each frame.

        self.IndentWrite(B"Animation\n", 0, True)
        self.IndentWrite(B"{\n")
        self.indentLevel += 1

        self.IndentWrite(B"Track (target = %transform)\n")
        self.IndentWrite(B"{\n")
        self.indentLevel += 1

        self.IndentWrite(B"Time\n")
        self.IndentWrite(B"{\n")
        self.indentLevel += 1

        self.IndentWrite(B"Key {float {")

        for i in range(self.beginFrame, self.endFrame):
            self.WriteFloat((i - self.beginFrame) * self.frameTime)
            self.Write(B", ")

        self.WriteFloat(self.endFrame * self.frameTime)
        self.Write(B"}}\n")

        self.IndentWrite(B"}\n\n", -1)
        self.IndentWrite(B"Value\n", -1)
        self.IndentWrite(B"{\n", -1)

        self.IndentWrite(B"Key\n")
        self.IndentWrite(B"{\n")
        self.indentLevel += 1

        self.IndentWrite(B"float[16]\n")
        self.IndentWrite(B"{\n")

        currentFrame = scene.frame_current
        currentSubframe = scene.frame_subframe

        parent = poseBone.parent
        if (parent):
            for i in range(self.beginFrame, self.endFrame):
                scene.frame_set(i)
                self.WriteMatrixFlat(parent.matrix.inverted() * poseBone.matrix)
                self.Write(B",\n")

            scene.frame_set(self.endFrame)
            self.WriteMatrixFlat(parent.matrix.inverted() * poseBone.matrix)
            self.IndentWrite(B"}\n", 0, True)

        else:
            for i in range(self.beginFrame, self.endFrame):
                scene.frame_set(i)
                self.WriteMatrixFlat(poseBone.matrix)
                self.Write(B",\n")

            scene.frame_set(self.endFrame)
            self.WriteMatrixFlat(poseBone.matrix)
            self.IndentWrite(B"}\n", 0, True)

        scene.frame_set(currentFrame, currentSubframe)

        self.indentLevel -= 1
        self.IndentWrite(B"}\n")

        self.indentLevel -= 1
        self.IndentWrite(B"}\n")

        self.indentLevel -= 1
        self.IndentWrite(B"}\n")

        self.indentLevel -= 1
        self.IndentWrite(B"}\n")


    def ExportNodeTransform(self, node, scene):
        posAnimCurve = [None, None, None]
        rotAnimCurve = [None, None, None]
        sclAnimCurve = [None, None, None]
        posAnimKind = [0, 0, 0]
        rotAnimKind = [0, 0, 0]
        sclAnimKind = [0, 0, 0]

        deltaPosAnimCurve = [None, None, None]
        deltaRotAnimCurve = [None, None, None]
        deltaSclAnimCurve = [None, None, None]
        deltaPosAnimKind = [0, 0, 0]
        deltaRotAnimKind = [0, 0, 0]
        deltaSclAnimKind = [0, 0, 0]

        positionAnimated = False
        rotationAnimated = False
        scaleAnimated = False
        posAnimated = [False, False, False]
        rotAnimated = [False, False, False]
        sclAnimated = [False, False, False]

        deltaPositionAnimated = False
        deltaRotationAnimated = False
        deltaScaleAnimated = False
        deltaPosAnimated = [False, False, False]
        deltaRotAnimated = [False, False, False]
        deltaSclAnimated = [False, False, False]

        mode = node.rotation_mode
        sampledAnimation = ((mode == "QUATERNION") or (mode == "AXIS_ANGLE"))

        if (node.animation_data):
            action = node.animation_data.action
            if (action):
                for fcurve in action.fcurves:
                    kind = OpenGexExporter.ClassifyAnimationCurve(fcurve)
                    if (kind != kAnimationSampled):
                        if (fcurve.data_path == "location"):
                            for i in range(3):
                                if ((fcurve.array_index == i) and (posAnimCurve[i] == None)):
                                    posAnimCurve[i] = fcurve
                                    posAnimKind[i] = kind
                                    if (OpenGexExporter.AnimationPresent(fcurve, kind)):
                                        posAnimated[i] = True
                        elif (fcurve.data_path == "delta_location"):
                            for i in range(3):
                                if ((fcurve.array_index == i) and (deltaPosAnimCurve[i] == None)):
                                    deltaPosAnimCurve[i] = fcurve
                                    deltaPosAnimKind[i] = kind
                                    if (OpenGexExporter.AnimationPresent(fcurve, kind)):
                                        deltaPosAnimated[i] = True
                        elif (fcurve.data_path == "rotation_euler"):
                            for i in range(3):
                                if ((fcurve.array_index == i) and (rotAnimCurve[i] == None)):
                                    rotAnimCurve[i] = fcurve
                                    rotAnimKind[i] = kind
                                    if (OpenGexExporter.AnimationPresent(fcurve, kind)):
                                        rotAnimated[i] = True
                        elif (fcurve.data_path == "delta_rotation_euler"):
                            for i in range(3):
                                if ((fcurve.array_index == i) and (deltaRotAnimCurve[i] == None)):
                                    deltaRotAnimCurve[i] = fcurve
                                    deltaRotAnimKind[i] = kind
                                    if (OpenGexExporter.AnimationPresent(fcurve, kind)):
                                        deltaRotAnimated[i] = True
                        elif (fcurve.data_path == "scale"):
                            for i in range(3):
                                if ((fcurve.array_index == i) and (sclAnimCurve[i] == None)):
                                    sclAnimCurve[i] = fcurve
                                    sclAnimKind[i] = kind
                                    if (OpenGexExporter.AnimationPresent(fcurve, kind)):
                                        sclAnimated[i] = True
                        elif (fcurve.data_path == "delta_scale"):
                            for i in range(3):
                                if ((fcurve.array_index == i) and (deltaSclAnimCurve[i] == None)):
                                    deltaSclAnimCurve[i] = fcurve
                                    deltaSclAnimKind[i] = kind
                                    if (OpenGexExporter.AnimationPresent(fcurve, kind)):
                                        deltaSclAnimated[i] = True
                        elif ((fcurve.data_path == "rotation_axis_angle") or (fcurve.data_path == "rotation_quaternion") or (fcurve.data_path == "delta_rotation_quaternion")):
                            sampledAnimation = True
                    else:
                        sampledAnimation = True
                        break

        positionAnimated = posAnimated[0] | posAnimated[1] | posAnimated[2]
        rotationAnimated = rotAnimated[0] | rotAnimated[1] | rotAnimated[2]
        scaleAnimated = sclAnimated[0] | sclAnimated[1] | sclAnimated[2]

        deltaPositionAnimated = deltaPosAnimated[0] | deltaPosAnimated[1] | deltaPosAnimated[2]
        deltaRotationAnimated = deltaRotAnimated[0] | deltaRotAnimated[1] | deltaRotAnimated[2]
        deltaScaleAnimated = deltaSclAnimated[0] | deltaSclAnimated[1] | deltaSclAnimated[2]

        if ((sampledAnimation) or ((not positionAnimated) and (not rotationAnimated) and (not scaleAnimated) and (not deltaPositionAnimated) and (not deltaRotationAnimated) and (not deltaScaleAnimated))):

            # If there's no keyframe animation at all, then write the node transform as a single 4x4 matrix.
            # We might still be exporting sampled animation below.

            self.IndentWrite(B"Transform")

            if (sampledAnimation):
                self.Write(B" %transform")

            self.IndentWrite(B"{\n", 0, True)
            self.indentLevel += 1

            self.IndentWrite(B"float[16]\n")
            self.IndentWrite(B"{\n")
            self.WriteMatrix(node.matrix_local)
            self.IndentWrite(B"}\n")

            self.indentLevel -= 1
            self.IndentWrite(B"}\n")

            if (sampledAnimation):
                self.ExportSampledAnimationTrack(node, scene)

        else:
            structFlag = False

            deltaTranslation = node.delta_location
            if (deltaPositionAnimated):

                # When the delta location is animated, write the x, y, and z components separately
                # so they can be targeted by different tracks having different sets of keys.

                for i in range(3):
                    pos = deltaTranslation[i]
                    if ((deltaPosAnimated[i]) or (math.fabs(pos) > kExportEpsilon)):
                        self.IndentWrite(B"Translation %", 0, structFlag)
                        self.Write(deltaSubtranslationName[i])
                        self.Write(B" (kind = \"")
                        self.Write(axisName[i])
                        self.Write(B"\")\n")
                        self.IndentWrite(B"{\n")
                        self.IndentWrite(B"float {", 1)
                        self.WriteFloat(pos)
                        self.Write(B"}")
                        self.IndentWrite(B"}\n", 0, True)

                        structFlag = True

            elif ((math.fabs(deltaTranslation[0]) > kExportEpsilon) or (math.fabs(deltaTranslation[1]) > kExportEpsilon) or (math.fabs(deltaTranslation[2]) > kExportEpsilon)):
                self.IndentWrite(B"Translation\n")
                self.IndentWrite(B"{\n")
                self.IndentWrite(B"float[3] {", 1)
                self.WriteVector3D(deltaTranslation)
                self.Write(B"}")
                self.IndentWrite(B"}\n", 0, True)

                structFlag = True

            translation = node.location
            if (positionAnimated):

                # When the location is animated, write the x, y, and z components separately
                # so they can be targeted by different tracks having different sets of keys.

                for i in range(3):
                    pos = translation[i]
                    if ((posAnimated[i]) or (math.fabs(pos) > kExportEpsilon)):
                        self.IndentWrite(B"Translation %", 0, structFlag)
                        self.Write(subtranslationName[i])
                        self.Write(B" (kind = \"")
                        self.Write(axisName[i])
                        self.Write(B"\")\n")
                        self.IndentWrite(B"{\n")
                        self.IndentWrite(B"float {", 1)
                        self.WriteFloat(pos)
                        self.Write(B"}")
                        self.IndentWrite(B"}\n", 0, True)

                        structFlag = True

            elif ((math.fabs(translation[0]) > kExportEpsilon) or (math.fabs(translation[1]) > kExportEpsilon) or (math.fabs(translation[2]) > kExportEpsilon)):
                self.IndentWrite(B"Translation\n")
                self.IndentWrite(B"{\n")
                self.IndentWrite(B"float[3] {", 1)
                self.WriteVector3D(translation)
                self.Write(B"}")
                self.IndentWrite(B"}\n", 0, True)

                structFlag = True

            if (deltaRotationAnimated):

                # When the delta rotation is animated, write three separate Euler angle rotations
                # so they can be targeted by different tracks having different sets of keys.

                for i in range(3):
                    axis = ord(mode[i]) - 0x58
                    angle = node.delta_rotation_euler[axis]
                    if ((deltaRotAnimated[axis]) or (math.fabs(angle) > kExportEpsilon)):
                        self.IndentWrite(B"Rotation %", 0, structFlag)
                        self.Write(deltaSubrotationName[axis])
                        self.Write(B" (kind = \"")
                        self.Write(axisName[axis])
                        self.Write(B"\")\n")
                        self.IndentWrite(B"{\n")
                        self.IndentWrite(B"float {", 1)
                        self.WriteFloat(angle)
                        self.Write(B"}")
                        self.IndentWrite(B"}\n", 0, True)

                        structFlag = True

            else:

                # When the delta rotation is not animated, write it in the representation given by
                # the node's current rotation mode. (There is no axis-angle delta rotation.)

                if (mode == "QUATERNION"):
                    quaternion = node.delta_rotation_quaternion
                    if ((math.fabs(quaternion[0] - 1.0) > kExportEpsilon) or (math.fabs(quaternion[1]) > kExportEpsilon) or (math.fabs(quaternion[2]) > kExportEpsilon) or (math.fabs(quaternion[3]) > kExportEpsilon)):
                        self.IndentWrite(B"Rotation (kind = \"quaternion\")\n", 0, structFlag)
                        self.IndentWrite(B"{\n")
                        self.IndentWrite(B"float[4] {", 1)
                        self.WriteQuaternion(quaternion)
                        self.Write(B"}")
                        self.IndentWrite(B"}\n", 0, True)

                        structFlag = True

                else:
                    for i in range(3):
                        axis = ord(mode[i]) - 0x58
                        angle = node.delta_rotation_euler[axis]
                        if (math.fabs(angle) > kExportEpsilon):
                            self.IndentWrite(B"Rotation (kind = \"", 0, structFlag)
                            self.Write(axisName[axis])
                            self.Write(B"\")\n")
                            self.IndentWrite(B"{\n")
                            self.IndentWrite(B"float {", 1)
                            self.WriteFloat(angle)
                            self.Write(B"}")
                            self.IndentWrite(B"}\n", 0, True)

                            structFlag = True

            if (rotationAnimated):

                # When the rotation is animated, write three separate Euler angle rotations
                # so they can be targeted by different tracks having different sets of keys.

                for i in range(3):
                    axis = ord(mode[i]) - 0x58
                    angle = node.rotation_euler[axis]
                    if ((rotAnimated[axis]) or (math.fabs(angle) > kExportEpsilon)):
                        self.IndentWrite(B"Rotation %", 0, structFlag)
                        self.Write(subrotationName[axis])
                        self.Write(B" (kind = \"")
                        self.Write(axisName[axis])
                        self.Write(B"\")\n")
                        self.IndentWrite(B"{\n")
                        self.IndentWrite(B"float {", 1)
                        self.WriteFloat(angle)
                        self.Write(B"}")
                        self.IndentWrite(B"}\n", 0, True)

                        structFlag = True

            else:

                # When the rotation is not animated, write it in the representation given by
                # the node's current rotation mode.

                if (mode == "QUATERNION"):
                    quaternion = node.rotation_quaternion
                    if ((math.fabs(quaternion[0] - 1.0) > kExportEpsilon) or (math.fabs(quaternion[1]) > kExportEpsilon) or (math.fabs(quaternion[2]) > kExportEpsilon) or (math.fabs(quaternion[3]) > kExportEpsilon)):
                        self.IndentWrite(B"Rotation (kind = \"quaternion\")\n", 0, structFlag)
                        self.IndentWrite(B"{\n")
                        self.IndentWrite(B"float[4] {", 1)
                        self.WriteQuaternion(quaternion)
                        self.Write(B"}")
                        self.IndentWrite(B"}\n", 0, True)

                        structFlag = True

                elif (mode == "AXIS_ANGLE"):
                    if (math.fabs(node.rotation_axis_angle[0]) > kExportEpsilon):
                        self.IndentWrite(B"Rotation (kind = \"axis\")\n", 0, structFlag)
                        self.IndentWrite(B"{\n")
                        self.IndentWrite(B"float[4] {", 1)
                        self.WriteVector4D(node.rotation_axis_angle)
                        self.Write(B"}")
                        self.IndentWrite(B"}\n", 0, True)

                        structFlag = True

                else:
                    for i in range(3):
                        axis = ord(mode[i]) - 0x58
                        angle = node.rotation_euler[axis]
                        if (math.fabs(angle) > kExportEpsilon):
                            self.IndentWrite(B"Rotation (kind = \"", 0, structFlag)
                            self.Write(axisName[axis])
                            self.Write(B"\")\n")
                            self.IndentWrite(B"{\n")
                            self.IndentWrite(B"float {", 1)
                            self.WriteFloat(angle)
                            self.Write(B"}")
                            self.IndentWrite(B"}\n", 0, True)

                            structFlag = True

            deltaScale = node.delta_scale
            if (deltaScaleAnimated):

                # When the delta scale is animated, write the x, y, and z components separately
                # so they can be targeted by different tracks having different sets of keys.

                for i in range(3):
                    scl = deltaScale[i]
                    if ((deltaSclAnimated[i]) or (math.fabs(scl) > kExportEpsilon)):
                        self.IndentWrite(B"Scale %", 0, structFlag)
                        self.Write(deltaSubscaleName[i])
                        self.Write(B" (kind = \"")
                        self.Write(axisName[i])
                        self.Write(B"\")\n")
                        self.IndentWrite(B"{\n")
                        self.IndentWrite(B"float {", 1)
                        self.WriteFloat(scl)
                        self.Write(B"}")
                        self.IndentWrite(B"}\n", 0, True)

                        structFlag = True

            elif ((math.fabs(deltaScale[0] - 1.0) > kExportEpsilon) or (math.fabs(deltaScale[1] - 1.0) > kExportEpsilon) or (math.fabs(deltaScale[2] - 1.0) > kExportEpsilon)):
                self.IndentWrite(B"Scale\n", 0, structFlag)
                self.IndentWrite(B"{\n")
                self.IndentWrite(B"float[3] {", 1)
                self.WriteVector3D(deltaScale)
                self.Write(B"}")
                self.IndentWrite(B"}\n", 0, True)

                structFlag = True

            scale = node.scale
            if (scaleAnimated):

                # When the scale is animated, write the x, y, and z components separately
                # so they can be targeted by different tracks having different sets of keys.

                for i in range(3):
                    scl = scale[i]
                    if ((sclAnimated[i]) or (math.fabs(scl) > kExportEpsilon)):
                        self.IndentWrite(B"Scale %", 0, structFlag)
                        self.Write(subscaleName[i])
                        self.Write(B" (kind = \"")
                        self.Write(axisName[i])
                        self.Write(B"\")\n")
                        self.IndentWrite(B"{\n")
                        self.IndentWrite(B"float {", 1)
                        self.WriteFloat(scl)
                        self.Write(B"}")
                        self.IndentWrite(B"}\n", 0, True)

                        structFlag = True

            elif ((math.fabs(scale[0] - 1.0) > kExportEpsilon) or (math.fabs(scale[1] - 1.0) > kExportEpsilon) or (math.fabs(scale[2] - 1.0) > kExportEpsilon)):
                self.IndentWrite(B"Scale\n", 0, structFlag)
                self.IndentWrite(B"{\n")
                self.IndentWrite(B"float[3] {", 1)
                self.WriteVector3D(scale)
                self.Write(B"}")
                self.IndentWrite(B"}\n", 0, True)

                structFlag = True

            # Export the animation tracks.

            self.IndentWrite(B"Animation (begin = ", 0, True)
            self.WriteFloat((action.frame_range[0] - self.beginFrame) * self.frameTime)
            self.Write(B", end = ")
            self.WriteFloat((action.frame_range[1] - self.beginFrame) * self.frameTime)
            self.Write(B")\n")
            self.IndentWrite(B"{\n")
            self.indentLevel += 1

            structFlag = False

            if (positionAnimated):
                for i in range(3):
                    if (posAnimated[i]):
                        self.ExportAnimationTrack(posAnimCurve[i], posAnimKind[i], subtranslationName[i], structFlag)
                        structFlag = True

            if (rotationAnimated):
                for i in range(3):
                    if (rotAnimated[i]):
                        self.ExportAnimationTrack(rotAnimCurve[i], rotAnimKind[i], subrotationName[i], structFlag)
                        structFlag = True

            if (scaleAnimated):
                for i in range(3):
                    if (sclAnimated[i]):
                        self.ExportAnimationTrack(sclAnimCurve[i], sclAnimKind[i], subscaleName[i], structFlag)
                        structFlag = True

            if (deltaPositionAnimated):
                for i in range(3):
                    if (deltaPosAnimated[i]):
                        self.ExportAnimationTrack(deltaPosAnimCurve[i], deltaPosAnimKind[i], deltaSubtranslationName[i], structFlag)
                        structFlag = True

            if (deltaRotationAnimated):
                for i in range(3):
                    if (deltaRotAnimated[i]):
                        self.ExportAnimationTrack(deltaRotAnimCurve[i], deltaRotAnimKind[i], deltaSubrotationName[i], structFlag)
                        structFlag = True

            if (deltaScaleAnimated):
                for i in range(3):
                    if (deltaSclAnimated[i]):
                        self.ExportAnimationTrack(deltaSclAnimCurve[i], deltaSclAnimKind[i], deltaSubscaleName[i], structFlag)
                        structFlag = True

            self.indentLevel -= 1
            self.IndentWrite(B"}\n")


    def ExportBoneTransform(self, armature, bone, scene):

        curveArray = self.CollectBoneAnimation(armature, bone.name)
        animation = (len(curveArray) != 0)

        transform = bone.matrix_local.copy()
        parentBone = bone.parent
        if (parentBone):
            transform = parentBone.matrix_local.inverted() * transform

        poseBone = armature.pose.bones.get(bone.name)
        if (poseBone):
            transform = poseBone.matrix.copy()
            parentPoseBone = poseBone.parent
            if (parentPoseBone):
                transform = parentPoseBone.matrix.inverted() * transform

        self.IndentWrite(B"Transform")

        if (animation):
            self.Write(B" %transform")

        self.IndentWrite(B"{\n", 0, True)
        self.indentLevel += 1

        self.IndentWrite(B"float[16]\n")
        self.IndentWrite(B"{\n")
        self.WriteMatrix(transform)
        self.IndentWrite(B"}\n")

        self.indentLevel -= 1
        self.IndentWrite(B"}\n")

        if ((animation) and (poseBone)):
            self.ExportBoneSampledAnimationTrack(poseBone, scene)


    def ExportMaterialRef(self, material, index):
        if (not material in self.materialArray):
            self.materialArray[material] = {"structName" : bytes("material" + str(len(self.materialArray) + 1), "UTF-8")}

        self.IndentWrite(B"MaterialRef (index = ")
        self.WriteInt(index)
        self.Write(B") {ref {$")
        self.Write(self.materialArray[material]["structName"])
        self.Write(B"}}\n")


    def ExportBone(self, armature, bone, scene):
        nodeRef = self.nodeArray.get(bone)
        if (nodeRef):
            self.IndentWrite(structIdentifier[nodeRef["nodeType"]], 0, True)
            self.Write(nodeRef["structName"])

            self.IndentWrite(B"{\n", 0, True)
            self.indentLevel += 1

            name = bone.name
            if (name != ""):
                self.IndentWrite(B"Name {string {\"")
                self.Write(bytes(name, "UTF-8"))
                self.Write(B"\"}}\n\n")

            self.ExportBoneTransform(armature, bone, scene)

        for subnode in bone.children:
            self.ExportBone(armature, subnode, scene)

        # Export any ordinary nodes that are parented to this bone.

        boneSubnodeArray = self.boneParentArray.get(bone.name)
        if (boneSubnodeArray):
            poseBone = None
            if (not bone.use_relative_parent):
                poseBone = armature.pose.bones.get(bone.name)

            for subnode in boneSubnodeArray:
                self.ExportNode(subnode, scene, poseBone)

        if (nodeRef):
            self.indentLevel -= 1
            self.IndentWrite(B"}\n")


    def ExportNode(self, node, scene, poseBone = None):

        # This function exports a single node in the scene and includes its name,
        # object reference, material references (for geometries), and transform.
        # Subnodes are then exported recursively.

        nodeRef = self.nodeArray.get(node)
        if (nodeRef):
            type = nodeRef["nodeType"]
            self.IndentWrite(structIdentifier[type], 0, True)
            self.Write(nodeRef["structName"])

            if (type == kNodeTypeGeometry):
                if (node.hide_render):
                    self.Write(B" (visible = false)")

            self.IndentWrite(B"{\n", 0, True)
            self.indentLevel += 1

            structFlag = False

            # Export the node's name if it has one.

            name = node.name
            if (name != ""):
                self.IndentWrite(B"Name {string {\"")
                self.Write(bytes(name, "UTF-8"))
                self.Write(B"\"}}\n")
                structFlag = True

            # Export the object reference and material references.

            object = node.data

            if (type == kNodeTypeGeometry):
                if (not object in self.geometryArray):
                    self.geometryArray[object] = {"structName" : bytes("geometry" + str(len(self.geometryArray) + 1), "UTF-8"), "nodeTable" : [node]}
                else:
                    self.geometryArray[object]["nodeTable"].append(node)

                self.IndentWrite(B"ObjectRef {ref {$")
                self.Write(self.geometryArray[object]["structName"])
                self.Write(B"}}\n")

                for i in range(len(node.material_slots)):
                    self.ExportMaterialRef(node.material_slots[i].material, i)

                structFlag = True

            elif (type == kNodeTypeLight):
                type = object.type
                if ((type == "SUN") or (type == "POINT") or (type == "SPOT")):
                    if (not object in self.lightArray):
                        self.lightArray[object] = {"structName" : bytes("light" + str(len(self.lightArray) + 1), "UTF-8"), "nodeTable" : [node]}
                    else:
                        self.lightArray[object]["nodeTable"].append(node)

                    self.IndentWrite(B"ObjectRef {ref {$")
                    self.Write(self.lightArray[object]["structName"])
                    self.Write(B"}}\n")
                    structFlag = True

            elif (type == kNodeTypeCamera):
                if (not object in self.cameraArray):
                    self.cameraArray[object] = {"structName" : bytes("camera" + str(len(self.cameraArray) + 1), "UTF-8"), "nodeTable" : [node]}
                else:
                    self.cameraArray[object]["nodeTable"].append(node)

                self.IndentWrite(B"ObjectRef {ref {$")
                self.Write(self.cameraArray[object]["structName"])
                self.Write(B"}}\n")
                structFlag = True

            if (structFlag):
                self.Write(B"\n")

            if (poseBone):

                # If the node is parented to a bone and is not relative, then undo the bone's transform.

                self.IndentWrite(B"Transform\n")
                self.IndentWrite(B"{\n")
                self.indentLevel += 1

                self.IndentWrite(B"float[16]\n")
                self.IndentWrite(B"{\n")
                self.WriteMatrix(poseBone.matrix.inverted())
                self.IndentWrite(B"}\n")

                self.indentLevel -= 1
                self.IndentWrite(B"}\n")

            # Export the transform. If the node is animated, then animation tracks are exported here.

            self.ExportNodeTransform(node, scene)

            if (node.type == "ARMATURE"):
                skeleton = node.data
                if (skeleton):
                    for bone in skeleton.bones:
                        if (bone.parent == None):
                            self.ExportBone(node, bone, scene)

        for subnode in node.children:
            if (subnode.parent_type != "BONE"):
                self.ExportNode(subnode, scene)

        if (nodeRef):
            self.indentLevel -= 1
            self.IndentWrite(B"}\n")


    def ExportSkin(self, node, armature, exportVertexArray):

        # This function exports all skinning data, which includes the skeleton
        # and per-vertex bone influence data.

        self.IndentWrite(B"Skin\n", 0, True)
        self.IndentWrite(B"{\n")
        self.indentLevel += 1

        # Write the skin bind pose transform.

        self.IndentWrite(B"Transform\n")
        self.IndentWrite(B"{\n")
        self.indentLevel += 1

        self.IndentWrite(B"float[16]\n")
        self.IndentWrite(B"{\n")
        self.WriteMatrix(node.matrix_world)
        self.IndentWrite(B"}\n")

        self.indentLevel -= 1
        self.IndentWrite(B"}\n\n")

        # Export the skeleton, which includes an array of bone node references
        # and and array of per-bone bind pose transforms.

        self.IndentWrite(B"Skeleton\n")
        self.IndentWrite(B"{\n")
        self.indentLevel += 1

        # Write the bone node reference array.

        self.IndentWrite(B"BoneRefArray\n")
        self.IndentWrite(B"{\n")
        self.indentLevel += 1

        boneArray = armature.data.bones
        boneCount = len(boneArray)

        self.IndentWrite(B"ref\t\t\t// ")
        self.WriteInt(boneCount)
        self.IndentWrite(B"{\n", 0, True)
        self.IndentWrite(B"", 1)

        for i in range(boneCount):
            boneRef = self.FindNode(boneArray[i].name)
            if (boneRef):
                self.Write(B"$")
                self.Write(boneRef[1]["structName"])
            else:
                self.Write(B"null")

            if (i < boneCount - 1):
                self.Write(B", ")
            else:
                self.Write(B"\n")

        self.IndentWrite(B"}\n")

        self.indentLevel -= 1
        self.IndentWrite(B"}\n\n")

        # Write the bind pose transform array.

        self.IndentWrite(B"Transform\n")
        self.IndentWrite(B"{\n")
        self.indentLevel += 1

        self.IndentWrite(B"float[16]\t// ")
        self.WriteInt(boneCount)
        self.IndentWrite(B"{\n", 0, True)

        for i in range(boneCount):
            self.WriteMatrixFlat(armature.matrix_world * boneArray[i].matrix_local)
            if (i < boneCount - 1):
                self.Write(B",\n")

        self.IndentWrite(B"}\n", 0, True)

        self.indentLevel -= 1
        self.IndentWrite(B"}\n")

        self.indentLevel -= 1
        self.IndentWrite(B"}\n\n")

        # Export the per-vertex bone influence data.

        groupRemap = []

        for group in node.vertex_groups:
            groupName = group.name
            for i in range(boneCount):
                if (boneArray[i].name == groupName):
                    groupRemap.append(i)
                    break
            else:
                groupRemap.append(-1)

        boneCountArray = []
        boneIndexArray = []
        boneWeightArray = []

        meshVertexArray = node.data.vertices
        for ev in exportVertexArray:
            boneCount = 0
            totalWeight = 0.0
            for element in meshVertexArray[ev.index].groups:
                boneIndex = groupRemap[element.group]
                boneWeight = element.weight
                if ((boneIndex >= 0) and (boneWeight != 0.0)):
                    boneCount += 1
                    totalWeight += boneWeight
                    boneIndexArray.append(boneIndex)
                    boneWeightArray.append(boneWeight)
            boneCountArray.append(boneCount)

            if (totalWeight != 0.0):
                normalizer = 1.0 / totalWeight
                for i in range(-boneCount, 0):
                    boneWeightArray[i] *= normalizer

        # Write the bone count array. There is one entry per vertex.

        self.IndentWrite(B"BoneCountArray\n")
        self.IndentWrite(B"{\n")
        self.indentLevel += 1

        self.IndentWrite(B"unsigned_int16\t\t// ")
        self.WriteInt(len(boneCountArray))
        self.IndentWrite(B"{\n", 0, True)
        self.WriteIntArray(boneCountArray)
        self.IndentWrite(B"}\n")

        self.indentLevel -= 1
        self.IndentWrite(B"}\n\n")

        # Write the bone index array. The number of entries is the sum of the bone counts for all vertices.

        self.IndentWrite(B"BoneIndexArray\n")
        self.IndentWrite(B"{\n")
        self.indentLevel += 1

        self.IndentWrite(B"unsigned_int16\t\t// ")
        self.WriteInt(len(boneIndexArray))
        self.IndentWrite(B"{\n", 0, True)
        self.WriteIntArray(boneIndexArray)
        self.IndentWrite(B"}\n")

        self.indentLevel -= 1
        self.IndentWrite(B"}\n\n")

        # Write the bone weight array. The number of entries is the sum of the bone counts for all vertices.

        self.IndentWrite(B"BoneWeightArray\n")
        self.IndentWrite(B"{\n")
        self.indentLevel += 1

        self.IndentWrite(B"float\t\t// ")
        self.WriteInt(len(boneWeightArray))
        self.IndentWrite(B"{\n", 0, True)
        self.WriteFloatArray(boneWeightArray)
        self.IndentWrite(B"}\n")

        self.indentLevel -= 1
        self.IndentWrite(B"}\n")

        self.indentLevel -= 1
        self.IndentWrite(B"}\n")


    def ExportGeometry(self, objectRef, scene):

        # This function exports a single geometry object.

        self.Write(B"\nGeometryObject $")
        self.Write(objectRef[1]["structName"])
        self.WriteNodeTable(objectRef)

        self.Write(B"\n{\n")
        self.indentLevel += 1

        self.IndentWrite(B"Mesh (primitive = \"triangles\")\n")
        self.IndentWrite(B"{\n")
        self.indentLevel += 1

        node = objectRef[1]["nodeTable"][0]
        mesh = None

        armature = node.find_armature()
        if (armature):

            # Get the mesh containing the vertex positions before they are deformed
            # by the armature modifier. We need this in order to export the proper bind pose.

            # This does also ignore modifiers that precede the armature modifier, but the
            # Blender API does not provide a reasonable way to retrieve the mesh at an arbitrary
            # stage in the modifier stack.

            mesh = objectRef[0]
            mesh.update(False, True)
        else:

            # Apply all modifiers to create a new mesh.

            mesh = node.to_mesh(scene, True, "RENDER", True, False)

        materialTable = []
        exportVertexArray = OpenGexExporter.DeindexMesh(mesh, materialTable)
        triangleCount = len(materialTable)

        indexTable = []
        unifiedVertexArray = OpenGexExporter.UnifyVertices(exportVertexArray, indexTable)
        vertexCount = len(unifiedVertexArray)

        # Write the position array.

        self.IndentWrite(B"VertexArray (attrib = \"position\")\n")
        self.IndentWrite(B"{\n")
        self.indentLevel += 1

        self.IndentWrite(B"float[3]\t\t// ")
        self.WriteInt(vertexCount)
        self.IndentWrite(B"{\n", 0, True)
        self.WriteVertexArray3D(unifiedVertexArray, "position")
        self.IndentWrite(B"}\n")

        self.indentLevel -= 1
        self.IndentWrite(B"}\n\n")

        # Write the normal array.

        self.IndentWrite(B"VertexArray (attrib = \"normal\")\n")
        self.IndentWrite(B"{\n")
        self.indentLevel += 1

        self.IndentWrite(B"float[3]\t\t// ")
        self.WriteInt(vertexCount)
        self.IndentWrite(B"{\n", 0, True)
        self.WriteVertexArray3D(unifiedVertexArray, "normal")
        self.IndentWrite(B"}\n")

        self.indentLevel -= 1
        self.IndentWrite(B"}\n")

        # Write the color array if it exists.

        colorCount = len(mesh.tessface_vertex_colors)
        if (colorCount > 0):
            self.IndentWrite(B"VertexArray (attrib = \"color\")\n", 0, True)
            self.IndentWrite(B"{\n")
            self.indentLevel += 1

            self.IndentWrite(B"float[3]\t\t// ")
            self.WriteInt(vertexCount)
            self.IndentWrite(B"{\n", 0, True)
            self.WriteVertexArray3D(unifiedVertexArray, "color")
            self.IndentWrite(B"}\n")

            self.indentLevel -= 1
            self.IndentWrite(B"}\n")

        # Write the texcoord arrays.

        texcoordCount = len(mesh.tessface_uv_textures)
        if (texcoordCount > 0):
            self.IndentWrite(B"VertexArray (attrib = \"texcoord\")\n", 0, True)
            self.IndentWrite(B"{\n")
            self.indentLevel += 1

            self.IndentWrite(B"float[2]\t\t// ")
            self.WriteInt(vertexCount)
            self.IndentWrite(B"{\n", 0, True)
            self.WriteVertexArray2D(unifiedVertexArray, "texcoord0")
            self.IndentWrite(B"}\n")

            self.indentLevel -= 1
            self.IndentWrite(B"}\n")

            if (texcoordCount > 1):
                self.IndentWrite(B"VertexArray (attrib = \"texcoord[1]\")\n", 0, True)
                self.IndentWrite(B"{\n")
                self.indentLevel += 1

                self.IndentWrite(B"float[2]\t\t// ")
                self.WriteInt(vertexCount)
                self.IndentWrite(B"{\n", 0, True)
                self.WriteVertexArray2D(unifiedVertexArray, "texcoord1")
                self.IndentWrite(B"}\n")

                self.indentLevel -= 1
                self.IndentWrite(B"}\n")

        # Write the index arrays.

        maxMaterialIndex = 0
        for i in range(len(materialTable)):
            index = materialTable[i]
            if (index > maxMaterialIndex):
                maxMaterialIndex = index

        if (maxMaterialIndex == 0):

            # There is only one material, so write a single index array.

            self.IndentWrite(B"IndexArray\n", 0, True)
            self.IndentWrite(B"{\n")
            self.indentLevel += 1

            self.IndentWrite(B"unsigned_int32[3]\t\t// ")
            self.WriteInt(triangleCount)
            self.IndentWrite(B"{\n", 0, True)
            self.WriteTriangleArray(triangleCount, indexTable)
            self.IndentWrite(B"}\n")

            self.indentLevel -= 1
            self.IndentWrite(B"}\n")

        else:

            # If there are multiple material indexes, then write a separate index array for each one.

            materialTriangleCount = [0 for i in range(maxMaterialIndex + 1)]
            for i in range(len(materialTable)):
                materialTriangleCount[materialTable[i]] += 1

            for m in range(maxMaterialIndex + 1):
                if (materialTriangleCount[m] != 0):
                    materialIndexTable = []
                    for i in range(len(materialTable)):
                        if (materialTable[i] == m):
                            k = i * 3
                            materialIndexTable.append(indexTable[k])
                            materialIndexTable.append(indexTable[k + 1])
                            materialIndexTable.append(indexTable[k + 2])

                    self.IndentWrite(B"IndexArray (material = ", 0, True)
                    self.WriteInt(m)
                    self.Write(B")\n")
                    self.IndentWrite(B"{\n")
                    self.indentLevel += 1

                    self.IndentWrite(B"unsigned_int32[3]\t\t// ")
                    self.WriteInt(materialTriangleCount[m])
                    self.IndentWrite(B"{\n", 0, True)
                    self.WriteTriangleArray(materialTriangleCount[m], materialIndexTable)
                    self.IndentWrite(B"}\n")

                    self.indentLevel -= 1
                    self.IndentWrite(B"}\n")

        # If the mesh is skinned, export the skinning data here.

        if (armature):
            self.ExportSkin(node, armature, unifiedVertexArray)
        else:
            bpy.data.meshes.remove(mesh)

        self.indentLevel -= 1
        self.IndentWrite(B"}\n")

        self.indentLevel -= 1
        self.Write(B"}\n")


    def ExportLight(self, objectRef):

        # This function exports a single light object.

        self.Write(B"\nLightObject $")
        self.Write(objectRef[1]["structName"])

        object = objectRef[0]
        type = object.type

        self.Write(B" (type = ")
        pointFlag = False
        spotFlag = False

        if (type == "SUN"):
            self.Write(B"\"infinite\"")
        elif (type == "POINT"):
            self.Write(B"\"point\"")
            pointFlag = True
        else:
            self.Write(B"\"spot\"")
            pointFlag = True
            spotFlag = True

        if (not object.use_shadow):
            self.Write(B", shadow = false")

        self.Write(B")")
        self.WriteNodeTable(objectRef)

        self.Write(B"\n{\n")
        self.indentLevel += 1

        # Export the light's color, and include a separate intensity if necessary.

        self.IndentWrite(B"Color (attrib = \"light\") {float[3] {")
        self.WriteColor(object.color)
        self.Write(B"}}\n")

        intensity = object.energy
        if (intensity != 1.0):
            self.IndentWrite(B"Param (attrib = \"intensity\") {float {")
            self.WriteFloat(intensity)
            self.Write(B"}}\n")

        if (pointFlag):

            # Export a separate attenuation function for each type that's in use.

            falloff = object.falloff_type

            if (falloff == "INVERSE_LINEAR"):
                self.IndentWrite(B"Atten (curve = \"inverse\")\n", 0, True)
                self.IndentWrite(B"{\n")

                self.IndentWrite(B"Param (attrib = \"scale\") {float {", 1)
                self.WriteFloat(object.distance)
                self.Write(B"}}\n")

                self.IndentWrite(B"}\n")

            elif (falloff == "INVERSE_SQUARE"):
                self.IndentWrite(B"Atten (curve = \"inverse_square\")\n", 0, True)
                self.IndentWrite(B"{\n")

                self.IndentWrite(B"Param (attrib = \"scale\") {float {", 1)
                self.WriteFloat(math.sqrt(object.distance))
                self.Write(B"}}\n")

                self.IndentWrite(B"}\n")

            elif (falloff == "LINEAR_QUADRATIC_WEIGHTED"):
                if (object.linear_attenuation != 0.0):
                    self.IndentWrite(B"Atten (curve = \"inverse\")\n", 0, True)
                    self.IndentWrite(B"{\n")

                    self.IndentWrite(B"Param (attrib = \"scale\") {float {", 1)
                    self.WriteFloat(object.distance)
                    self.Write(B"}}\n")

                    self.IndentWrite(B"Param (attrib = \"constant\") {float {", 1)
                    self.WriteFloat(1.0)
                    self.Write(B"}}\n")

                    self.IndentWrite(B"Param (attrib = \"linear\") {float {", 1)
                    self.WriteFloat(object.linear_attenuation)
                    self.Write(B"}}\n")

                    self.IndentWrite(B"}\n\n")

                if (object.quadratic_attenuation != 0.0):
                    self.IndentWrite(B"Atten (curve = \"inverse_square\")\n")
                    self.IndentWrite(B"{\n")

                    self.IndentWrite(B"Param (attrib = \"scale\") {float {", 1)
                    self.WriteFloat(object.distance)
                    self.Write(B"}}\n")

                    self.IndentWrite(B"Param (attrib = \"constant\") {float {", 1)
                    self.WriteFloat(1.0)
                    self.Write(B"}}\n")

                    self.IndentWrite(B"Param (attrib = \"quadratic\") {float {", 1)
                    self.WriteFloat(object.quadratic_attenuation)
                    self.Write(B"}}\n")

                    self.IndentWrite(B"}\n")

            if (object.use_sphere):
                self.IndentWrite(B"Atten (curve = \"linear\")\n", 0, True)
                self.IndentWrite(B"{\n")

                self.IndentWrite(B"Param (attrib = \"end\") {float {", 1)
                self.WriteFloat(object.distance)
                self.Write(B"}}\n")

                self.IndentWrite(B"}\n")

            if (spotFlag):

                # Export additional angular attenuation for spot lights.

                self.IndentWrite(B"Atten (kind = \"angle\", curve = \"linear\")\n", 0, True)
                self.IndentWrite(B"{\n")

                endAngle = object.spot_size * 0.5
                beginAngle = endAngle * (1.0 - object.spot_blend)

                self.IndentWrite(B"Param (attrib = \"begin\") {float {", 1)
                self.WriteFloat(beginAngle)
                self.Write(B"}}\n")

                self.IndentWrite(B"Param (attrib = \"end\") {float {", 1)
                self.WriteFloat(endAngle)
                self.Write(B"}}\n")

                self.IndentWrite(B"}\n")

        self.indentLevel -= 1
        self.Write(B"}\n")


    def ExportCamera(self, objectRef):

        # This function exports a single camera object.

        self.Write(B"\nCameraObject $")
        self.Write(objectRef[1]["structName"])
        self.WriteNodeTable(objectRef)

        self.Write(B"\n{\n")
        self.indentLevel += 1

        object = objectRef[0]

        self.IndentWrite(B"Param (attrib = \"fov\") {float {")
        self.WriteFloat(object.angle_x)
        self.Write(B"}}\n")

        self.IndentWrite(B"Param (attrib = \"near\") {float {")
        self.WriteFloat(object.clip_start)
        self.Write(B"}}\n")

        self.IndentWrite(B"Param (attrib = \"far\") {float {")
        self.WriteFloat(object.clip_end)
        self.Write(B"}}\n")

        self.indentLevel -= 1
        self.Write(B"}\n")


    def ExportObjects(self, scene):
        for objectRef in self.geometryArray.items():
            self.ExportGeometry(objectRef, scene)
        for objectRef in self.lightArray.items():
            self.ExportLight(objectRef)
        for objectRef in self.cameraArray.items():
            self.ExportCamera(objectRef)


    def ExportTexture(self, textureSlot, attrib):

        # This function exports a single texture from a material.

        self.IndentWrite(B"Texture (attrib = \"", 0, True)
        self.Write(attrib)
        self.Write(B"\")\n")

        self.IndentWrite(B"{\n")
        self.indentLevel += 1

        self.IndentWrite(B"string {\"")
        self.WriteFileName(textureSlot.texture.image.filepath)
        self.Write(B"\"}\n")

        # If the texture has a scale and/or offset, then export a coordinate transform.

        uscale = textureSlot.scale[0]
        vscale = textureSlot.scale[1]
        uoffset = textureSlot.offset[0]
        voffset = textureSlot.offset[1]

        if ((uscale != 1.0) or (vscale != 1.0) or (uoffset != 0.0) or (voffset != 0.0)):
            matrix = [[uscale, 0.0, 0.0, 0.0], [0.0, vscale, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [uoffset, voffset, 0.0, 1.0]]

            self.IndentWrite(B"Transform\n", 0, True)
            self.IndentWrite(B"{\n")
            self.indentLevel += 1

            self.IndentWrite(B"float[16]\n")
            self.IndentWrite(B"{\n")
            self.WriteMatrix(matrix)
            self.IndentWrite(B"}\n")

            self.indentLevel -= 1
            self.IndentWrite(B"}\n")

        self.indentLevel -= 1
        self.IndentWrite(B"}\n")


    def ExportMaterials(self):

        # This function exports all of the materials used in the scene.

        for materialRef in self.materialArray.items():
            material = materialRef[0]

            self.Write(B"\nMaterial $")
            self.Write(materialRef[1]["structName"])
            self.Write(B"\n{\n")
            self.indentLevel += 1

            self.IndentWrite(B"Name {string {\"")
            self.Write(bytes(material.name, "UTF-8"))
            self.Write(B"\"}}\n\n")

            intensity = material.diffuse_intensity
            diffuse = [material.diffuse_color[0] * intensity, material.diffuse_color[1] * intensity, material.diffuse_color[2] * intensity]

            self.IndentWrite(B"Color (attrib = \"diffuse\") {float[3] {")
            self.WriteColor(diffuse)
            self.Write(B"}}\n")

            intensity = material.specular_intensity
            specular = [material.specular_color[0] * intensity, material.specular_color[1] * intensity, material.specular_color[2] * intensity]

            if ((specular[0] > 0.0) or (specular[1] > 0.0) or (specular[2] > 0.0)):
                self.IndentWrite(B"Color (attrib = \"specular\") {float[3] {")
                self.WriteColor(specular)
                self.Write(B"}}\n")

                self.IndentWrite(B"Param (attrib = \"specular_power\") {float {")
                self.WriteFloat(material.specular_hardness)
                self.Write(B"}}\n")

            emission = material.emit
            if (emission > 0.0):
                self.IndentWrite(B"Color (attrib = \"emission\") {float[3] {")
                self.WriteColor([emission, emission, emission])
                self.Write(B"}}\n")

            diffuseTexture = None
            specularTexture = None
            emissionTexture = None
            transparencyTexture = None
            normalTexture = None

            for textureSlot in material.texture_slots:
                if ((textureSlot) and (textureSlot.use) and (textureSlot.texture.type == "IMAGE")):
                    if (((textureSlot.use_map_color_diffuse) or (textureSlot.use_map_diffuse)) and (diffuseTexture == None)):
                        diffuseTexture = textureSlot
                    elif (((textureSlot.use_map_color_spec) or (textureSlot.use_map_specular)) and (specularTexture == None)):
                        specularTexture = textureSlot
                    elif ((textureSlot.use_map_emit) and (emissionTexture == None)):
                        emissionTexture = textureSlot
                    elif ((textureSlot.use_map_translucency) and (transparencyTexture == None)):
                        transparencyTexture = textureSlot
                    elif ((textureSlot.use_map_normal) and (normalTexture == None)):
                        normalTexture = textureSlot

            if (diffuseTexture):
                self.ExportTexture(diffuseTexture, B"diffuse")
            if (specularTexture):
                self.ExportTexture(specularTexture, B"specular")
            if (emissionTexture):
                self.ExportTexture(emissionTexture, B"emission")
            if (transparencyTexture):
                self.ExportTexture(transparencyTexture, B"transparency")
            if (normalTexture):
                self.ExportTexture(normalTexture, B"normal")

            self.indentLevel -= 1
            self.Write(B"}\n")


    def ExportMetrics(self, scene):
        scale = scene.unit_settings.scale_length

        if (scene.unit_settings.system == "IMPERIAL"):
            scale *= 0.3048

        self.Write(B"Metric (key = \"distance\") {float {")
        self.WriteFloat(scale)
        self.Write(B"}}\n")

        self.Write(B"Metric (key = \"angle\") {float {1.0}}\n")
        self.Write(B"Metric (key = \"time\") {float {1.0}}\n")
        self.Write(B"Metric (key = \"up\") {string {\"z\"}}\n")


    @classmethod
    def poll(cls, context):
        return (context.active_object is not None)

# import sys
# ogex = sys.modules['OpenGex-Blender']


# class MemoryOpenGexExporter(ogex.OpenGexExporter):
class MemoryOpenGexExporter(OpenGexExporterBase):

    def __init__(self):
        super()
        self.file = None

    def exportToBytes(self, context):
        self.file = MemoryFile()

        self.indentLevel = 0

        scene = context.scene
        self.ExportMetrics(scene)

        originalFrame = scene.frame_current
        originalSubframe = scene.frame_subframe
        self.restoreFrame = False

        self.beginFrame = scene.frame_start
        self.endFrame = scene.frame_end
        self.frameTime = 1.0 / (scene.render.fps_base * scene.render.fps)

        self.nodeArray = {}
        self.geometryArray = {}
        self.lightArray = {}
        self.cameraArray = {}
        self.materialArray = {}
        self.boneParentArray = {}

        exportAllFlag = True # not self.option_export_selection

        for object in scene.objects:
            if (object.parent == None):
                self.ProcessNode(object, exportAllFlag)

        for object in scene.objects:
            if (object.parent == None):
                self.ExportNode(object, scene)

        self.ExportObjects(scene)
        self.ExportMaterials()

        if (self.restoreFrame):
            scene.frame_set(originalFrame, originalSubframe)

        self.file.close()
        return self.file.data


class MemoryFile:

    def __init__(self):
        self.data = bytearray()

    def close(self):
        pass

    def write(self, data):
        self.data.extend(data)



def register():
    # Register the RenderEngine
    bpy.utils.register_class(ExternalRenderEngine)

    # RenderEngines also need to tell UI Panels that they are compatible
    # Otherwise most of the UI will be empty when the engine is selected.
    # In this example, we need to see the main render image button and
    # the material preview panel.
    from bl_ui import properties_render
    properties_render.RENDER_PT_render.COMPAT_ENGINES.add(RE_NAME)
    del properties_render

    from bl_ui import properties_material
    properties_material.MATERIAL_PT_preview.COMPAT_ENGINES.add(RE_NAME)
    del properties_material


def unregister():
    gloop.close()
    bpy.utils.unregister_class(ExternalRenderEngine)


# This allows you to run the script directly from blenders text editor
# to test the addon without having to install it.
if __name__ == "__main__":
    register()
