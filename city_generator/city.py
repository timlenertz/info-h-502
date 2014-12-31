import numpy as np
import random
import math
import bpy

from . import terrain, plan

class City:
	def __init__(self):
		self.terrain = Terrain()
		self.plan = Plan(terrain)
	
	def generate(self):
		self.terrain.generate()
	
	def create_blender_object(self, name="City"):
		scene = bpy.context.scene
	
		# Root
		root = bpy.data.objects.new(name=name, object_data=None)
		
		# Terrain
		scale = (20.0, 20.0, 1.0)
		terrain_mesh = self.terrain.create_blender_mesh(scale)
		terrain_obj = bpy.data.objects.new("Terrain", terrain_mesh)
		terrain_obj.parent = root
		scene.objects.link(terrain_obj)
		
		return root