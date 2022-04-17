from pyrevit import revit, DB, forms, script
from rpw.ui.forms import (FlexForm, Label, ComboBox, Separator, Button, TextBox)
from Autodesk.Revit import Exceptions
import rpw
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
import sys


def get_name(el):
    return DB.Element.Name.__get__(el)


def containment(poly, pt):
    # Copyright(c) 2017, Dimitar Venkov
    # @5devene, dimitar.ven@gmail.com
    # www.badmonkeys.net
    def testCCW(A, B, C):
        return (B.X - A.X) * (C.Y - A.Y) > (B.Y - A.Y) * (C.X - A.X)

    wn = 0
    ln1 = len(poly)
    for i in xrange(ln1):
        j = (i + 1) % ln1
        isCCW = testCCW(poly[i], poly[j], pt)
        if poly[i].Y <= pt.Y:
            if poly[j].Y > pt.Y and isCCW: wn += 1
        else:
            if poly[j].Y <= pt.Y and not isCCW: wn -= 1

    return wn != 0

#todo: filter by area type
class CatFilter(ISelectionFilter):
    def __init__(self, cat):
        self.cat = cat

    def AllowElement(self, elem):
        try:
            if elem.Category.Id.IntegerValue == int(self.cat):
                return True
            else:
                return False
        except AttributeError:
            return False

    def AllowReference(self, reference):
        try:
            if isinstance(revit.doc.GetElement(reference), self.cat):
                return True
            else:
                return False
        except AttributeError:
            return False


def select_with_cat_filter(cat, message):

    # select elements while applying category filter
    try:
        with forms.WarningBar(title=message):
            selection = [revit.doc.GetElement(reference) for reference in rpw.revit.uidoc.Selection.PickObjects(
                ObjectType.Element, CatFilter(cat=cat))]
    except Exceptions.OperationCanceledException:
        forms.alert("Cancelled", ok=True, warn_icon=False, exitscript=True)
    if not selection:
        forms.alert("You need to select at least one element.", exitscript=True)
    return selection


def param_set_by_cat(cat, doc=revit.doc, storage_type="String", type_param = False):
    # get all project type parameters of a given category
    # can be used to gather parameters for UI selection
    if type_param:
        any_el = DB.FilteredElementCollector(doc).OfCategory(cat).WhereElementIsElementType().FirstElement()
    else:
        any_el = DB.FilteredElementCollector(doc).OfCategory(cat).WhereElementIsNotElementType().FirstElement()
    parameter_set = []

    params = any_el.Parameters
    for p in params:
        if p not in parameter_set and p.IsReadOnly == False and p.StorageType.ToString()== storage_type:
            parameter_set.append(p)
    return parameter_set


link_cat = DB.BuiltInCategory.OST_RvtLinks

components1 = [
    Label("Where are the Areas located?"),
    ComboBox(name="areas_loc", options=["Main Model", "Link"]),
    Button("Select")
]
form1 = FlexForm("Select Model", components1)
ok1 = form1.show()
if ok1:
    areas_loc = form1.values["areas_loc"]
else:
    sys.exit()

if areas_loc == "Main Model":
    areas_model = revit.doc
else:
    areas_model = select_with_cat_filter(link_cat, "Select Revit Link with Areas")[0].GetLinkDocument()


# link = select_with_cat_filter(link_cat, "Select Revit Link with Areas")[0].GetLinkDocument()

areas = DB.FilteredElementCollector(areas_model).OfCategory(DB.BuiltInCategory.OST_Areas).ToElements()

GIA_areas = [a for a in areas if a.AreaScheme.Name == "GIA"]
rooms = DB.FilteredElementCollector(revit.doc).OfCategory(DB.BuiltInCategory.OST_Rooms).ToElements()
# print ("Debug: picked up {} areas".format(len(areas)))

area_param_set = param_set_by_cat(DB.BuiltInCategory.OST_Areas, doc=areas_model)
room_param_set = param_set_by_cat(DB.BuiltInCategory.OST_Rooms)


area_param_names = [p.Definition.Name for p in area_param_set]
room_param_names = [p.Definition.Name for p in room_param_set]

components2 = [
    Label("[Areas] Pick parameter to copy value From:"),
    ComboBox(name="areas_param", options=area_param_names),
    Label("[Rooms] Pick parameter to copy value To:"),
    ComboBox(name="rooms_param", options=room_param_names),
    Button("Select")
]

form2 = FlexForm("Match params", components2)
ok2=form2.show()
if ok2:
    area_param = form2.values["areas_param"]
    room_param = form2.values["rooms_param"]
else:
    sys.exit()


with revit.Transaction("Cross Areas and Rooms",revit.doc):
    opts = DB.SpatialElementBoundaryOptions()
    for a in GIA_areas:
        area_name = get_name(a)
        copy_param_value = a.LookupParameter(area_param).AsString()
        list_bnd_segments= a.GetBoundarySegments(opts)

        area_elev = a.Level.Elevation
        for lst in list_bnd_segments:
            poly_pts = [c.GetCurve().GetEndPoint(0) for c in lst]
            # print (area_boundary)


            for r in rooms:
                if r.Location:
                    p = r.Location.Point
                    if round(p.Z, 2) == round(area_elev, 2):
                        if containment(poly_pts, p):
                        # print("Area Elevation {}       Room {}".format(area_elev, p.Z))
                            r.LookupParameter(room_param).Set(str(copy_param_value))

