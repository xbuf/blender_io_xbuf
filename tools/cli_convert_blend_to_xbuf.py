import bpy
import sys
import getopt

def usage():
    print("Run this as the following blender command.")
    print("\tblender <blend file> --background --python %r -- -a <assets_root_path> -f <xbuf_file_path>" % (__file__))

def apply_cli():
    if ("--" in sys.argv) == False:
        opts = [("-h", None)]
    else:
        try:
            args_start_pos = sys.argv.index("--") + 1
            my_args = sys.argv[args_start_pos:]
            opts, args = getopt.getopt(my_args, 'ha:f:', ["help", "assets_path=", "file="])
        except getopt.GetoptError:
            print("Opt Error.")
            opts = [("-h", None)]

    filepath = None
    assets_path = None
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            return
        elif opt == "-a":
            assets_path = arg
        elif opt == "-f":
            filepath = arg
    bpy.context.scene.xbuf.assets_path = assets_path
    bpy.ops.export_scene.xbuf(filepath= filepath)

if (__name__ == "__main__"):
    apply_cli()
