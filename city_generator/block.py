import numpy as np
import random
import math
import bpy
import networkx as nx

from . import util, building

class Lot(object):
	city_cell = None
	city = None
	terrain = None
	outline = None
	outer_edges = None
	
	building = None

	def __init__(self, city_cell, outline, outer_edges):
		self.city_cell = city_cell
		self.city = self.city_cell.city
		self.terrain = self.city.terrain
		self.outline = outline
		self.outer_edges = outer_edges
		
	def is_near_rectangular(self):
		if self.outline.number_of_vertices() != 4:
			return False
		for e1, e2 in util.cycle_pairs(list(self.outline.edges_iter())):
			if not util.near_perpendicular(e1, e2):
				return False
		return True
	
	def rectangle_pose(self):
		edges = list(self.outline.edges_iter())
		e, f = (edges[0], edges[2])
		w = (util.line_to_point_distance(e, f[0]) + util.line_to_point_distance(e, f[1]) \
			+ util.line_to_point_distance(f, e[0]) + util.line_to_point_distance(f, e[1])) / 4.0
		rotation = math.atan2(e[1][1] - e[0][1], e[1][0] - e[0][0]) + np.pi
		
		e, f = (edges[1], edges[3])
		h = (util.line_to_point_distance(e, f[0]) + util.line_to_point_distance(e, f[1]) \
			+ util.line_to_point_distance(f, e[0]) + util.line_to_point_distance(f, e[1])) / 4.0
		
		position = (0.0, 0.0)
		for x, y in self.outline.vertices_iter():
			position = (position[0] + x, position[1] + y)
		position = (position[0] / 4.0, position[1] / 4.0)
	
		return (w, h), position, rotation
	
	
	def generate(self):
		building_types = self.city_cell.building_types[:]
	
		if not self.is_near_rectangular():
			if 'Skyscraper' in building_types:
				building_types.remove('Skyscraper')

		type = random.choice(building_types)
		Class = getattr(building, type)
		self.building = Class(self) 
		
		self.building.generate()
	
	def create_blender_object(self, parent, name):
		self.building.create_blender_object(parent, name+'_building')

	

