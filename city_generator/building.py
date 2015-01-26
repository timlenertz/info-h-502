import numpy as np
import random
import math
import bpy
import networkx as nx
import bmesh


from . import util, assets

def cuboid_without_bottom(x_range, y_range, z_range):
	vertices = [
		# Top
		(x_range[0], y_range[0], z_range[1]),
		(x_range[1], y_range[0], z_range[1]),
		(x_range[1], y_range[1], z_range[1]),
		(x_range[0], y_range[1], z_range[1]),
		# Bottom
		(x_range[0], y_range[0], z_range[0]),
		(x_range[1], y_range[0], z_range[0]),
		(x_range[1], y_range[1], z_range[0]),
		(x_range[0], y_range[1], z_range[0])
	]
	faces = [
		[0, 1, 2, 3],
		[0, 3, 7, 4],
		[1, 2, 6, 5],
		[3, 2, 6, 7],
		[0, 1, 5, 4]
	]
	return (vertices, faces)


class Building(object):
	lot = None
	rectangle_pose = None
	terrain = None
		
	def __init__(self, lot):
		self.lot = lot
		self.terrain = lot.terrain
		
	def generate(self):
		if self.lot.is_near_rectangular():
			self.rectangle_pose = self.lot.rectangle_pose()
	
	def create_blender_object(self, parent, name='building'):
		pass

