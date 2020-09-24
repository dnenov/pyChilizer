__title__ = "Find \n neighbour"
__doc__ = "Populate the PHPP Thermal Bridge Value parameters for all nested Windows"

#

from pyrevit import revit, DB
from pyrevit.framework import List


# Creates a model line; used for debugging
def CreateLine(doc, line, dir):
    with revit.Transaction("draw line"):
        plane = DB.Plane.CreateByNormalAndOrigin(dir, line.GetEndPoint(0))
        sketch_plane = DB.SketchPlane.Create(doc, plane)
        curve = doc.Create.NewModelCurve(line, sketch_plane)


# Remove unnecessary IDs from the collection
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


# Find an intersection based on direction
def FindSingleIntersection(_win, _host_win, _current_view, _location_pt, _direction):
    # line = DB.Line.CreateBound(_location_pt, _location_pt + 2 * _direction) # Keep for visual debugging
    # CreateLine(revit.doc, line, DB.XYZ(1, 0, 0))  # Keep for visual debugging (change plane dir)

    element_ids = CleanElementIds(elements, _win, _host_win)     # Get the clean list of Ids
    target = DB.FindReferenceTarget.All     # Any intersection for the time being, can test more
    ref_int = DB.ReferenceIntersector(element_ids, target, _current_view)   # The Intersector

    nearest_up = ref_int.FindNearest(_location_pt, _direction)     # Find only the nearest
    shot = nearest_up.GetReference()    # We got a shot! TO DO: Check if no intersection

    return shot


# Populate the PHPP ThermalValue parameter
# TO DO: Handle no parameter - possible UI improvement solution?
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


# Find the intersections for each Window and populate the thermal value
# TO DO: Handle no intersection
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


# TO DO: create filter if not active 3D view
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
    .ToElements()

# filter nested by not hosted on wall - MAYBE BETTER FILTER
nested_win = [w for w in windows if not isinstance(w.Host, DB.Wall)]
host_wall = [w.Host for w in windows if isinstance(w.Host, DB.Wall)]


# win = revit.pick_element("pick a window") # Keep for visual debugging

with revit.TransactionGroup('Populate Thermal Bridge Values'):
    for win in nested_win:
        PopulateIntersection(win, current_view)
