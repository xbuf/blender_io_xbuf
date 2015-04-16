# Script to help edit the addon in an external editor
# based on http://www.blender.org/api/blender_python_api_2_72_release/info_tips_and_tricks.html
# copy the script into a blender python script text
# run the script to reload the addon from filesystem

import sys
# import os
# import bpy

# module_dir = os.path.dirname(bpy.data.filepath)
module_dir = "/home/dwayne/work/oss/blender_io_xbuf"
if module_dir not in sys.path:
    sys.path.append(module_dir)
module_dir = "/home/dwayne/work/oss/blender_io_xbuf/modules"
if module_dir not in sys.path:
    sys.path.append(module_dir)

import blender_io_xbuf
import xbuf.datas_pb2
import xbuf.cmds_pb2
import xbuf_ext.custom_params_pb2
import xbuf_ext.animations_kf_pb2

# unregister previously code
try:
    blender_io_xbuf.unregister()
except (RuntimeError):
    pass

# register with new code
import imp

imp.reload(xbuf.datas_pb2)
imp.reload(xbuf.cmds_pb2)
imp.reload(xbuf_ext.custom_params_pb2)
imp.reload(xbuf_ext.animations_kf_pb2)

imp.reload(blender_io_xbuf)
imp.reload(blender_io_xbuf.helpers)
imp.reload(blender_io_xbuf.xbuf_export)
imp.reload(blender_io_xbuf.protocol)
imp.reload(blender_io_xbuf.renderengine)
blender_io_xbuf.register()
