import numpy as np
import random
import math
import bpy

from . import assets, util

class HeightMap(object):
	"""Randomly generated height map.
	
	Generated using diamond-square algorithm."""
	
	initial_height_range = (0.0, 1.0) # Range for height of four corners
	roughness = 0.6 # Diamond-square roughness parameter
	resolution = 7 # Number of 2x2 subdivisions
	
	image_side_length = None # Image side length in pixel
	image = None # Numpy ndarray of terrain, with shape (pixel_side_length, pixel_side_length)
	
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
			if (0 <= x < self.image_side_length) and (0 <= y < self.image_side_length):
				value = self.image[y, x]
				if not np.isnan(value):
					values.append(value)
		return np.mean(values)
	
	
	def __subdivide(self, full, d):
		half = full // 2
		if(half < 1):
			return
			
		for y in range(half, self.image_side_length, full):
			for x in range(half, self.image_side_length, full):
				self.__square((x, y), half, d)

		for y in range(0, self.image_side_length, half):
			for x in range((y + half)%full, self.image_side_length, full):
				self.__diamond((x, y), half, d)
		
		self.__subdivide(half, d / 2.0)			
	
	def generate(self):
		self.image_side_length = 2**self.resolution + 1
		self.image = np.empty((self.image_side_length, self.image_side_length))
		self.image.fill(np.nan)

		self.image[0, 0] = random.uniform(*self.initial_height_range)
		self.image[0, -1] = random.uniform(*self.initial_height_range)
		self.image[-1, 0] = random.uniform(*self.initial_height_range)
		self.image[-1, -1] = random.uniform(*self.initial_height_range)

		self.__subdivide(self.image_side_length - 1, self.roughness)



class Terrain(HeightMap):
	"""Terrain based on height map."""
	side_length = 500.0 # Extent in X and Y directions (square side length)
	elevation = 50.0 # Elevation in Y direction
	
	pixel_side_length = None # Side length of one image pixel, i.e. side_length / image_side_length
	
	def create_blender_mesh(self, name='terrain'):
		"""Create blender mesh for the terrain."""
		sl = self.image_side_length
		
		# Vertex for each point on the image
		vertices = []		
		for y in range(0, self.image_side_length):
			vert_y = y * self.pixel_side_length
			for x in range(0, self.image_side_length):
				vert_x = x * self.pixel_side_length
				vert_z = self.elevation * self.image[y, x]
				vert = (vert_x, vert_y, vert_z)
				vertices.append(vert)
		
		# Quad face for each square of 4 adjacent pixels
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
		
		# Create the mesh object
		mesh = bpy.data.meshes.new(name)
		mesh.from_pydata(vertices, [], faces)
		mesh.update(calc_edges=True)
		
		return mesh
	


	def create_blender_object(self, parent):
		"""Create textured blender object for the terrain."""
		# Create mesh and object with that mesh
		terrain_mesh = self.create_blender_mesh('terrain')
		terrain_obj = bpy.data.objects.new('terrain', terrain_mesh)
		terrain_obj.parent = parent
		bpy.context.scene.objects.link(terrain_obj)
		
		# Create material
		mat = bpy.data.materials.new('terrain')
		mat.diffuse_color = (1.0, 1.0, 1.0)
		mat.diffuse_shader = 'LAMBERT'
		mat.diffuse_intensity = 1.0
		mat.specular_intensity = 0.0
		mat.ambient = 1
		terrain_obj.data.materials.append(mat)
		
		# Create texture for the material
		tex = assets.load_texture('terrain.jpg')
		mtex = mat.texture_slots.add()
		mtex.texture = tex
		mtex.texture_coords = 'UV'
		mtex.use_map_color_diffuse = True
		mtex.use_map_color_emission = True
		mtex.emission_color_factor = 0.5
		mtex.use_map_density = True
		mtex.mapping = 'FLAT'
		
		# Add modifier
		sub_modifier = terrain_obj.modifiers.new("Subdivision Surface", type='SUBSURF')
		
		return terrain_obj
	
	
	def generate(self):
		super(Terrain, self).generate()
		self.pixel_side_length = self.side_length / self.image_side_length
	
	def to_image(self, x, y):
		"""From terrain coordinates to image pixel coordinates."""
		x_ind = int(math.floor(x / self.pixel_side_length))
		x_ind = min(x_ind, self.side_length - 1)
		x_ind = max(x_ind, 0)			
		y_ind = int(math.floor(y / self.pixel_side_length))
		y_ind = min(y_ind, self.side_length - 1)
		y_ind = max(y_ind, 0)
		return (x_ind, y_ind)
	
	def to_terrain(self, x_ind, y_ind):
		"""From image pixel coordinates to terrain coordinates."""
		x = x_ind * self.pixel_side_length
		y = y_ind * self.pixel_side_length
		return (x, y)
	
	def elevation_at(self, x, y):
		"""Terrain elevation at given terrain coordinates."""
		x_ind, y_ind = self.to_image(x, y)
		return self.elevation * self.image[y_ind, x_ind]

	def flatten_segment(self, a, b, a_el=None, b_el=None):
		ab = (b[0] - a[0], b[1] - a[1])
		ab_len = math.sqrt(ab[0]**2 + ab[1]**2)
					
		w = 4
		emboss = 0.01 / self.elevation
		a_i = self.to_image(*a)
		b_i = self.to_image(*b)
		
		if (a_el is None) or (a_el is None):
			a_el = self.image[a_i[1], a_i[0]]
			b_el = self.image[b_i[1], b_i[0]]
		else:
			a_el /= self.elevation
			b_el /= self.elevation
			
		mn = ( \
			min(a_i[0] - w, b_i[0] - w), \
			min(a_i[1] - w, b_i[1] - w) \
		)
		mx = ( \
			max(a_i[0] + w, b_i[0] + w), \
			max(a_i[1] + w, b_i[1] + w) \
		)
		last = self.image_side_length - 1
		mn = max(mn[0], 0), max(mn[1], 0)
		mx = min(mx[0], last), min(mx[1], last)
		
		def flat_depth(p):
			ap = (p[0] - a[0], p[1] - a[1])
			dot = ab[0]*ap[0] + ab[1]*ap[1]
			ratio = max(min(dot / ab_len**2.0, 1.0), 0.0)
			interpolated = ratio*a_el + (1.0 - ratio)*b_el
			return interpolated - emboss
		
		for x_i in range(mn[0], mx[0]):
			for y_i in range(mn[1], mx[1]):
				p_i = (x_i, y_i)
				p = self.to_terrain(*p_i)
				flat = flat_depth(p_i)
				real = self.image[y_i, x_i]
				d = abs(util.line_to_point_distance((a, b), p))
				if d < w * self.pixel_side_length:
					ratio = d / w
					ratio = max(0.0, min(ratio, 1.0))**2.0
					el = ratio*real + (1.0 - ratio)*flat
					self.image[y_i, x_i] = el
		