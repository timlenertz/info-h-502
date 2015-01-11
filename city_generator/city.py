import numpy as np
import random
import math
import bpy
import os

from . import plan, terrain


class City(object):
	def __init__(self):
		self.terrain = terrain.Terrain()
		self.plan = plan.Plan(self.terrain)
	
	def generate(self):
		self.terrain.generate()
		self.plan.generate()
		
	def create_blender_object(self, name):
		scene = bpy.context.scene
			
		# Root
		root = bpy.data.objects.new(name=name, object_data=None)
		
		# Terrain
		self.terrain.create_blender_object(root)
		
		# Primary Roads
		self.plan.road_network.create_blender_roads(root)
		
		return root