class Block(object):
	"""Block of a city cell, enclosed by secondary (and primary) roads.
	
	Gets further subdivided into lots, one for each building."""
	city_cell = None # BlocksCell object
	cycle = None  # Roads enclosing block, clockwise Polygon.
	contracted_cycle = None # Same polygon, contracted for sidewalks space.
	
	sidewalk_width = 5.0
	valid = True
	lots = None

	def __init__(self, city_cell, cycle):
		self.city_cell = city_cell
		self.cycle = cycle
		self.cycle.make_clockwise()
			
	
	def __split_lot_recursive(self, lot, outer_edges, depth):
		max_iterations = 20
		minimal_area = 100
		minimal_ratio = 0.3
	
		vec = lambda edge: (edge[1][0] - edge[0][0], edge[1][1] - edge[0][1])
	
		edges = list(lot.edges_iter())

		# Drop this lot if it is not adjacent to road
		locked_in = True
		for edge in edges:
			if edge in outer_edges:
				locked_in = False
				break
		
		if locked_in or lot.area() < self.city_cell.lot_area_range[0]:
			return
			
		elif lot.area() < self.city_cell.lot_area_range[1] and lot.is_simple():
			def angle(edge_pair):
				e1, e2 = edge_pair
				v1, v2 = vec(e1), vec(e2)
				dot = v1[0]*v2[0] + v1[1]*v2[1]
				dot /= (util.distance(*e1) * util.distance(*e2))
				return np.arccos(dot)
			
			min_angle = min(util.cycle_pairs(edges), key=angle)
			if angle(min_angle) > 0.3*np.pi:
				lot_outer = [edge for edge in edges if (edge in outer_edges)]
				lot_obj = Lot(self.city_cell, lot, lot_outer)
				self.lots.append(lot_obj)
				
		elif lot.number_of_vertices() >= 3 and depth <= max_iterations:
			# Cutting the lot in two...
			# First choose 2 edges to cut through
			last_i = len(edges) - 1
		
			# First = longest
			length = lambda i: util.distance_sq(*edges[i])
			longest_i = max(range(len(lot)), key=length)
			longest_j = longest_i + 1 if longest_i != last_i else 0
			longest_edge = edges[longest_i]
			longest_edge_vec = vec(longest_edge)
			longest_edge_len = util.distance(*longest_edge)
		
			# Second = most parallel to first
			def parallelity(i):
				edge = edges[i]
				edge_vec = vec(edges[i])
				dot = edge_vec[0]*longest_edge_vec[0] + edge_vec[1]*longest_edge_vec[1]
				dot /= longest_edge_len
				dot /= util.distance(*edge)
				# Dot=cos of angle between this edge and longest edge. Parallel means angle is 0 or 180,
				# so cos(angle) = 1 (maximum)
				return abs(dot)
					
			other_is = [i for i in range(len(edges)) if i != longest_i]
			opposed_i = max(other_is, key=parallelity)
			opposed_j = opposed_i + 1 if opposed_i != last_i else 0

			# Cut edges at center point
			longest_edge = edges[longest_i]
			opposed_edge = edges[opposed_i]
			center = lambda edge: ((edge[0][0] + edge[1][0])/2.0, (edge[0][1] + edge[1][1])/2.0)
			longest_p = center(longest_edge)
			opposed_p = center(opposed_edge)
			
			# Adjust outer_edges
			if longest_edge in outer_edges:
				outer_edges.remove(longest_edge)
				outer_edges.append( (lot[longest_i], longest_p) )
				outer_edges.append( (longest_p, lot[longest_j]) )
			if opposed_edge in outer_edges:
				outer_edges.remove(opposed_edge)
				outer_edges.append( (lot[opposed_i], opposed_p) )
				outer_edges.append( (opposed_p, lot[opposed_j]) )

			# Create two halves of lot
			sublot1 = []
			sublot2 = []
			if longest_i < opposed_i:
				first_i, first_p = longest_i, longest_p
				second_i, second_p = opposed_i, opposed_p
			else:
				first_i, first_p = opposed_i, opposed_p
				second_i, second_p = longest_i, longest_p

			n = len(lot)
			sublot1.append(second_p)
			for i in range(second_i + 1, n):
				sublot1.append(lot[i])
			for i in range(0, first_i + 1):
				sublot1.append(lot[i])
			sublot1.append(first_p)
			
			sublot2.append(first_p)
			for i in range(first_i + 1, second_i + 1):
				sublot2.append(lot[i])
			sublot2.append(second_p)


			# Recurse into two lots
			self.__split_lot_recursive(util.Polygon(sublot1), outer_edges[:], depth + 1)
			self.__split_lot_recursive(util.Polygon(sublot2), outer_edges[:], depth + 1)
	
	
	def __make_lots(self):
		self.lots = []		
		outer_edges = list(self.contracted_cycle.edges_iter())
		self.__split_lot_recursive(self.contracted_cycle, outer_edges, 1)

	def __create_blender_outline(self, cyc):
		if len(self.cycle) < 2:
			return
		curve = bpy.data.curves.new(name='cycle', type='CURVE')
		curve.dimensions = '3D'
		
		polyline = curve.splines.new('POLY')

		polyline.points.add(len(cyc))
		i = 0
		for p in cyc:
			polyline.points[i].co = (p[0], p[1], 10.0, 1.0)
			i += 1
		polyline.points[i].co = (cyc[0][0], cyc[0][1], 10.0, 1.0)
		
		
		curve_obj = bpy.data.objects.new('cycle_curv', curve)
		#curve_obj.parent = root
		
		bpy.context.scene.objects.link(curve_obj)


	def generate(self):
		if self.cycle.area() <= self.city_cell.lot_area_range[0]:
			self.valid = False
			return
		
		self.contracted_cycle = self.cycle.clone()
		self.contracted_cycle.contract(self.sidewalk_width)
		
		
		self.valid = self.contracted_cycle.is_simple() \
			and self.contracted_cycle.area() <= self.city_cell.lot_area_range[0]
		
		if not self.valid:
			return
			
		self.__make_lots()
		for lot in self.lots:
			lot.generate()


	
	def create_blender_object(self, root):
		if not self.valid:
			return
			
		parent = bpy.data.objects.new('block', None)
		parent.parent = root
		bpy.context.scene.objects.link(parent)
		
		i = 0
		for lot in self.lots:
			lot.create_blender_object(parent, 'lot_'+str(i))
			i += 1
		
