import math
import numpy as np

def line_to_point_distance_sq(line, p):
	a, b = line
	num = ( (b[1] - a[1])*p[0] - (b[0] - a[0])*p[1] + b[0]*a[1] - b[1]*a[0] )**2
	den = (b[1] - a[1])**2 + (b[0] - a[0])**2
	return num / den

def line_to_point_distance(line, p):
	return math.sqrt(line_to_point_distance_sq(line, p))

def length_sq(v):
	return v[0]**2 + v[1]**2

def length(v):
	return math.sqrt(length_sq(v))

def distance_sq(a, b):
	return (a[0] - b[0])**2 + (a[1] - b[1])**2

def distance(a, b):
	return math.sqrt(distance_sq(a, b))

def near_perpendicular(e1, e2, threshold=0.2):
	u = (e1[1][0] - e1[0][0], e1[1][1] - e1[0][1])
	v = (e2[1][0] - e2[0][0], e2[1][1] - e2[0][1])
	dot = u[0]*v[0] + u[1]*v[1]
	dot /= length(u)
	dot /= length(v)
	return (abs(dot) < 0.2)

	
def projection_is_on_segment(seg, p, seg_length=None):
	"""Check if point p projected on line seg is on the segment."""
	if seg_length is None:
		seg_length = distance(*seg)
	a, b = seg
	ap = (p[0] - a[0], p[1] - a[1])
	ab = (b[0] - a[0], b[1] - a[1])
	ab = (ab[0] / seg_length, ab[1] / seg_length)
	dot = ab[0]*ap[0] + ab[1]*ap[1]
	return (dot > 0) and (dot < seg_length)

def project_on_line(l, p):
	"""Return point p projected on line l (given by two points)."""
	a, b = l
	seg_length = distance(a, b)
	ap = (p[0] - a[0], p[1] - a[1])
	ab = (b[0] - a[0], b[1] - a[1])
	ab = (ab[0] / seg_length, ab[1] / seg_length)
	dot = ab[0]*ap[0] + ab[1]*ap[1]
	return (a[0] + dot*ab[0], a[1] + dot*ab[1])

def segment_intersection(seg1, seg2):
	"""Test whether two segments intersect.
	 
	Segments given as tuple of two points. ((x1, y1), (x2, y2))
	"""
	seg1_len = distance(*seg1)
	seg2_len = distance(*seg2)

	test = lambda seg, seg_len, p: projection_is_on_segment(seg, p, seg_length=seg_len)
	
	return test(seg1, seg1_len, seg2[0]) \
		and test(seg1, seg1_len, seg2[1]) \
		and test(seg2, seg2_len, seg1[0]) \
		and test(seg2, seg2_len, seg1[1])


def line_intersection_point(l1, l2):
	"""Intersection point of two lines, or None if no intersection point.
	
	Lines given as tuple of two points. ((x1, y1), (x2, y2)), but intersection point may be outside that segment.
	"""
	p, q = l1
	A1 = q[1] - p[1]
	B1 = p[0] - q[0]
	C1 = A1*p[0] + B1*p[1]

	p, q = l2
	A2 = q[1] - p[1]
	B2 = p[0] - q[0]
	C2 = A2*p[0] + B2*p[1]

	det = A1*B2 - A2*B1
	min_det = 0.1
	if -min_det < det < min_det:
		return None
	else:
		x = (B2*C1 - B1*C2)/det
		y = (A1*C2 - A2*C1)/det
		return (x, y)


def list_pairs(items):
	"""Generator which yields adjacent pairs of list."""
	if len(items) <= 1:
		return
	prev = items[0]
	for curr in items[1:]:
		yield (prev, curr)
		prev = curr


def cycle_pairs(items):
	"""Generator which yields adjacent pairs of list, followed by one from last item to first."""
	if len(items) <= 1:
		return
	prev = items[0]
	for curr in items[1:]:
		yield (prev, curr)
		prev = curr
	yield (prev, items[0])


def turn_direction(a, b, c):
	ba = (a[0] - b[0], a[1] - b[1])
	bc = (c[0] - b[0], c[1] - b[1])
	return ba[0]*bc[1] - ba[1]*bc[0]


def convex_hull(points):
	points.sort(key=lambda p: p[0])
	upper = []
	upper.append(points[0])
	upper.append(points[1])
	for i in range(2, len(points)):
		p = points[i]
		upper.append(p)
		l = len(upper) - 1
		while (len(upper) > 2) and (turn_direction(upper[l-2], upper[l-1], upper[l]) > 0):
			del upper[l - 1]
			l = len(upper) - 1
	
	points.sort(key=lambda p: -p[0])
	lower = []
	lower.append(points[0])
	lower.append(points[1])
	for i in range(2, len(points)):
		p = points[i]
		lower.append(p)
		l = len(lower) - 1
		while (len(lower) > 2) and (turn_direction(lower[l-2], lower[l-1], lower[l]) > 0):
			del lower[l - 1]
			l = len(lower) - 1

	poly = upper + lower[1:-2]
	return Polygon(poly)
			


