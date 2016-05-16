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


bl_info = {
    "name": "Xbuf Exporter & Render Engine",
    "author": "David Bernard",
    "version": (0, 7),
    "blender": (2, 73, 0),
    # "location": "Render > Engine > Xbuf Render",
    "description": "Xbuf exporter and renderer (via an external xbuf compatible render engine (eg provided by game engine))",
    "warning": "This script is Alpha",
    "wiki_url": "https://github.com/xbuf/blender_io_xbuf",
    "tracker_url": "https://github.com/xbuf/blender_io_xbuf/issues",
    "category": "Import-Export"}

import sys
import os
# Python dependencies are bundled inside the xxxxx/../modules folder
_modules_path = os.path.join(os.path.dirname(__file__), "modules")
if _modules_path not in sys.path:
    sys.path.append(_modules_path)
del _modules_path

# Use F8 to reload (see http://wiki.blender.org/index.php/Dev:2.5/Py/Scripts/Cookbook/Code_snippets/Multi-File_packages)
from . import renderengine
from . import protocol
from . import xbuf_export
from . import helpers

"""If the module is reloaded, reload all submodules as well
   This will reload all modules at the initial import as well but
   that should not be a problem
"""
import imp
import types
locals_copy = dict(locals())
for var in locals_copy:
    tmp = locals_copy[var]
    if isinstance(tmp, types.ModuleType) and tmp.__package__ == __name__:
        # print("Reloading: %s" % (var))
        imp.reload(tmp)

import bpy


# TODO default the value from plugin preferences
class RenderSettingsScene(bpy.types.PropertyGroup):

    port = bpy.props.IntProperty(
        name="port",
        description="network port of the external renderer",
        default=4242, min=1024)
    host = bpy.props.StringProperty(
        name="host",
        description="hostname or ip of the external renderer",
        default="127.0.0.1")
    auto_redraw = bpy.props.BoolProperty(
        name="auto_redraw",
        description="continously request external to renderer, usefull if update on external side, like playing animation but require more resource",
        default=False)

    def __init__(self):
        pass


# TODO default the value from plugin preferences
class xbufSettingsScene(bpy.types.PropertyGroup):
    import os

    # TODO use user_cache_dir like in https://pypi.python.org/pypi/appdirs
    assets_path = bpy.props.StringProperty(
        name="assets root folder path",
        description="Full path to directory where the assets are saved",
        default=os.path.abspath(os.path.expanduser("~/assets")),
        maxlen=1024, subtype="DIR_PATH")

    def __init__(self):
        pass


class ExternalRenderPanel(bpy.types.Panel):
    bl_idname = "RENDER_PT_external_render"
    bl_label = "Xbuf Render Config"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"
    bl_options = {'DEFAULT_CLOSED'}
    COMPAT_ENGINES = {renderengine.ExternalRenderEngine.bl_idname}

    def __init__(self):
        pass

    @classmethod
    def poll(cls, context):
        engine = context.scene.render.engine
        return engine in cls.COMPAT_ENGINES

    def draw(self, context):
        layout = self.layout
        render = context.scene.external_render
        xbuf = context.scene.xbuf
        row = layout.row()
        row.prop(render, "host")
        row.prop(render, "port")
        row = layout.row()
        row.prop(render, "auto_redraw")
        col = layout.column()
        col.prop(xbuf, "assets_path")
        # layout.label(text="Hello World")


def register_settings():
    bpy.utils.register_class(RenderSettingsScene)
    bpy.types.Scene.external_render = bpy.props.PointerProperty(type=RenderSettingsScene)
    bpy.utils.register_class(xbufSettingsScene)
    bpy.types.Scene.xbuf = bpy.props.PointerProperty(type=xbufSettingsScene)
    bpy.utils.register_class(ExternalRenderPanel)


def unregister_settings():
    bpy.utils.unregister_class(ExternalRenderPanel)
    # del bpy.types.Scene.xbuf
    bpy.utils.unregister_class(xbufSettingsScene)
    # del bpy.types.Scene.external_renderer
    bpy.utils.unregister_class(RenderSettingsScene)


def register_renderer():

    # Register the RenderEngine
    bpy.utils.register_class(renderengine.ExternalRenderEngine)

    # RenderEngines also need to tell UI Panels that they are compatible
    # Otherwise most of the UI will be empty when the engine is selected.
    # In this example, we need to see the main render image button and
    # the material preview panel.
    import bl_ui
    panels = [
        bl_ui.properties_render.RENDER_PT_render,
        # # bl_ui.properties_material.MATERIAL_PT_preview,
        # bl_ui.properties_material.MATERIAL_PT_context_material,
        # bl_ui.properties_material.MATERIAL_PT_diffuse,
        # bl_ui.properties_material.MATERIAL_PT_specular,
        # bl_ui.properties_material.MATERIAL_PT_shadow,
        # bl_ui.properties_material.MATERIAL_PT_shading,
        # bl_ui.properties_material.MATERIAL_PT_custom_props,
        # bl_ui.properties_data_lamp.DATA_PT_lamp,
        # bl_ui.properties_data_lamp.DATA_PT_spot,
        # bl_ui.properties_data_lamp.DATA_PT_custom_props_lamp,
    ]
    # register in every properties'panels already compatible with BLENDER_RENDER (except render)
    for k1 in dir(bl_ui):
        if k1.startswith('properties_') and k1 not in ['properties_render', 'properties_freestyle']:
            v1 = getattr(bl_ui, k1)
            for k2 in dir(v1):
                if k2.find('_PT_') > 0:
                    v2 = getattr(v1, k2)
                    if hasattr(v2, 'COMPAT_ENGINES') and 'BLENDER_RENDER' in getattr(v2, 'COMPAT_ENGINES'):
                        panels.append(v2)

    for p in panels:
        p.COMPAT_ENGINES.add(renderengine.ExternalRenderEngine.bl_idname)


def unregister_renderer():
    bpy.utils.unregister_class(renderengine.ExternalRenderEngine)


def menu_func_exporter(self, context):
    self.layout.operator(xbuf_export.xbufExporter.bl_idname, text="xbuf (.xbuf)")


def register_exporter():
    bpy.utils.register_class(xbuf_export.xbufExporter)
    bpy.types.INFO_MT_file_export.append(menu_func_exporter)


def unregister_exporter():
    bpy.types.INFO_MT_file_export.remove(menu_func_exporter)
    bpy.utils.unregister_class(xbuf_export.xbufExporter)


def register():
    register_settings()
    register_exporter()
    register_renderer()


def unregister():
    unregister_renderer()
    unregister_exporter()
    unregister_settings()


def main():
    try:
        unregister()
    except (RuntimeError, ValueError):
        pass
    register()


# This allows you to run the script directly from blenders text editor
# to test the addon without having to install it.
if __name__ == "__main__":
    main()
