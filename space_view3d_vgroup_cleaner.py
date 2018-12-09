# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import bpy

bl_info = {
    "name": "Vertex Group Cleaner",
    "author": "IRIE Shinsuke",
    "version": (0, 7, 0),
    "blender": (2, 80, 0),  # or (2, 79, 0)
    "location": "View3D > Object/Weights/Vertex > Vertex Group Cleaner",
    "description": "Clean vertex groups or delete empty vertex groups in selected objects",
    "tracker_url": "https://github.com/iRi-E/blender_vgroup_cleaner/issues",
    "category": "3D View"}


# clean vertex groups
def zero_verts(obj, grp, th):
    ids = []

    for v in obj.data.vertices:
        try:
            if grp.weight(v.index) <= th:
                ids.append(v.index)
        except RuntimeError:
            pass

    return ids


def remove_verts(obj, grp, ctx):
    ids = zero_verts(obj, grp, ctx.scene.vgroup_cleaner_threshold)

    if ids:
        print("remove %d vertices from vertex group %s" % (len(ids), grp.name))
        grp.remove(ids)

        # toggle edit mode, to force correct drawing
        bpy.ops.object.mode_set(mode="EDIT", toggle=True)
        bpy.ops.object.mode_set(mode="EDIT", toggle=True)


class VGROUP_CLEANER_OT_clean_active_vgroup(bpy.types.Operator):
    """Remove vertices with weight=0 from active vertex group in active object"""
    bl_idname = "vgroup_cleaner.clean_active_vgroup"
    bl_label = "Clean Active Vertex Group"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj.type != 'MESH' or obj not in context.selected_objects:
            self.report({'INFO'}, "Mesh object is not selected")
            return {'CANCELLED'}

        print("Object %s:" % obj.name)
        idx = obj.vertex_groups.active_index
        if idx >= 0:
            remove_verts(obj, obj.vertex_groups[idx], context)

        return {'FINISHED'}


class VGROUP_CLEANER_OT_clean_all_vgroups(bpy.types.Operator):
    """Remove vertices with weight=0 from all vertex groups in all selected objects"""
    bl_idname = "vgroup_cleaner.clean_all_vgroups"
    bl_label = "Clean Vertex Groups"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        objs = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not objs:
            self.report({'INFO'}, "Mesh object is not selected")
            return {'CANCELLED'}

        for obj in objs:
            print("Object %s:" % obj.name)
            for grp in obj.vertex_groups:
                remove_verts(obj, grp, context)

        return {'FINISHED'}


# delete vertex groups
def is_empty(obj, grp):
    for v in obj.data.vertices:
        try:
            grp.weight(v.index)
            return False
        except RuntimeError:
            pass

    return True


def remove_vgrp(obj, grp):
    print("delete vertex group %s" % grp.name)
    obj.vertex_groups.remove(grp)


class VGROUP_CLEANER_OT_delete_empty_vgroups(bpy.types.Operator):
    """Delete empty vertex groups in selected objects"""
    bl_idname = "vgroup_cleaner.delete_empty_vgroups"
    bl_label = "Delete Empty Vertex Groups"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        import re
        re_L = re.compile(r"^(.+[._])([Ll])(\.\d+)?$")
        re_R = re.compile(r"^(.+[._])([Rr])(\.\d+)?$")

        objs = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not objs:
            self.report({'INFO'}, "Mesh object is not selected")
            return {'CANCELLED'}

        for obj in objs:
            print("Object %s:" % obj.name)
            grps_LR = {}

            for grp in obj.vertex_groups:
                m = re_L.match(grp.name)
                if m or re_R.match(grp.name):

                    if m:
                        name_R = m.group(1) + chr(ord(m.group(2)) + 6) + (m.group(3) or "")
                    else:
                        name_R = grp.name

                    if name_R in grps_LR:
                        if is_empty(obj, grp) and is_empty(obj, grps_LR[name_R]):
                            remove_vgrp(obj, grp)
                            remove_vgrp(obj, grps_LR[name_R])
                        del grps_LR[name_R]
                    else:
                        grps_LR[name_R] = grp

                elif is_empty(obj, grp):
                    remove_vgrp(obj, grp)

            for grp in grps_LR.values():
                if is_empty(obj, grp):
                    remove_vgrp(obj, grp)

        return {'FINISHED'}


