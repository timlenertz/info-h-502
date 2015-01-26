bl_info = {
	'name' : "City Generator",
	'description' : "Generate random city",
	'author' : "Tim Lenertz / Renzhi Deng",
	'location' : "Toolshelf > Create Tab",
	'category' : "Object"	
}

import imp
import math
import random

if 'bpy' in locals():
	import imp
	imp.reload(city)
	imp.reload(terrain)
	imp.reload(assets)
	imp.reload(citycell)
	imp.reload(util)
	imp.reload(mcb)
	imp.reload(block)
	imp.reload(building)
else:
	from . import city, terrain, assets, citycell, util, mcb, block, building
	import bpy


bpy.types.Scene.city_name = bpy.props.StringProperty(
	name="Name",
	description="Name of root object for city",
	default="City",
)

bpy.types.Scene.seed = bpy.props.StringProperty(
	name="Random Seed",
	description="Seed for random number generation (empty for random)",
	default="",
)

bpy.types.Scene.terrain_initial_height_max = bpy.props.FloatProperty(
	name="Corner Elevation",
	description="Maximal Z coordinate for city corner",
	default=0.0,
	soft_min=0.0,
	soft_max=10,
	subtype='DISTANCE',
	unit='LENGTH'
)

bpy.types.Scene.terrain_side_length = bpy.props.FloatProperty(
	name="Size",
	description="Side length of city.",
	default=1000.0,
	subtype='NONE',
	unit='AREA'
)

bpy.types.Scene.terrain_height = bpy.props.FloatProperty(
	name="Elevation",
	description="Multiplier for terrain elevation",
	default=10.0,
	soft_min=1.0,
	soft_max=250.0,
	subtype='FACTOR',
	unit='NONE'
)


bpy.types.Scene.plan_intersections = bpy.props.IntProperty(
	name="Junctions",
	description="Approximate number of primary street intersections",
	default=25,
	min=5,
	max=200,
	subtype='NONE'
)

bpy.types.Scene.plan_intersection_deviation = bpy.props.FloatProperty(
	name="Grid Alignment",
	description="Controls how much primary street intersection positions deviate from regular grid layout. Smaller value corresponds to greater deviation.",
	default=4.0,
	min=1.0,
	max=30.0,
	subtype='FACTOR'
)


bpy.types.Scene.urbanization = bpy.props.FloatProperty(
	name="Urbanization",
	description="The higher the value, the more urbanized the city becomes.",
	default=0.5,
	min=0.0,
	max=1.0,
	subtype='FACTOR',
	unit='NONE'
)

        
class CityGeneratorPanel(bpy.types.Panel):
	bl_label = "City Generator"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_category = "City Generator"

	def draw(self, context):
		layout = self.layout
		scene = context.scene
		
		layout.prop(scene, 'city_name')
		layout.prop(scene, 'seed')
		
		box = layout.box()
		box.label("Terrain")
		box.prop(scene, 'terrain_roughness')
		box.prop(scene, 'terrain_resolution')
		box.prop(scene, 'terrain_initial_height_max')
		box.prop(scene, 'terrain_side_length')
		box.prop(scene, 'terrain_height')
		
		box = layout.box()
		box.label("Primary Roads")
		box.prop(scene, 'plan_intersections')
		box.prop(scene, 'plan_intersection_deviation')
		
		box = layout.box()
		box.label("Features")
		box.prop(scene, 'urbanization')

			
		layout.operator('city.generate')
		layout.operator('city.delete')


class OBJECT_OT_GenerateCity(bpy.types.Operator):
	bl_idname = 'city.generate'
	bl_label = "Generate new city"
	bl_description = "Generate city with given parameters."
		
	def execute(self, context):	
		scene = context.scene

		if scene.seed != "":
			random.seed(int(scene.seed))
	
		cit = city.City()
		cit.terrain.initial_height_range = (
			0.0,
			scene.terrain_initial_height_max
		)
		cit.terrain.side_length = scene.terrain_side_length
		cit.terrain.elevation = scene.terrain_height
		cit.approximate_number_of_intersection_points = scene.plan_intersections
		cit.edges_deviation = scene.plan_intersection_deviation
		cit.urbanization = scene.urbanization
		
		cit.generate()
		city_root = cit.create_blender_object(scene.city_name)
		city_root.scale = (0.1, 0.1, 0.1)
		bpy.context.scene.objects.link(city_root)
				
		return { 'FINISHED' }


class OBJECT_OT_DeleteCity(bpy.types.Operator):
	bl_idname = 'city.delete'
	bl_label = "Delete city"
	bl_description = "Delete city with the given name."
	
	def execute(self, context):
		if context.scene.city_name in bpy.data.objects:
			city = bpy.data.objects.get(context.scene.city_name)
			bpy.ops.object.select_all(action='DESELECT')
			bpy.context.scene.objects.active = city
			city.select = True
			bpy.ops.object.select_grouped(type='CHILDREN_RECURSIVE', extend=True)
			#bpy.ops.object.select_hierarchy(direction='CHILD', extend=True)
			bpy.ops.object.delete(use_global=False)
		
		return { 'FINISHED' }



def register():
	bpy.utils.register_module(__name__)

def unregister():
	bpy.utils.unregister_module(__name__)