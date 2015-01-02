import numpy as np
import random
import math
import bpy
import os

from . import plan, terrain


class City:
	def __init__(self):
		self.terrain = terrain.Terrain()
		self.plan = plan.Plan(self.terrain)
	
	def generate(self):
		self.terrain.generate()
		self.plan.generate()
		
	def create_blender_object(self, name="City"):
		scene = bpy.context.scene
			
		# Root
		root = bpy.data.objects.new(name=name, object_data=None)
		
		# Terrain
		terrain_mesh = self.terrain.create_blender_mesh()
		terrain_obj = bpy.data.objects.new("Terrain", terrain_mesh)
		terrain_obj.parent = root
		scene.objects.link(terrain_obj)
		
		# Primary Roads
		self.plan.primary_road_network.create_blender_roads()
		
		return root