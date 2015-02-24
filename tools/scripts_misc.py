import bpy
from bpy import data as D
from bpy import context as C
from mathutils import *
from math import *


# mute all constraint
obj = D.objects[0]
for bone in obj.pose.bones:
    for con in bone.constraints:
        con.mute = True
