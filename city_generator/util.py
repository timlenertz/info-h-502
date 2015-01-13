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


def point_inside_polygon(poly, p):
	c = False
	for edge in poly:
		a, b = edge
		if (b[1] > p[1]) != (a[1] > p[1]):
			if p[0] < (a[0]-b[0])*(p[1]-b[1])/(a[1]-b[1]) + p[0]:
				c = not c
	return c