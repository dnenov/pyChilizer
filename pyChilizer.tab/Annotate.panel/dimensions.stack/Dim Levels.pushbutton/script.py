"""Create Dimension Lines between Levels."""

__title__ = 'Dimension\nLevels'


from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Architecture import *
from Autodesk.Revit.DB.Analysis import *
from Autodesk.Revit.UI import *

from pyrevit import revit, DB
from pyrevit import forms
from pyrevit.compat import get_elementid_value_func

from Autodesk.Revit.UI.Selection import *
from Autodesk.Revit.DB import XYZ

from pyrevit import revit, DB

get_elementid_value = get_elementid_value_func()

# Selection Filter
class CustomISelectionFilter(ISelectionFilter):
    def __init__(self, cat):
        self.cat = cat

    def AllowElement(self, e):
        if get_elementid_value(e.Category.Id) == int(self.cat):
            return True
        else:
            return False

    @staticmethod
    def AllowReference(ref, point):
        return True


# set the active Revit application and document
app = __revit__.Application
doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
active_view = doc.ActiveView

with forms.WarningBar(title="Pick levels"):
    try:
        levels = uidoc.Selection.PickElementsByRectangle(CustomISelectionFilter(DB.BuiltInCategory.OST_Levels),
                                           "Select Levels")
    except:
        forms.alert("Failed", ok=True, exitscript=True)

ref_array = DB.ReferenceArray()
s = ""

# Terminate early if no levels were selected
if not levels:
    forms.alert("No grids selected.", ok=True, exitscript=True)

# Get all geometry reference lines
for lvl in levels:
    if lvl:
        ref_array.Append(lvl.GetPlaneReference())

# Create a sketch plane to draw the dimensions in
with revit.Transaction("Dim Grids Sketch Plane", doc=doc):
    origin = active_view.Origin
    direction = active_view.ViewDirection

    plane = DB.Plane.CreateByNormalAndOrigin(direction, origin)
    sp = DB.SketchPlane.Create(doc, plane)

    active_view.SketchPlane = sp
    doc.Regenerate

# Get the placement point and dim line
pick_point = uidoc.Selection.PickPoint()
line = DB.Line.CreateBound(pick_point, pick_point + DB.XYZ.BasisZ * 100)

# Finally, create the dimension
with revit.Transaction("Dim Grids", doc=doc):
    doc.Create.NewDimension(active_view, line, ref_array)
