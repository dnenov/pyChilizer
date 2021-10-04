"""Create Dimension Lines between Grids."""

from pyrevit import revit, DB, forms
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
import rpw
from Autodesk.Revit import Exceptions

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

with forms.WarningBar(title="Pick one row of grid lines"):
    try:
        grids = [revit.doc.GetElement(ref) for ref in rpw.revit.uidoc.Selection.PickObjects(ObjectType.Element, GridsFilter())]
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

with forms.WarningBar(title="Pick Point"):
    try:
        pick_point = revit.uidoc.Selection.PickPoint()
    except Exceptions.OperationCanceledException:
        forms.alert("Cancelled", ok=True, exitscript=True)
line = DB.Line.CreateBound(pick_point, pick_point + direction * 100)

with revit.Transaction("Dim Grids", doc=revit.doc):
    revit.doc.Create.NewDimension(active_view, line, ref_array)
