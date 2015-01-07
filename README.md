A blender addon to allow an external renderer (like a game engine) to be used in blender viewport. The addon provide a generic (renderer agnostic) client that connect to a running server (a game) and display server image into Blender.

License: [GPL](LICENSE.txt)

> The addon is WIP

# Uses Cases

* Preview model with game engine
* Use Blender as level editor for a game (or for a game engine) with realtime rendering (including effects, hud, entities,... not managed by blender)

[![blender external renderer (a game engine)](youtube_img.png)](http://www.youtube.com/watch?v=3pQd65_dkeM)


## Installation

1. download the zip from [releases section](https://github.com/davidB/blender_external_renderer/releases)
2. in Blender : User Preferences... > Add-ons > Install from File... (select the downloaded .zip)
3. in Blender : User Preferences... > Add-ons > enable the addon (check box of "Render: External Render Engine")

## Usage

1. start your external render engine
2. in Blender : Select "External Render" in the render list
3. in Blender : Select "Rendered" in the viewport shading button of 3D View

## Setup used for the video-demo

* Blender 2.72b
* [blender_external_renderer 0.3.0](https://github.com/davidB/blender_external_renderer/releases/tag/0.3.0)
* ModelViewer 0.3.0 for jMonkeyEngine from [jme3_ext_assettools](https://github.com/davidB/jme3_ext_assettools/releases/tag/0.3.0)