# clear vertex groups assigned to selected pose bones
class VGROUP_CLEANER_OT_clear_bone_weights(bpy.types.Operator):
    """Remove selected vertices from vertex groups assigned to selected pose bones"""
    bl_idname = "vgroup_cleaner.clear_bone_weights"
    bl_label = "Clear Bone Weights"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj.type != 'MESH' or obj not in context.selected_objects:
            self.report({'INFO'}, "Mesh object is not selected")
            return {'CANCELLED'}

        mode = context.mode
        if mode not in {'EDIT_MESH', 'PAINT_WEIGHT'}:
            self.report({'INFO'}, "Need to be edit mode or weight paint mode")
            return {'CANCELLED'}

        parent = obj.parent
        if not parent or parent.type != 'ARMATURE':
            self.report({'INFO'}, "Mesh object is not parented to armature")
            return {'CANCELLED'}

        print("Object %s:" % obj.name)
        mesh = obj.data

        if mode == "EDIT_MESH":
            bpy.ops.object.mode_set(mode="EDIT", toggle=True)

        for grp in obj.vertex_groups:
            for bone in parent.pose.bones:
                if bone.bone.select and grp.name == bone.name:
                    if mode == "EDIT_MESH" or mesh.use_paint_mask or mesh.use_paint_mask_vertex:
                        igrp = grp.index
                        ids = [v.index for v in mesh.vertices if v.select for g in v.groups if g.group == igrp]
                    else:
                        ids = [v.index for v in mesh.vertices]

                    if ids:
                        print("remove %d vertices from vertex group %s" % (len(ids), grp.name))
                        grp.remove(ids)

        bpy.ops.object.mode_set(mode="EDIT", toggle=True)

        if mode == "PAINT_WEIGHT":
            bpy.ops.object.mode_set(mode="EDIT", toggle=True)

        return {'FINISHED'}


# user interface
class VIEW3D_MT_vgroup_cleaner(bpy.types.Menu):
    bl_label = "Vertex Group Cleaner"

    def draw(self, context):
        layout = self.layout

        if not context.edit_object:
            col = layout.column()
            col.operator("vgroup_cleaner.clean_active_vgroup", text="Clean Active Vertex Group")
            col.operator("vgroup_cleaner.clean_all_vgroups", text="Clean All Vertex Groups")
            col.prop(context.scene, "vgroup_cleaner_threshold", slider=True)

            col.separator()
            col.operator("vgroup_cleaner.delete_empty_vgroups", text="Delete Empty Vertex Groups")

        if context.mode in {"EDIT_MESH", "PAINT_WEIGHT"}:
            col = layout.column()
            parent = context.object.parent
            col.active = parent is not None and parent.type == "ARMATURE"
            col.operator("vgroup_cleaner.clear_bone_weights", text="Clear Bone Weights")


def vgroup_cleaner_menu(self, context):
    layout = self.layout
    layout.separator()
    layout.menu("VIEW3D_MT_vgroup_cleaner", icon="PLUGIN")


# register classes and props
classes = (
    VGROUP_CLEANER_OT_clean_active_vgroup,
    VGROUP_CLEANER_OT_clean_all_vgroups,
    VGROUP_CLEANER_OT_delete_empty_vgroups,
    VGROUP_CLEANER_OT_clear_bone_weights,
    VIEW3D_MT_vgroup_cleaner,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_object.append(vgroup_cleaner_menu)
    bpy.types.VIEW3D_MT_paint_weight.append(vgroup_cleaner_menu)
    bpy.types.VIEW3D_MT_edit_mesh_vertices.append(vgroup_cleaner_menu)

    bpy.types.Scene.vgroup_cleaner_threshold = bpy.props.FloatProperty(
        name="Threshold",
        description="Maximum value of vertex weight that vertices will be removed from vertex group",
        min=0.0,
        soft_max=1.0,
        precision=3,
        default=0.000999)


def unregister():
    del bpy.types.Scene.vgroup_cleaner_threshold

    for cls in classes:
        bpy.utils.unregister_class(cls)
    bpy.types.VIEW3D_MT_object.remove(vgroup_cleaner_menu)
    bpy.types.VIEW3D_MT_paint_weight.remove(vgroup_cleaner_menu)
    bpy.types.VIEW3D_MT_edit_mesh_vertices.remove(vgroup_cleaner_menu)


if __name__ == "__main__":
    register()
