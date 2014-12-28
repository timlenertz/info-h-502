bl_info = {
	'name' : "City Generator",
	'description' : "Generate random city",
	'author' : "Tim Lenertz / Renzhi Deng",
	'location' : "Toolshelf > Create Tab",
	'category' : "Object"	
}

if 'bpy' in locals():
	import imp
	imp.reload(city)
else:
	from . import city

import bpy

class CityGeneratorPanel(bpy.types.Panel):
	bl_label = "City Generator"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_category = "City Generator"

	def draw(self, context):
		row = self.layout.row()
		row.operator('city.generate')


class OBJECT_OT_GenerateCity(bpy.types.Operator):
	bl_idname = 'city.generate'
	bl_label = "Generate"
	bl_description = "Generate city with given parameters."

	def execute(self, context):
		cit = city.City()
		cit.generate()
		city_root = cit.create_blender_object()
		bpy.context.scene.objects.link(city_root)
		return { 'FINISHED' }


def register():
	bpy.utils.register_module(__name__)

def unregister():
	bpy.utils.unregister_module(__name__)