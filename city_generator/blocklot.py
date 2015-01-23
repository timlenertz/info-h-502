import numpy as np
import random
import math
import bpy
import networkx as nx

from . import util

class Lot(object):
	def __init__(self, city_cell, cycle, outer_edges):
		self.city_cell = city_cell
		self.city = self.city_cell.city
		self.terrain = self.city.terrain
		self.cycle = cycle
		self.outer_edges = outer_edges
		
	
	def generate(self):
		pass
	
	def __create_skyscraper_mesh(self, height, name='skyscraper'):
		n = self.cycle.number_of_vertices()
		vertices = [None]*(2*n)
		faces = []
		
		center = self.cycle.center()
		
		z = min([self.terrain.elevation_at(*p) for p in self.cycle])
		i = 0
		for p in self.cycle.vertices_iter():
			x, y = p
			vertices[i] = (x - center[0], y - center[1], z)
			vertices[i + n] = (x - center[0], y - center[1], z + height)
			i += 1
		
		faces.append( list(range(0, n)) )
		faces.append( list(range(n, n+n)) )
		for i, j in util.cycle_pairs( list(range(0, n)) ):
			face = [i, j, j + n, i + n]
			faces.append(face)
		
		mesh = bpy.data.meshes.new(name)
		mesh.from_pydata(vertices, [], faces)
		mesh.update(calc_edges=True)
		return mesh, center
	
	def create_blender_object(self, parent):
		height = random.uniform(10.0, 30.0)
		mesh, center = self.__create_skyscraper_mesh(height, 'skyscraper')
		skyscraper_obj = bpy.data.objects.new('skyscraper', mesh)
		skyscraper_obj.location = (center[0], center[1], 0)
		skyscraper_obj.scale = (0.95, 0.95, 1.0)
		skyscraper_obj.parent = parent
		bpy.context.scene.objects.link(skyscraper_obj)
		return skyscraper_obj