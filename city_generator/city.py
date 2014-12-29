import numpy as np
import random
import bpy
import math
import scipy.spatial


class PrimaryRoadNetwork:
	number_of_intersections = 3

	def __init__(self, terrain):
		self.terrain = terrain
	

	def __choose_intersection_points(self):
		"""Choose points on terrain for primary road intersections."""
		# Subdivide terrain into grid where cell side length is power of 2
		# such that there are at least as many cells as intersections  
		depth = int(math.ceil(math.log(self.number_of_intersections, 4)))
		side_number_of_cells = 2**depth
		number_of_cells = side_number_of_cells**2
		assert number_of_cells >= self.number_of_intersections
		cell_side_length = 1.0 / side_number_of_cells
		
		def cell_center(i):
			x = i % side_number_of_cells
			y = i // side_number_of_cells
			center_x = cell_side_length/2.0 + x*cell_side_length
			center_y = cell_side_length/2.0 + y*cell_side_length
			return (center_x, center_y)
		
		# Randomly choose cells that will contain intersection
		intersection_cells = []
		for i in range(self.number_of_intersections):
			cell = random.randint(0, number_of_cells - 1)
			if cell in intersection_cells:
				continue
			intersection_cells.append(cell)
		
		# Randomly place intersection points in these cells
		self.intersection_points = []
		for c in intersection_cells:
			center_x, center_y = cell_center(c)
			sigma = cell_side_length / 7.0
			x = random.normalvariate(center_x, sigma)
			y = random.normalvariate(center_y, sigma)
			self.intersection_points.append((x, y))
		
	
	def __connect_intersection_points(self):
		"""Generate road segments joining the intersection points."""
		triangulation = scipy.spatial.Delaunay(self.intersection_points, qhull_options='Qbb Qc Qz QJ')
		
		
	
	def generate(self):
		self.__choose_intersection_points()
	



class Terrain:
	"""Generates random terrain height map, using diamond-square algorithm."""

	initial_height_range = (0.0, 1.0)
	roughness = 1.0
	resolution = 8

	def __init__(self):
		pass

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
		
	
	def create_blender_mesh(self, scale, name="terrain"):
		sl = self.side_length
		
		vertices = []		
		for y in range(0, sl):
			vert_y = float(scale[1] * y) / sl
			for x in range(0, sl):
				vert_x = float(scale[0] * x) / sl
				vert_z = scale[2] * self.image[y, x]
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


class City:
	def __init__(self):
		self.terrain = Terrain()
	
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