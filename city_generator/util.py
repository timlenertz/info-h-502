import math
import networkx as nx


def line_to_point_dist_sq(line, p):
	a, b = line
	num = ( (b[1] - a[1])*p[0] - (b[0] - a[0])*p[1] + b[0]*a[1] - b[1]*a[0] )**2
	den = (b[1] - a[1])**2 + (b[0] - a[0])**2
	return num / den

def line_to_point_dist(line, p):
	return math.sqrt(line_to_point_dist_sq(line, p))

def distance_sq(a, b):
	return (a[0] - b[0])**2 + (a[1] - b[1])**2

def distance(a, b):
	return math.sqrt(distance_sq(a, b))
	
def projection_is_on_segment(seg, p, seg_length=None):
	if seg_length is None:
		seg_length = distance(*seg)
	a, b = seg
	ap = (p[0] - a[0], p[1] - a[1])
	ab = (b[0] - a[0], b[1] - a[1])
	ab = (ab[0] / seg_length, ab[1] / seg_length)
	dot = ab[0]*ap[0] + ab[1]*ap[1]
	return (dot > 0) and (dot < seg_length)

def project_on_segment(seg, p):
	a, b = seg
	seg_length = distance(*seg)
	ap = (p[0] - a[0], p[1] - a[1])
	ab = (b[0] - a[0], b[1] - a[1])
	ab = (ab[0] / seg_length, ab[1] / seg_length)
	dot = ab[0]*ap[0] + ab[1]*ap[1]
	return (a[0] + dot*ab[0], a[1] + dot*ab[1])

def segment_intersection(seg1, seg2):
	seg1_len = distance(*seg1)
	seg2_len = distance(*seg2)

	test = lambda seg, seg_len, p: projection_is_on_segment(seg, p, seg_length=seg_len)
	
	return test(seg1, seg1_len, seg2[0]) and test(seg1, seg1_len, seg2[1]) and test(seg2, seg2_len, seg1[0]) and test(seg2, seg2_len, seg1[1])


def line_intersection_point(l1, l2):
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


def point_inside_polygon(poly, p):
	c = False
	for edge in poly:
		a, b = edge
		if (b[1] > p[1]) != (a[1] > p[1]):
			if p[0] < (a[0]-b[0])*(p[1]-b[1])/(a[1]-b[1]) + p[0]:
				c = not c
	return c


def polygon_is_clockwise(poly):
	s = 0
	for a, b in cycle_pairs(poly):
		s += (b[0] - a[0])*(b[1] + a[1])
	return (s > 0)


def polygon_is_simple(poly):
	edges = list(cycle_pairs(poly))
	i = 0
	for e1 in edges:
		i += 1
		for e2 in edges[i:]:
			if (e1[0] == e2[0]) or (e1[0] == e2[1]) or (e1[1] == e2[0]) or (e1[1] == e2[1]):
				continue
			elif segment_intersection(e1, e2):
				return False
	return True


def cycle_pairs(items):
	if len(items) <= 1:
		return
	prev = items[0]
	for curr in items[1:]:
		yield (prev, curr)
		prev = curr
	yield (prev, items[0])
	
	
def polygon_area(poly):
	area = 0
	for a, b in cycle_pairs(poly):
		area += (b[0] - a[0])*(b[1] + a[1])
	return abs(area / 2.0)