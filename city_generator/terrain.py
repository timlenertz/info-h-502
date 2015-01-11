import numpy as np
import random
import math
import bpy

from . import assets

class HeightMap(object):
	"""Randomly generated height map, using diamond-square algorithm."""
	initial_height_range = (0.0, 1.0)
	roughness = 0.6
	resolution = 7
	
	def __square(self, pos, r, d):
		x, y = pos
		positions = [
			(y - r, x - r),
			(y - r, x + r),
			(y + r, x - r),
			(y + r, x + r)
		];
		self.image[y, x] = self.__average(positions) + random.uniform(-d, d)


	def __diamond(self, pos, r, d):
		x, y = pos
		positions = [
			(y - r, x),
			(y, x - r),
			(y, x + r),
			(y + r, x)
		];
		self.image[y, x] = self.__average(positions) + random.uniform(-d, d)


	def __average(self, positions):
		values = []
		for y, x in positions:
			if (0 <= x < self.side_length) and (0 <= y < self.side_length):
				value = self.image[y, x]
				if not np.isnan(value):
					values.append(value)
		return np.mean(values)
	
	
	def __subdivide(self, full, d):
		half = full // 2
		if(half < 1):
			return
			
		for y in range(half, self.side_length, full):
			for x in range(half, self.side_length, full):
				self.__square((x, y), half, d)

		for y in range(0, self.side_length, half):
			for x in range((y + half)%full, self.side_length, full):
				self.__diamond((x, y), half, d)
		
		self.__subdivide(half, d / 2.0)
		
	
	def generate(self):
		self.side_length = 2**self.resolution + 1
		self.image = np.empty((self.side_length, self.side_length))
		self.image.fill(np.nan)

		self.image[0, 0] = random.uniform(*self.initial_height_range)
		self.image[0, -1] = random.uniform(*self.initial_height_range)
		self.image[-1, 0] = random.uniform(*self.initial_height_range)
		self.image[-1, -1] = random.uniform(*self.initial_height_range)

		self.__subdivide(self.side_length - 1, self.roughness)




class Terrain(HeightMap):
	"""Terrain based on height map."""
	width = 500.0
	height = 50.0
	
	def create_blender_mesh(self, name="terrain"):
		sl = self.side_length
		
		vertices = []		
		for y in range(0, sl):
			vert_y = float(self.width * y) / sl
			for x in range(0, sl):
				vert_x = float(self.width * x) / sl
				vert_z = self.height * self.image[y, x]
				vert = (vert_x, vert_y, vert_z)
				vertices.append(vert)
		
		faces = []
		for i in range(0, sl*(sl-1)):
			if (i + 1) % sl == 0:
				continue
			a = i
			b = i + 1
			c = i + sl + 1
			d = i + sl
			face = (a, b, c, d)
			faces.append(face)
			
		mesh = bpy.data.meshes.new(name)
		mesh.from_pydata(vertices, [], faces)
		mesh.update(calc_edges=True)
		return mesh
	

	def create_blender_object(self, parent):	
		terrain_mesh = self.create_blender_mesh('terrain')
		terrain_obj = bpy.data.objects.new('terrain', terrain_mesh)
		terrain_obj.parent = parent
		#bpy.context.scene.objects.link(terrain_obj)
		
		mat = bpy.data.materials.new('terrain')
		mat.diffuse_color = (1.0, 1.0, 1.0)
		mat.diffuse_shader = 'LAMBERT'
		mat.diffuse_intensity = 1.0
		mat.specular_intensity = 0.0
		mat.ambient = 1
		terrain_obj.data.materials.append(mat)
		
		tex = assets.load_texture('terrain')
		mtex = mat.texture_slots.add()
		mtex.texture = tex
		mtex.texture_coords = 'UV'
		mtex.use_map_color_diffuse = True
		mtex.use_map_color_emission = True
		mtex.emission_color_factor = 0.5
		mtex.use_map_density = True
		mtex.mapping = 'FLAT'
		
		return terrain_obj		


	
	def height_at(self, x, y):
		x_ind = int(math.floor(x * self.side_length / self.width))
		x_ind = min(x_ind, self.side_length - 1)
		x_ind = max(x_ind, 0)
					
		y_ind = int(math.floor(y * self.side_length / self.width))
		y_ind = min(y_ind, self.side_length - 1)
		y_ind = max(y_ind, 0)
	
		return self.height * self.image[y_ind, x_ind]