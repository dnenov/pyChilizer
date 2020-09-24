__title__ = "Find nearest\n neighbour"
__doc__ = ""

import re

from pyrevit import revit, DB
from pyrevit.framework import List
from pyrevit import coreutils


def CreateLine(doc, line, dir):
    with revit.Transaction("draw line"):
        plane = DB.Plane.CreateByNormalAndOrigin(dir, line.GetEndPoint(0))
        sketch_plane = DB.SketchPlane.Create(doc, plane)
        curve = doc.Create.NewModelCurve(line, sketch_plane)


def CleanElementIds(_elements, _win, _host_win):
    element_ids = []

    # Skip myself and my parent window host
    for element in elements:
        if element.IntegerValue == _host_win.Id.IntegerValue:
            continue
        if element.IntegerValue == _win.Id.IntegerValue:
            continue
        element_ids.append(element)

    return List[DB.ElementId](element_ids)


def FindSingleIntersection(_win, _host_win, _current_view, _location_pt, _direction):
    # line = DB.Line.CreateBound(_location_pt, _location_pt + 2 * _direction) # Keep for visual debugging
    # CreateLine(revit.doc, line, DB.XYZ(1, 0, 0))  # Keep for visual debugging (change plane dir)

    element_ids = CleanElementIds(elements, _win, _host_win)     # Get the clean list of Ids
    target = DB.FindReferenceTarget.All     # Any intersection for the time being, can test more
    ref_int = DB.ReferenceIntersector(element_ids, target, _current_view)   # The Intersector

    nearest_up = ref_int.FindNearest(_location_pt, _direction)     # Find only the nearest
    shot = nearest_up.GetReference()    # We got a shot! TO DO: Check if no intersection

    # selection = revit.get_selection()
    #
    # element_ids = [shot.ElementId]
    # selection.set_to(element_ids)

    return shot


def PopulateThermalValue(_win, _dir, _intersection):
    cat = revit.doc.GetElement(_intersection).Category
    # if cat.Name == "Walls":
    if cat.Id.IntegerValue == int(DB.BuiltInCategory.OST_Walls):
        value = 1
    else:
        value = 0

    with revit.Transaction("populate parameter"):
        if _dir == "up":
            _win.LookupParameter("ART_ThermalBridgeValue_Top").Set(value)
        elif _dir == "down":
            _win.LookupParameter("ART_ThermalBridgeValue_Bottom").Set(value)
        elif _dir == "left":
            _win.LookupParameter("ART_ThermalBridgeValue_Left").Set(value)
        else:
            _win.LookupParameter("ART_ThermalBridgeValue_Right").Set(value)


def PopulateIntersection(_win, _current_view,):
    bb = _win.get_BoundingBox(_current_view)
    x = _win.Location.Point.X
    y = _win.Location.Point.Y
    location_pt = DB.XYZ(x, y, (bb.Max.Z + bb.Min.Z) * 0.5)

    host_win = _win.SuperComponent  # The root window
    host = host_win.Host    # The wall ultimately hosted; not used now

    direction_up = DB.XYZ(0, 0, 1)
    direction_down = DB.XYZ(0, 0, -1)
    direction_right = _win.HandOrientation.Normalize()
    direction_left = direction_right.Negate()

    up = FindSingleIntersection(_win, host_win, _current_view, location_pt, direction_up)
    down = FindSingleIntersection(_win, host_win, _current_view, location_pt, direction_down)
    left = FindSingleIntersection(_win, host_win, _current_view, location_pt, direction_left)
    right = FindSingleIntersection(_win, host_win, _current_view, location_pt, direction_right)

    PopulateThermalValue(_win, "up", up)
    PopulateThermalValue(_win, "down", down)
    PopulateThermalValue(_win, "left", left)
    PopulateThermalValue(_win, "right", right)


# to do later : create filter if not active 3D view
current_view = revit.active_view

cat_filters = [DB.ElementCategoryFilter(DB.BuiltInCategory.OST_Windows),
               DB.ElementCategoryFilter(DB.BuiltInCategory.OST_Doors),
               DB.ElementCategoryFilter(DB.BuiltInCategory.OST_Walls)]

cat_filter = DB.LogicalOrFilter(List[DB.ElementFilter](cat_filters))

elements = DB.FilteredElementCollector(revit.doc) \
    .WherePasses(cat_filter) \
    .WhereElementIsNotElementType() \
    .ToElementIds()

windows = DB.FilteredElementCollector(revit.doc) \
    .OfCategory(DB.BuiltInCategory.OST_Windows) \
    .WhereElementIsNotElementType() \
    .ToElementIds()

# filter nested by not hosted on wall - MAYBE BETTER FILTER - I think that's great!
# nested_win = [w for w in windows if not isinstance(w.Host, DB.Wall)]
# host_wall = [w.Host for w in windows if isinstance(w.Host, DB.Wall)]

win = revit.pick_element("pick a window") # Keep for visual debugging

# with revit.Transaction("populate parameter"):
    # param = win.LookupParameter("ART_ThermalBridgeValue_Right")
    # param = win.LookupParameter("ART_ThermalBridgeValue_Left")
    # param.Set(7)

PopulateIntersection(win, current_view)

# for win in nested_win:



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
