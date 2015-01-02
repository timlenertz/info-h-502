import os
import bpy

def load_assets_library():
	lib = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets.blend')
	return bpy.data.libraries.load(lib, link=False)


def load_object(name):
	with load_assets_library() as (data_from, data_to):
		data_to.objects = [name]
	return bpy.data.objects[name]