class Skyscraper(Building):
	"""Skyscraper-like structure generated from fractal algorithm on rectangular base."""
	mesh = None
	height = None
	iterations = None
	
	def __transform(self, box, iterations_left):
		if iterations_left == 0:
			return
			
		vertices, faces = box
				
		x_range = (vertices[0][0], vertices[1][0])
		x_diff = x_range[1] - x_range[0]
		y_range = (vertices[0][1], vertices[3][1])
		y_diff = y_range[1] - y_range[0]
		
		# Choose rectangle on top face
		r = 0.1
		x_subrange = (
			random.uniform(x_range[0], x_range[0] + r*x_diff),
			random.uniform(x_range[1] - r*x_diff, x_range[1])
		)
		y_subrange = (
			random.uniform(y_range[0], y_range[0] + r*y_diff),
			random.uniform(y_range[1] - r*y_diff, y_range[1])
		)
		
		height = vertices[0][2]
		base = vertices[4][2]
		if iterations_left > (self.iterations // 2):
			new_base = base + random.uniform(0.05, 0.10)*(height - base)
		else:
			new_base = base + random.uniform(0.7, 0.85)*(height - base)

		# New cuboid which will be recursively modified		
		new_cuboid = cuboid_without_bottom(x_subrange, y_subrange, (new_base, height))

		# Recursively transform new cuboid
		self.__transform(new_cuboid, iterations_left - 1)
		new_vertices, new_faces = new_cuboid

		# Extrude remaining surface downwards
		del faces[0] # Remove old top face
		for i in range(0, 4): # Adjust old's height
			vertices[i] = (vertices[i][0], vertices[i][1], new_base)
		
		# Merge
		offset = len(vertices)
		vertices.extend(new_vertices)
		for i, face in enumerate(new_faces):
			for j, _ in enumerate(face):
				new_faces[i][j] += offset
		faces.extend([
			[0, 1, 8+5, 8+4],
			[1, 2, 8+6, 8+5],
			[2, 3, 8+7, 8+6],
			[3, 0, 8+4, 8+7]
		])
		faces.extend(new_faces)
		
	def generate(self):
		super(Skyscraper, self).generate()
	
		if self.rectangle_pose is None:
			return
		
		self.height = random.uniform(30, 70)
		self.iterations = random.randint(2, 11)
		
		dimensions, position, rotation = self.rectangle_pose
		sx, sy = dimensions
		self.mesh = cuboid_without_bottom((-sx/2, sx/2), (-sy/2, sy/2), (0, self.height))
		self.__transform(self.mesh, self.iterations)

	
	def create_blender_object(self, parent, name='skyscraper'):
		if self.mesh is None:
			return
		
		dimensions, position, rotation = self.rectangle_pose
		vertices, faces = self.mesh
		mesh = bpy.data.meshes.new(name)
		mesh.from_pydata(vertices, [], faces)
		mesh.update(calc_edges=True)

		skyscraper_obj = bpy.data.objects.new(name, mesh)
		skyscraper_obj.parent = parent
		skyscraper_obj.location = (position[0], position[1], self.terrain.elevation_at(*position))
		skyscraper_obj.rotation_mode = 'AXIS_ANGLE'
		skyscraper_obj.rotation_axis_angle = (rotation, 0.0, 0.0, 1.0)
		bpy.context.scene.objects.link(skyscraper_obj)
		return skyscraper_obj


class Office(Building):
	center = None
	outline = None

	def generate(self):
		super(Office, self).generate()
		
		self.outline = self.lot.outline.clone()
		self.center = self.outline.center()
		self.outline.contract(2.0)		
		center_x, center_y = self.center

		self.height = random.uniform(8.0, 15.0)
		self.roof_height = random.uniform(1.0, 3.0)

		# Vertices and faces for walls
		vertices_bottom, vertices_top = [], []
		for p in self.outline:
			x, y = p[0] - center_x, p[1] - center_y
			vertices_bottom.append( (x, y, self.terrain.elevation_at(*p)) )
			vertices_top.append( (x, y, self.height) )
		
		vertices = vertices_bottom + vertices_top
		faces = []
		n = self.outline.number_of_vertices()
		t = 0.4
		for i, j in util.cycle_pairs(list(range(n))):
			face = [i, j, j + n, i + n]
			faces.append(face)
			w = util.distance(vertices[i], vertices[j]) * t
			h = self.height * t
		
		faces.append(list(range(n, 2*n)))
		
		self.mesh = vertices, faces
	
	def create_blender_object(self, parent, name='office'):		
		vertices, faces = self.mesh
		mesh = bpy.data.meshes.new(name)
		mesh.from_pydata(vertices, [], faces)
		mesh.update(calc_edges=True)

		house_obj = bpy.data.objects.new(name, mesh)
		
		house_obj.parent = parent
		center_x, center_y = self.center
		house_obj.location = (center_x, center_y, self.terrain.elevation_at(center_x, center_y))
		bpy.context.scene.objects.link(house_obj)
		return house_obj




class House(Building):
	center = None
	outline = None
	wall_texture = None
	roof_texture = None
	wall_mesh = None
	roof_mesh = None

	def generate(self):
		super(House, self).generate()
		
		self.outline = self.lot.outline.clone()
		self.center = self.outline.center()
		self.outline.contract(2.0)		
		center_x, center_y = self.center

		self.height = random.uniform(8.0, 15.0)
		self.roof_height = random.uniform(1.0, 3.0)

		# Vertices and faces for walls
		vertices_bottom, vertices_top, faces = [], [], []
		for p in self.outline:
			x, y = p[0] - center_x, p[1] - center_y
			vertices_bottom.append( (x, y, self.terrain.elevation_at(*p)) )
			vertices_top.append( (x, y, self.height) )
		
		vertices = vertices_bottom + vertices_top
		faces = []
		t = 0.1
		n = self.outline.number_of_vertices()
		for i, j in util.cycle_pairs(list(range(n))):
			face = [i, j, j + n, i + n]
			faces.append(face)
			w = util.distance(vertices[i], vertices[j]) * t
			h = self.height * t
			
		self.wall_mesh = vertices, faces	
	
	
		# Vertices and 1 face for base of roof
		vertices, faces = [], []
		roof = self.outline.clone()
		roof.expand(0.3)
		faces.append(list(range( 0, roof.number_of_vertices() )))
		roof_vertices_offset = len(vertices)
		for p in roof:
			x, y = p[0] - center_x, p[1] - center_y
			vertices.append( (x, y, self.height) )
	
		# Make roof top: move points towards center
		roof_top = roof.clone()
		c = roof_top.center()
		r = 0.3
		for i, p in enumerate(roof_top.vertices):
			pc = (c[0] - p[0], c[1] - p[1])
			p = (p[0] + r*pc[0], p[1] + r*pc[1])
			roof_top.vertices[i] = p
			
		# Add vertices and face for roof top
		for p in roof_top:
			x, y = p[0] - center_x, p[1] - center_y
			vertices.append( (x, y, self.height + self.roof_height) )
		faces.append(list(range( roof_top.number_of_vertices() )))
		
		# Connect roof base to roof top
		for i, j in util.cycle_pairs(list(range(n))):
			face = [
				i,
				j,
				j + n,
				i + n
			]
			faces.append(face)
	
		self.roof_mesh = vertices, faces

	
	def create_blender_object(self, parent, name):	
		center_x, center_y = self.center
		house_obj = bpy.data.objects.new(name, object_data=None)
		house_obj.parent = parent
		center_x, center_y = self.center
		house_obj.location = (center_x, center_y, self.terrain.elevation_at(center_x, center_y))
		bpy.context.scene.objects.link(house_obj)
	
		vertices, faces = self.wall_mesh
		mesh = bpy.data.meshes.new(name)
		mesh.from_pydata(vertices, [], faces)
		mesh.update(calc_edges=True)
		
		house_walls_obj = bpy.data.objects.new(name+'_walls', mesh)
		bpy.context.scene.objects.link(house_walls_obj)
		house_walls_obj.parent = house_obj



		vertices, faces = self.roof_mesh
		mesh = bpy.data.meshes.new(name)
		mesh.from_pydata(vertices, [], faces)
		mesh.update(calc_edges=True)
		
		house_roof_obj = bpy.data.objects.new(name+'_roof', mesh)
		bpy.context.scene.objects.link(house_roof_obj)
		house_roof_obj.parent = house_obj
		
		return house_obj