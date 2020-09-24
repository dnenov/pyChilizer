__title__ = "Find nearest\n neighbour"
__doc__ = ""


from itertools import izip
from pyrevit import revit, DB, script, forms, HOST_APP
from time import time

import math

from pyrevit import HOST_APP
from pyrevit import revit, DB


def CreateLine(doc, line):
    with revit.Transaction("draw line"):
        plane = DB.Plane.CreateByNormalAndOrigin(DB.XYZ(0,0,1), line.GetEndPoint(0))
        sketch_plane = DB.SketchPlane.Create(doc, plane)
        curve = doc.Create.NewModelCurve(line, sketch_plane)


# to do later : create filter if not active 3D view
curview = revit.active_view

# collect all windows instances
windows = DB.FilteredElementCollector(revit.doc) \
    .OfCategory(DB.BuiltInCategory.OST_Windows) \
    .WhereElementIsNotElementType() \
    .ToElements()

# filter nested by not hosted on wall - MAYBE BETTER FILTER
#nested_win = [w for w in windows if not isinstance(w.Host, DB.Wall)]
#host_wall = [w.Host for w in windows if isinstance(w.Host, DB.Wall)]

#wall_curve = host_wall[0].Location
#wall_centerplane = DB.XYZ(wall_curve.Curve.GetEndPoint(0).X, wall_curve.Curve.GetEndPoint(0).Z, 1500 )

win = revit.pick_element("pick a window")

# win = revit.doc.GetElement(revit.pick_element("pick a window").Id)

fam_filter = DB.ElementClassFilter(DB.FamilyInstance)
wall_filter = DB.ElementClassFilter(DB.Wall)

class_filter = DB.LogicalAndFilter(fam_filter, wall_filter)

target = DB.FindReferenceTarget.Face
ref_int = DB.ReferenceIntersector(class_filter, target, curview)

bb = win.get_BoundingBox(curview)
x = win.Location.Point.X
y = win.Location.Point.Y
location_pt = DB.XYZ(x, y, (bb.Max.Z + bb.Min.Z)*0.5)

rotation = win.Location.Rotation
host = win.SuperComponent.Host
direction = host.Location.Curve.Direction

# print(str(rotation * 180/3.14))
# print(str(host.Id))

facing = win.FacingOrientation
direction_down = DB.XYZ(0, 0, -1)
direction_up = DB.XYZ(0, 0, 1)
direction_right = win.HandOrientation.Normalize()
direction_left = direction_right.Negate()

# print(str(facing.AngleTo(direction_left)))

line = DB.Line.CreateBound(location_pt, location_pt + 2*direction_left)
CreateLine(revit.doc, line)

# nearest_up = ref_int.Find(location_pt, direction_up)
# ups = []
# try:
#     for nu in set(nearest_up):
#         i_up = revit.doc.GetElement(nu.GetReference())
#         ups.append(i_up)
#         print("UP      {0}, Element Id: {1}".format(i_up.Name, i_up.Id))
# except:
#     pass
#
# nearest_down = ref_int.Find(location_pt, direction_down)
# downs = []
# try:
#     for nd in set(nearest_down):
#         i_dn = revit.doc.GetElement(nd.GetReference())
#         nd.append(i_dn)
#         print("DOWN: {0}, Element Id: {1}".format(i_dn.Name, i_dn.Id))
# except:
#     pass

# ref = ref_context.GetReference()
#
# selection = revit.get_selection()
# selection.set_to(list(ref))

# for win in nested_win:
#
#     print ("Intersecting family type name: {0} Element Id {1}".format(win.Name, win.Id))
#
#     class_filter = DB.ElementClassFilter(DB.FamilyInstance)
#     target = DB.FindReferenceTarget.Face
#     ref_int = DB.ReferenceIntersector(class_filter, target, curview)
#
#     bb = win.get_BoundingBox(curview)
#     x = win.Location.Point.X
#     y = win.Location.Point.Y
#     location_pt = DB.XYZ(x, y, bb.Max.Z)
#
#     direction_down = DB.XYZ(0, 0, -1)
#     direction_up = DB.XYZ(0, 0, 1)
#
#     nearest_up = ref_int.Find(location_pt, direction_up)
#     ups = []
#     try:
#         for nu in set(nearest_up):
#             i_up = revit.doc.GetElement(nu.GetReference())
#             ups.append(i_up)
#             print("UP      {0}, Element Id: {1}".format(i_up.Name, i_up.Id))
#     except:
#         pass
#
#     nearest_down = ref_int.Find(location_pt, direction_down)
#     downs = []
#     try:
#         for nd in set(nearest_down):
#             i_dn = revit.doc.GetElement(nd.GetReference())
#             nd.append(i_dn)
#             print("DOWN: {0}, Element Id: {1}".format(i_dn.Name, i_dn.Id))
#     except:
#         pass


    # illustrate with line
#    line = DB.Line.CreateBound(bb.Max, direction)

#    x = bb.Max.X
##    y = bb.Min.Y
#    z = bb.Max.Z

#    normal = DB.XYZ(x,y,z)

 #   origin = center

#    with revit.Transaction("draw line"):
#        plane = DB.Plane.CreateByNormalAndOrigin(normal, origin)
#        sketch_plane = DB.SketchPlane.Create(revit.doc, plane)
 #       model_line = revit.doc.Create.NewModelCurve(line, sketch_plane)
