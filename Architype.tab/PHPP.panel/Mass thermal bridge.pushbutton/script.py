__title__ = "Mass Thermal\n Bridge PHPP"
__doc__ = "Populate the PHPP Thermal Bridge Value parameters for all Windows \nv1.1"

from pyrevit import revit, DB
from pyrevit.framework import List
from pyrevit.forms import ProgressBar


# http://www.revitapidocs.com/2018.1/5da8e3c5-9b49-f942-02fc-7e7783fe8f00.htm
class FamilyLoaderOptionsHandler(DB.IFamilyLoadOptions):
    def OnFamilyFound(self, familyInUse, overwriteParameterValues): #pylint: disable=W0613
        """A method called when the family was found in the target document."""
        return True

    def OnSharedFamilyFound(self,
                            sharedFamily, #pylint: disable=W0613
                            familyInUse, #pylint: disable=W0613
                            source, #pylint: disable=W0613
                            overwriteParameterValues): #pylint: disable=W0613
        source = DB.FamilySource.Family
        overwriteParameterValues = True
        return True


# Creates a model line; used for debugging
def CreateLine(doc, line, dir):
    with revit.Transaction("draw line"):
        plane = DB.Plane.CreateByNormalAndOrigin(dir, line.GetEndPoint(0))
        sketch_plane = DB.SketchPlane.Create(doc, plane)
        curve = doc.Create.NewModelCurve(line, sketch_plane)


# Remove unnecessary IDs from the collection
def CleanElementIds(_elements, _win, _host_win, _doc):
    element_ids = []

    # Skip myself and my parent window host
    for element in _elements:
        if element.IntegerValue == _host_win.Id.IntegerValue and not _doc.IsFamilyDocument:
            continue
        if element.IntegerValue == _win.Id.IntegerValue:
            continue
        element_ids.append(element)

    return List[DB.ElementId](element_ids)


# Find an intersection based on direction
def FindSingleIntersection(_win, _host_win, _elements, _current_view, _location_pt, _direction, _doc):
    # line = DB.Line.CreateBound(_location_pt, _location_pt + 2 * _direction) # Keep for visual debugging
    # CreateLine(_doc, line, DB.XYZ(1, 0, 0))  # Keep for visual debugging (change plane dir)
    try:
        element_ids = CleanElementIds(_elements, _win, _host_win, _doc)     # Get the clean list of Ids

        target = DB.FindReferenceTarget.All     # Any intersection for the time being, can test more
        ref_int = DB.ReferenceIntersector(element_ids, target, _current_view)   # The Intersector
        nearest_up = ref_int.FindNearest(_location_pt, _direction)     # Find only the nearest
        shot = nearest_up.GetReference()    # We got a shot! TO DO: Check if no intersection

        return shot
    except:
        pass


# Populate the PHPP ThermalValue parameter
# TO DO: Handle no parameter - possible UI improvement solution?
def PopulateThermalValue(_win, _dir, _intersection, _doc):
    if not _intersection:
        value = 1
    else:
        cat = _doc.GetElement(_intersection).Category
        # if cat.Name == "Walls":
        if cat.Id.IntegerValue == int(DB.BuiltInCategory.OST_Walls):
            value = 1
        else:
            value = 0

    with DB.Transaction(_doc, "populate parameter") as tr:
        tr.Start()
        if _dir == "up":
            # print(str(_win.Name) + " : " + str(value))
            _win.LookupParameter("ART_ThermalBridgeValue_Top").Set(str(value))
        elif _dir == "down":
            _win.LookupParameter("ART_ThermalBridgeValue_Bottom").Set(str(value))
        elif _dir == "left":
            _win.LookupParameter("ART_ThermalBridgeValue_Left").Set(str(value))
        else:
            _win.LookupParameter("ART_ThermalBridgeValue_Right").Set(str(value))
        tr.Commit()


