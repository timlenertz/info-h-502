import numpy as np
import random
import bpy

class Terrain:
	"""Generates random terrain height map, using diamond-square algorithm."""

	initial_height_range = (0.0, 1.0)
	roughness = 1.0

	def __init__(self, n):
		self.side_length = 2**n + 1
		self.terrain = np.empty((self.side_length, self.side_length))
		self.terrain.fill(np.nan)


	def __square(self, pos, r, d):
		x, y = pos
		if not np.isnan(self.terrain[y, x]):
			return

		positions = [
			(y - r, x - r),
			(y - r, x + r),
			(y + r, x - r),
			(y + r, x + r)
		];
		self.terrain[y, x] = self.__average(positions) + random.uniform(-d, d)


	def __diamond(self, pos, r, d):
		x, y = pos
		if not np.isnan(self.terrain[y, x]):
			return

		positions = [
			(y - r, x),
			(y, x - r),
			(y, x + r),
			(y + r, x)
		];
		self.terrain[y, x] = self.__average(positions) + random.uniform(-d, d)


	def __average(self, positions):
		values = []
		for y, x in positions:
			if (0 <= x < self.side_length) and (0 <= y < self.side_length):
				value = self.terrain[y, x]
				if not np.isnan(value):
					values.append(value)
		return np.mean(values)
	
	
	def __subdivide(self, full, d):
		half = full // 2
		if(half < 1):
			return;
			
		for y in range(half, self.side_length, full):
			for x in range(half, self.side_length, full):
				self.__square((x, y), half, d)

		for y in range(0, self.side_length, half):
			for x in range((y + half)%full, self.side_length, full):
				self.__diamond((x, y), half, d)
		
		self.__subdivide(half, d / 2.0)
			
	
	def generate(self):
		self.terrain[0, 0] = random.uniform(*self.initial_height_range)
		self.terrain[0, -1] = random.uniform(*self.initial_height_range)
		self.terrain[-1, 0] = random.uniform(*self.initial_height_range)
		self.terrain[-1, -1] = random.uniform(*self.initial_height_range)

		self.__subdivide(self.side_length - 1, self.roughness)
		
	
	def create_blender_mesh(self, scale, name="terrain"):
		len = self.side_length
		
		vertices = []		
		for y in range(0, len):
			vert_y = float(scale * y) / len
			for x in range(0, self.side_length):
				vert_x = float(scale * x) / len
				vert_z = scale * self.terrain[y, x]
				vert = (vert_x, vert_y, vert_z)
				vertices.append(vert)
		
		faces = []
		for i in range(0, len*(len-1)):
			if i > 0 and i % len == 0:
				continue
			a = i
			b = i + 1
			c = i + len + 1
			d = i + len
			face = (a, b, c, d)
			#faces.append(face)
			
		mesh = bpy.data.meshes.new(name)
		mesh.from_pydata(vertices, [], faces)
		mesh.update(calc_edges=True)
		return mesh


class City:
	def __init__(self, n):
		self.terrain = Terrain(n)
	
	def generate(self):
		self.terrain.generate()
	
	def create_blender_object(self, name="City"):
		scene = bpy.context.scene
	
		# Root
		root = bpy.data.objects.new(name=name, object_data=None)
		
		# Terrain
		terrain_mesh = self.terrain.create_blender_mesh(1.0)
		terrain_obj = bpy.data.objects.new("Terrain", terrain_mesh)
		terrain_obj.parent = root
		scene.objects.link(terrain_obj)
		
		return root