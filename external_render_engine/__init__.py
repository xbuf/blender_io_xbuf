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

import renderengine

bl_info = {
    "name": "external_render_engine",
    "author": "David Bernard",
    "version": (0, 1),
    "blender": (2, 72, 0),
    # "location": "View3D > Add > Mesh > New Object",
    "description": "Delegate rendering to an external render engine (eg provide by game engine)",
    "warning": "",
    "wiki_url": "",
    "category": "Add RenderEngine"}

__all__ = ['ExternalRenderEngine']


def register():

    import bpy
    # Register the RenderEngine
    bpy.utils.register_class(renderengine.ExternalRenderEngine)

    # RenderEngines also need to tell UI Panels that they are compatible
    # Otherwise most of the UI will be empty when the engine is selected.
    # In this example, we need to see the main render image button and
    # the material preview panel.
    from bl_ui import properties_render
    properties_render.RENDER_PT_render.COMPAT_ENGINES.add(renderengine.ExternalRenderEngine.bl_idname)
    del properties_render

    from bl_ui import properties_material
    properties_material.MATERIAL_PT_preview.COMPAT_ENGINES.add(renderengine.ExternalRenderEngine.bl_idname)
    del properties_material


def unregister():
    import bpy
    bpy.utils.unregister_class(renderengine.ExternalRenderEngine)


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
