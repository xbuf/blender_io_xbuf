import bpy

def pre_ob_updated(scene):
    ob = scene.objects.active
    if ob is not None and ob.is_updated:
        print("%s - Object is_updated (pre)" % ob.name)

def pre_ob_updated_data(scene):
    ob = scene.objects.active
    if ob is not None and ob.is_updated_data:
        print("%s - Object is_updated_data (pre)" % ob.name)

def pre_ob_data_updated(scene):
    ob = scene.objects.active
    if ob is not None and ob.data.is_updated:
        print("%s - Object data is_updated (pre)" % ob.data.name)

def pre_ob_data_updated_data(scene):
    ob = scene.objects.active
    if ob is not None and ob.data.is_updated_data:
        print("%s - Object data is_updated_data (pre)" % ob.data.name)

def post_ob_updated(scene):
    ob = scene.objects.active
    if ob is not None and ob.is_updated:
        print("%s - Object is_updated (post)" % ob.name)

def post_ob_updated_data(scene):
    ob = scene.objects.active
    if ob is not None and ob.is_updated_data:
        print("%s - Object is_updated_data (post)" % ob.name)

def post_ob_data_updated(scene):
    ob = scene.objects.active
    if ob is not None and ob.data.is_updated:
        print("%s - Object data is_updated (post)" % ob.data.name)

def post_ob_data_updated_data(scene):
    ob = scene.objects.active
    if ob is not None and ob.data.is_updated_data:
        print("%s - Object data is_updated_data (post)" % ob.data.name)

bpy.app.handlers.scene_update_pre.clear()
bpy.app.handlers.scene_update_pre.clear()
bpy.app.handlers.scene_update_pre.clear()
bpy.app.handlers.scene_update_pre.clear()

bpy.app.handlers.scene_update_post.clear()
bpy.app.handlers.scene_update_post.clear()
bpy.app.handlers.scene_update_post.clear()
bpy.app.handlers.scene_update_post.clear()

bpy.app.handlers.scene_update_pre.append(pre_ob_updated)
bpy.app.handlers.scene_update_pre.append(pre_ob_updated_data)
bpy.app.handlers.scene_update_pre.append(pre_ob_data_updated)
bpy.app.handlers.scene_update_pre.append(pre_ob_data_updated_data)

bpy.app.handlers.scene_update_post.append(post_ob_updated)
bpy.app.handlers.scene_update_post.append(post_ob_updated_data)
bpy.app.handlers.scene_update_post.append(post_ob_data_updated)
bpy.app.handlers.scene_update_post.append(post_ob_data_updated_data)
