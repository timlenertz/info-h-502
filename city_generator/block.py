import numpy as np
import random
import math
import bpy
import networkx as nx

from . import util, blocklot

class CityBlock(object):
	cycle = None  # Roads enclosing block, clockwise list of vertices.
	contracted_cycle = None
	sidewalk_width = 5.0
	minimal_area = 30.0
	valid = True
	lots = None

	def __init__(self, city_cell, cycle):
		self.city_cell = city_cell
		self.cycle = cycle
		if not util.polygon_is_clockwise(self.cycle):
			self.cycle.reverse()
	
	def __make_contracted_cycle(self):
		contracted_segments = []
		for edge in util.cycle_pairs(self.cycle):
			a, b = edge
			ab = (b[0] - a[0], b[1] - a[1])
			ap = (ab[1], -ab[0])
			len_ap = math.sqrt(ap[0]**2 + ap[1]**2)
			ap = (self.sidewalk_width * ap[0] / len_ap, self.sidewalk_width * ap[1] / len_ap)
			p = (a[0] + ap[0], a[1] + ap[1])
			q = (p[0] + ab[0], p[1] + ab[1])
			seg = (p, q)
			contracted_segments.append(seg)
		
		contracted_points = []
		for e, f in util.cycle_pairs(contracted_segments):
			p = util.line_intersection_point(e, f)
			if p is not None:
				contracted_points.append(p)
		
		self.contracted_cycle = contracted_points
	
	
	def __split_lot_recursive(self, lot, outer_edges, depth):
		max_iterations = 20
		minimal_area = 100
		minimal_ratio = 0.3
	
		vec = lambda edge: (edge[1][0] - edge[0][0], edge[1][1] - edge[0][1])
	
		edges = list(util.cycle_pairs(lot))

		# Drop this lot if it is not adjacent to road
		locked_in = True
		for edge in edges:
			if edge in outer_edges:
				locked_in = False
				break
		
		if locked_in:
			return
		elif util.polygon_area(lot) < minimal_area and util.polygon_is_simple(lot):			
			def angle(edge_pair):
				e1, e2 = edge_pair
				v1, v2 = vec(e1), vec(e2)
				dot = v1[0]*v2[0] + v1[1]*v2[1]
				dot /= (util.distance(*e1) * util.distance(*e2))
				return np.arccos(dot)
			
			min_angle = min(util.cycle_pairs(edges), key=angle)
			if angle(min_angle) > 0.3*np.pi:
				lot_outer = [edge for edge in edges if (edge in outer_edges)]
				lot_obj = blocklot.Lot(self.city_cell, lot, lot_outer)
				self.lots.append(lot_obj)
		elif len(lot) >= 3 and depth <= max_iterations:
			# Cutting the lot in two...
			# First chooses 2 edges to cut through
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
			self.__split_lot_recursive(sublot1, outer_edges[:], depth + 1)
			self.__split_lot_recursive(sublot2, outer_edges[:], depth + 1)
	
	def __make_lots(self):
		self.lots = []		
		outer_edges = list(util.cycle_pairs(self.contracted_cycle))
		self.__split_lot_recursive(self.contracted_cycle, outer_edges, 1)

		for lot in self.lots:
			lot.generate()
			

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
		if util.polygon_area(self.cycle) <= self.minimal_area:
			self.valid = False
			return
		
		self.__make_contracted_cycle()
		self.valid = util.polygon_is_simple(self.contracted_cycle) \
			and util.polygon_is_clockwise(self.contracted_cycle) \
			and util.polygon_area(self.contracted_cycle) > self.minimal_area
		
		if self.valid:
			self.__make_lots()
	
	def create_blender_object(self, root):
		parent = bpy.data.objects.new('block', None)
		parent.parent = root
		bpy.context.scene.objects.link(parent)
		
		for lot in self.lots:
			lot.create_blender_object(parent)
		
