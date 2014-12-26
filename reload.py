# Script to help edit the addon in an external editor
# based on http://www.blender.org/api/blender_python_api_2_72_release/info_tips_and_tricks.html
# copy the script into a blender python script text
# run the script to reload the addon from filesystem

import sys
# import os
# import bpy

# module_dir = os.path.dirname(bpy.data.filepath)
module_dir = "/home/dwayne/work/oss/blender_external_renderer"
if module_dir not in sys.path:
    sys.path.append(module_dir)
module_dir = "/home/dwayne/work/oss/blender_external_renderer/modules"
if module_dir not in sys.path:
    sys.path.append(module_dir)

import external_render_engine
import pgex.datas_pb2
import pgex.cmds_pb2

# unregister previously code
try:
    external_render_engine.unregister()
except (RuntimeError):
    pass

# register with new code
import imp

imp.reload(pgex.datas_pb2)
imp.reload(pgex.cmds_pb2)

imp.reload(external_render_engine)
imp.reload(external_render_engine.protocol)
imp.reload(external_render_engine.renderengine)
external_render_engine.register()
