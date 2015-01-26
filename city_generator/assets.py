import os
import bpy
import random

def load_assets_library(link):
	lib = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets.blend')
	return bpy.data.libraries.load(lib, link=link)


def load_object(name, link=True):
	with load_assets_library(link) as (data_from, data_to):
		data_to.objects = [name]
	return bpy.data.objects[name]

def load_texture(name):
	if name in bpy.data.textures:
		return bpy.data.textures[name]
	else:
		file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'textures/' + name)
		img = bpy.data.images.load(file)
		tex = bpy.data.textures.new(name, type='IMAGE')
		tex.image = img
		return tex

def choose_random_texture(dir):
	return None
	fulldir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'textures/') + dir + '/'
	files = os.listdir(fulldir)
	file = None
	while (file is None) or (file[0] == '.'):
		file = random.choice(files)
	return dir + '/' + file
