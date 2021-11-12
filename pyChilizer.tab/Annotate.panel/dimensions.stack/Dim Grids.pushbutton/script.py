"""Create Dimension Lines between Grids."""

__title__ = 'Dimension\nGrids'


from pyrevit import revit, DB, forms
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
import rpw
from Autodesk.Revit import Exceptions

# set the active Revit application and document
app = __revit__.Application
doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
active_view = doc.ActiveView


# Selection filter for Grids
class GridsFilter(ISelectionFilter):
    def AllowElement(self, e):
        try:
            if e.Category.Name == "Grids":
                return True
            else:
                return False
        except AttributeError:
            return False


active_view = revit.active_view
is_plan = True

if doc.GetElement(active_view.GetTypeId()).FamilyName == 'Floor Plan':
    is_plan = True
else:
    is_plan = False

with forms.WarningBar(title="Pick levels"):
    try:
        levels = uidoc.Selection.PickElementsByRectangle(CustomISelectionFilter("Levels"),
                                           "Select Levels")
    except:
        forms.alert("Failed", ok=True, exitscript=True)


with forms.WarningBar(title="Pick one row of grid lines"):
    try:
        grids = [revit.doc.GetElement(ref) for ref in rpw.revit.uidoc.Selection.PickElementsByRectangle(ObjectType.Element, GridsFilter())]
    except Exceptions.OperationCanceledException:
        forms.alert("Cancelled", ok=True, exitscript=True)

ref_array = DB.ReferenceArray()
#s = ""

for gr in grids:
    crv = gr.Curve
    p = crv.GetEndPoint(0)
    q = crv.GetEndPoint(1)
    v = p - q
    up = DB.XYZ.BasisZ
    direction = up.CrossProduct(v)

    opt = DB.Options()
    opt.ComputeReferences = True
    opt.IncludeNonVisibleObjects = True
    opt.View = active_view

    for obj in gr.get_Geometry(opt):
#        s = s + str(type(obj)) + "\n"
        if isinstance(obj, DB.Line):
            ref = obj.Reference
            ref_array.Append(ref)

if not is_plan:
    with revit.Transaction("Dim Grids Sketch Plane", doc=doc):
        origin = active_view.Origin
        direction = active_view.ViewDirection

        plane = DB.Plane.CreateByNormalAndOrigin(direction, origin)
        sp = DB.SketchPlane.Create(doc, plane)

        active_view.SketchPlane = sp
        doc.Regenerate


with forms.WarningBar(title="Pick Point"):
    try:
        pick_point = revit.uidoc.Selection.PickPoint()
    except Exceptions.OperationCanceledException:
        forms.alert("Cancelled", ok=True, exitscript=True)


if is_plan:
    line = DB.Line.CreateBound(pick_point, pick_point + direction * 100)
else:
    line = DB.Line.CreateBound(pick_point, pick_point + DB.XYZ.BasisX * 100)


with revit.Transaction("Dim Grids", doc=revit.doc):
    revit.doc.Create.NewDimension(active_view, line, ref_array)
