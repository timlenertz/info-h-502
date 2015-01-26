import os
import bpy

def load_assets_library(link):
	lib = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets.blend')
	return bpy.data.libraries.load(lib, link=link)


def load_object(name, link=True):
	with load_assets_library(link) as (data_from, data_to):
		data_to.objects = [name]
	return bpy.data.objects[name]


def load_texture(name):
	file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'textures/' + name + '.jpg')
	img = bpy.data.images.load(file)
	tex = bpy.data.textures.new(name, type='IMAGE')
	tex.image = img
	return tex