# Find the intersections for each Window and populate the thermal value
# TO DO: Handle no intersection - Update 26/11/20 handled by assuming value = 1 when no intersection
def PopulateIntersection(_win, _elements, _current_view, _doc):
    bb = _win.get_BoundingBox(_current_view)
    x = _win.Location.Point.X
    y = _win.Location.Point.Y
    location_pt = DB.XYZ(x, y, (bb.Max.Z + bb.Min.Z) * 0.5)

    if _doc.IsFamilyDocument:
        wall = DB.FilteredElementCollector(_doc) \
            .OfCategory(DB.BuiltInCategory.OST_Walls) \
            .WhereElementIsNotElementType() \
            .ToElements()

        host_win = wall[0]
    else:
        host_win = _win.SuperComponent  # The root window

    # host_win = _win.SuperComponent  # The root window

    direction_up = DB.XYZ(0, 0, 1)
    direction_down = DB.XYZ(0, 0, -1)
    direction_left = _win.HandOrientation.Normalize()   # The left will be read from outside-in
    direction_right = direction_left.Negate()

    up = FindSingleIntersection(_win, host_win, _elements, _current_view, location_pt, direction_up, _doc)
    down = FindSingleIntersection(_win, host_win, _elements, _current_view, location_pt, direction_down, _doc)
    left = FindSingleIntersection(_win, host_win, _elements, _current_view, location_pt, direction_left, _doc)
    right = FindSingleIntersection(_win, host_win, _elements, _current_view, location_pt, direction_right, _doc)

    PopulateThermalValue(_win, "up", up, _doc)
    PopulateThermalValue(_win, "down", down, _doc)
    PopulateThermalValue(_win, "left", left, _doc)
    PopulateThermalValue(_win, "right", right, _doc)


def Get3DView(_doc):
    view3d = DB.FilteredElementCollector(_doc) \
        .OfClass(DB.View3D) \
        .ToElements()

    view3d = next(v for v in view3d if v.Name == "View 1")

    return view3d


def ExecuteWindow(_doc):
    # TO DO: create filter if not active 3D view
    current_view = Get3DView(_doc)

    if not isinstance(current_view, DB.View3D):
        print("Please run in 3D view where you can see all Windows")

    cat_filters = [DB.ElementCategoryFilter(DB.BuiltInCategory.OST_Windows),
                   DB.ElementCategoryFilter(DB.BuiltInCategory.OST_Doors),
                   DB.ElementCategoryFilter(DB.BuiltInCategory.OST_Walls)]

    cat_filter = DB.LogicalOrFilter(List[DB.ElementFilter](cat_filters))

    elements = DB.FilteredElementCollector(_doc) \
        .WherePasses(cat_filter) \
        .WhereElementIsNotElementType() \
        .ToElementIds()

    windows = DB.FilteredElementCollector(_doc) \
        .OfCategory(DB.BuiltInCategory.OST_Windows) \
        .WhereElementIsNotElementType() \
        .ToElements()

    # filter nested by not hosted on wall - MAYBE BETTER FILTER
    # this bugs out for some reason on a live project - I added a Type Comment filter, still not good maybe :/
    phpp_win = [w for w in windows if _doc.GetElement(w.GetTypeId()).get_Parameter(
        DB.BuiltInParameter.ALL_MODEL_TYPE_COMMENTS).AsString() == "Panel"]
    nested_win = [w for w in windows if not isinstance(w.Host, DB.Wall)]
    host_wall = [w.Host for w in windows if isinstance(w.Host, DB.Wall)]

    if len(phpp_win) == 0:
        print("No panels with Type Comment = 'Panel' found.")

    # with revit.TransactionGroup('Populate Thermal Bridge Values'):
    #     win = revit.pick_element("pick a window") # Keep for visual debugging
    #     PopulateIntersection(win, elements, current_view)

    counter = 0
    max_value = len(phpp_win)

    elements = [e for e in elements if "Default" not in _doc.GetElement(e).Name]

    with ProgressBar(cancellable=True, step=1) as pb:
        with DB.TransactionGroup(_doc, 'Populate Thermal Bridge Values') as tg:
            tg.Start()
            for win in phpp_win:
                if pb.cancelled:
                    break
                else:
                    PopulateIntersection(win, elements, current_view, _doc)
                    pb.update_progress(counter, max_value)
                    counter += 1
            tg.Assimilate()


selection = revit.get_selection()

for sel in selection:
    fam_ins = sel
    fam = fam_ins.Symbol.Family
    fam_doc = revit.doc.EditFamily(fam)

    ExecuteWindow(fam_doc)

    # print("Is document modifiable? " + str(revit.doc.IsModifiable))
    fam = fam_doc.LoadFamily(revit.doc, FamilyLoaderOptionsHandler())


