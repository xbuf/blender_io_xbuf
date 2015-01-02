# Main

## Overview

- ~~java: logger server (netty)~~
- ~~python: client send message (asyncore)~~
- ~~java: send generated image on (render x,y,w,h)~~
- ~~python: request update image~~
- ~~java: wrap server into appstate~~
- ~~java: send image from current jme display~~
- ~~test: resize~~
- ~~python: integrate into blender~~
- ~~python: display image send from server~~
- python: send camera update
- ~~server: drive camera from python~~
- ~~blender: try to send data in ddl (opengex)~~
- server: ignore (log) unimplemented message
- doc: write protocol
- blender: display error
- blender: display in render view, animation, preview, viewport (interactive)
- ~~server: add/remove/update geometries~~
- ~~blender: update/add/remove geometries~~
- server: add/remove/update custom properties
- blender: update/add/remove custom properties
- ~~server: transform object (location, rotation, scale)~~
- ~~blender:  transform object (location, rotation, scale)~~
- server: add/remove/update geometry placeholder
- blender: update/add/remove geometry placeholder
- server: add/remove/update lights
- ~~blender: update/add/remove lights~~
- ~~server: add/remove/update materials~~
- ~~blender: update/add/remove materials~~
- ~~server: add/remove/update link (material /geometries)~~
- ~~blender: update/add/remove link (material /geometries)~~
- server gui: enable/disable some remote control (camera,...)
- doc: update
- demo: scenario, screenshot, video

## TODO

- custom properties
- only send update not the full scene
- only send update on change
- take care of blender metrics (define in world)
- add a [panel](http://www.blender.org/api/blender_python_api_2_72_release/bpy.types.Panel.html) in blender's render properties to define properties : host, port, assets_folders
- add support of texture via [pathlib](https://docs.python.org/3.4/library/pathlib.html#module-pathlib) + AssetFolder
- provide an exporter for pgex
- support for proxy, linked object
- made a full pipeline demo from blender to jme
- add custom property group dedicated [example] (http://blender.stackexchange.com/questions/6984/color-as-custom-property)

# Protocol options

- metrics (size / time / cpu)
- enable/disable (protocol negotiation ?)
- compression (gzip)
- image via compression
- image via video codec
- image via shared memory
- image via shared file memory mapped
  * http://comments.gmane.org/gmane.comp.video.blender.python/206
- image via shared texture across opengl context (blender  / x) ??
  * http://developer.download.nvidia.com/opengl/specs/GL_NV_copy_image.txt
  * http://www.gamedev.net/topic/634947-sharing-a-texture-between-multiple-processes/
- using ipc
  * http://stackoverflow.com/questions/9250648/fast-ipc-socket-communication-in-java-python
- alternate procotol/serialization
  * [Cap’n Proto](http://kentonv.github.io/capnproto/otherlang.html)
  * [msgpack](http://msgpack.org/) + [MessagePack-RPC](https://github.com/msgpack-rpc/msgpack-rpc)
  * [opengex](http://opengex.org)

# Extension

- server can send a "panel" with a list of additionnals commands

# links

*
* [Blender related python snippets to get you started. Learn blender bpy today.](http://blenderscripting.blogspot.fr/), [bgl drawing with OpenGL onto blender 2.5 view ](http://blenderscripting.blogspot.fr/2011/07/bgl-drawing-with-opengl-onto-blender-25.html)
* http://wiki.blender.org/index.php/Dev:2.6/Source/Render/RenderEngineAPI
* http://wiki.blender.org/index.php/Dev:2.6/Source/Render/UpdateAPI
* http://wiki.blender.org/index.php/Dev:Source/Architecture/External_Engine_Interface ??
* http://www.blender.org/api/blender_python_api_2_72_release/bpy.types.RenderEngine.html
* [Module BGL: affichage d'image](http://jmsoler.free.fr/didacticiel/blender/tutor/def_tga_pic.htm)
* [tga](http://www.martinreddy.net/gfx/2d/TGA.txt)
* Python [18.5.6. Streams (high-level API)](https://docs.python.org/3/library/asyncio-stream.html#asyncio-tcp-echo-client-streams)
* http://blender.stackexchange.com/questions/1645/how-to-monitor-render-process-in-a-thread-safe-manner
* http://stackoverflow.com/questions/22190403/how-could-i-use-requests-in-asyncio
* http://www.blender.org/api/blender_python_api_2_61_0/info_tips_and_tricks.html#bundled-python-extensions
* blender streaming via websocket
  * http://code.google.com/p/pyppet/
  * http://blenderartists.org/forum/showthread.php?243522-Streaming-data-from-Blender-into-Three-js-%28WebGL-Websockets%29
  * http://www.blend4web.com streaming
* some ~ renderengine for blender :
  * http://www.thearender.com/cms/index.php/plugins/thea-for-blender.html
  * http://wiki.blender.org/index.php/Extensions:2.6/Py/Scripts/Game_Engine/Gamekit_Engine
  * https://github.com/YafaRay/Blender-Exporter/blob/master/io/yaf_export.py
  * http://wiki.blender.org/index.php/Extensions:2.6/Py/Scripts/Render/POV-Ray
  * https://svn.blender.org/svnroot/bf-extensions/trunk/py/scripts/addons/render_povray/render.py
* level editing
  * http://code.blender.org/index.php/2014/06/supporting-game-developers-with-blender-2-71/
  * http://www.reddit.com/r/gamedev/comments/1nddr8/are_there_any_open_source_3d_level_editors/
  * http://kristianduske.com/trenchbroom/
  * http://gamedev.stackexchange.com/questions/35265/create-levels-using-blender
* http://cgcookiemarkets.com/blender/contest-blender-add-on/
* [bdx](https://github.com/GoranM/bdx) blender + libgdx framework

---

import msgpack

import sys
ogex = sys.modules['OpenGex-Blender']
ogex.

extends OpenGexExporter
override file
override/copy + adapte execute