class Polygon:
	"""2D Polygon defined by list of vertices."""
	vertices = None # List of (float, float) tuples for vertices of polygon.
	
	def __init__(self, vertices):
		self.vertices = vertices
	
	def clone(self):
		return Polygon(self.vertices[:])
	
	def number_of_vertices(self):
		return len(self.vertices)
	
	def vertices_iter(self):
		"""Iterator over vertices."""
		return iter(self.vertices)
	
	def edges_iter(self):
		"""Iterator over edges. Edge = tuple of adjacent vertices. Includes last edge joining final with first vertex."""
		return cycle_pairs(self.vertices)
		
	def __len__(self):
		return len(self.vertices)
	
	def __getitem__(self, i):
		return self.vertices[i]
	
	def __setitem__(self, i, v):
		self.vertices[i] = v
	
	def __delitem__(self, i):
		del self.vertices[i]
	
	def __iter__(self):
		return self.vertices_iter()
	
	def contains_point(self, p):
		"""Check of pt is inside the polygon. pt is (float, float) tuple."""
		c = False
		for a, b in self.edges_iter():
			if (b[1] > p[1]) != (a[1] > p[1]):
				if p[0] < (a[0]-b[0])*(p[1]-b[1])/(a[1]-b[1]) + p[0]:
					c = not c
		return c

	def is_clockwise(self):
		s = 0
		for a, b in self.edges_iter():
			s += (b[0] - a[0])*(b[1] + a[1])
		return (s > 0)

	def make_clockwise(self):
		if not self.is_clockwise():
			self.vertices.reverse()

	def is_counterclockwise(self):
		return not self.is_clockwise()
		
	def make_counterclockwise(self):
		if not self.is_counterclockwise():
			self.vertices.reverse()
	
	def is_simple(self):
		edges = list(self.edges_iter())
		i = 0
		for e1 in edges:
			i += 1
			for e2 in edges[i:]:
				if (e1[0] == e2[0]) or (e1[0] == e2[1]) or (e1[1] == e2[0]) or (e1[1] == e2[1]):
					continue
				elif segment_intersection(e1, e2):
					return False
		return True

	def area(self):		
		area = 0
		for a, b in self.edges_iter():
			area += (b[0] - a[0])*(b[1] + a[1])
		return abs(area / 2.0)
		
	def contract(self, dist):
		contracted_segments = []
		for a, b in self.edges_iter():
			ab = (b[0] - a[0], b[1] - a[1])
			ap = (ab[1], -ab[0])
			len_ap = math.sqrt(ap[0]**2 + ap[1]**2)
			ap = (dist * ap[0] / len_ap, dist * ap[1] / len_ap)
			p = (a[0] + ap[0], a[1] + ap[1])
			q = (p[0] + ab[0], p[1] + ab[1])
			seg = (p, q)
			contracted_segments.append(seg)
		
		contracted_points = []
		for e, f in cycle_pairs(contracted_segments):
			p = line_intersection_point(e, f)
			if p is not None:
				contracted_points.append(p)
		
		self.vertices = contracted_points

	def expand(self, dist):
		self.contract(-dist)
	
	def center(self):
		x, y = 0.0, 0.0
		for pt in self.vertices:
			x += pt[0]
			y += pt[1]
		n = len(self.vertices)
		if n != 0:
			return (x / n, y / n)
		else:
			return (0, 0)
	
	def bounding_box(self):
		mn = self.vertices[0]
		mx = self.vertices[0]
		for p in self.vertices:
			mn = (min(mn[0], p[0]), min(mn[1], p[1]))
			mx = (max(mx[0], p[0]), max(mx[1], p[1]))
		return (mn, mx)
	
	def point_distance(self, p):
		min_dist_sq = +np.inf
		for edge in self.edges_iter():
			dist_sq = line_to_point_distance_sq(edge, p)
			if dist_sq < min_dist_sq:
				min_dist_sq = dist_sq
		return math.sqrt(min_dist_sq)
	
	def maximal_distance(self):
		max_dist = 0
		for i, p in enumerate(self.vertices):
			for q in self.vertices[i+1:]:
				dist = distance_sq(p, q)
				max_dist = max(max_dist, dist)
		return math.sqrt(max_dist)
