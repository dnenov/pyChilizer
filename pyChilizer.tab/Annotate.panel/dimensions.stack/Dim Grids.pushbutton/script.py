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

# Selection Filter
class CustomISelectionFilter(ISelectionFilter):
    def __init__(self, cat):
        self.cat = cat

    def AllowElement(self, e):
        if e.Category.Id.IntegerValue == int(self.cat):
            return True
        else:
            return False

    @staticmethod
    def AllowReference(ref, point):
        return True
        

active_view = revit.active_view # the current active view
is_plan = True  # Separate condition if the view is a Plan View or Elevetaion/Section

if doc.GetElement(active_view.GetTypeId()).FamilyName == 'Floor Plan':
    is_plan = True
else:
    is_plan = False


with forms.WarningBar(title="Pick one row of grid lines"):
    try:
        grids = uidoc.Selection.PickElementsByRectangle(CustomISelectionFilter(DB.BuiltInCategory.OST_Grids), 
        "Select Grids")
    except Exceptions.OperationCanceledException:
        forms.alert("Cancelled", ok=True, exitscript=True)

# Terminate early if no grids were selected
if not grids:
    forms.alert("No grids selected.", ok=True, exitscript=True)

# Container for the reference lines
ref_array = DB.ReferenceArray()

# Grab all geometrical reference lines to dimension to
for gr in grids:
    if gr.IsCurved: 
        continue
    # Obtaining reference with the below code works for all grid types https://autode.sk/3cJLY1a
    ref = DB.Reference.ParseFromStableRepresentation(doc, gr.UniqueId)
    ref_array.Append(ref)
    crv = gr.Curve
    p = crv.GetEndPoint(0)
    q = crv.GetEndPoint(1)
    v = p - q
    up = DB.XYZ.BasisZ
    direction = up.CrossProduct(v)

# Condion: Elevation/Section
if not is_plan:
    with revit.Transaction("Dim Grids Sketch Plane", doc=doc):
        origin = active_view.Origin
        direction = active_view.ViewDirection

        plane = DB.Plane.CreateByNormalAndOrigin(direction, origin)
        sp = DB.SketchPlane.Create(doc, plane)

        active_view.SketchPlane = sp
        doc.Regenerate

# Pick the placement point
with forms.WarningBar(title="Pick Point"):
    try:
        pick_point = revit.uidoc.Selection.PickPoint()
    except Exceptions.OperationCanceledException:
        forms.alert("Cancelled", ok=True, exitscript=True)

# Create the dim line
if is_plan:
    line = DB.Line.CreateBound(pick_point, pick_point + direction * 100)
else:
    line = DB.Line.CreateBound(pick_point, pick_point + DB.XYZ.BasisX * 100)

# Finally, create the dimension
with revit.Transaction("Dim Grids", doc=revit.doc):
    revit.doc.Create.NewDimension(active_view, line, ref_array)
