"""Create Dimension Lines between Levels."""

__title__ = 'Dimension\nLevels'

# import libraries and reference the RevitAPI and RevitAPIUI

from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Architecture import *
from Autodesk.Revit.DB.Analysis import *
from Autodesk.Revit.UI import *

from pyrevit import revit, DB
from pyrevit import forms

import msvcrt

# THIS IS NOT NECESSARY, BUT COULD BE HANDY
import clr

# clr.AddReferenceByName("PresentationFramework, Version=3.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35")
# clr.AddReferenceByName("PresentationCore, Version=3.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35")
clr.AddReferenceByPartialName('PresentationCore')
clr.AddReferenceByPartialName("PresentationFramework")
clr.AddReferenceByPartialName('System.Windows.Forms')

from Autodesk.Revit.UI.Selection import *
from Autodesk.Revit.DB import XYZ

from pyrevit import revit, DB

import System.Windows
import Autodesk.Revit.DB


class CustomISelectionFilter(ISelectionFilter):
    def __init__(self, name_cat):
        self.name_cat = name_cat

    def AllowElement(self, e):
        if e.Category.Name == self.name_cat:
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
        levels = uidoc.Selection.PickElementsByRectangle(CustomISelectionFilter("Levels"),
                                           "Select Levels")
    except:
        forms.alert("Failed", ok=True, exitscript=True)


ref_array = DB.ReferenceArray()
s = ""

for lvl in levels:
    if lvl:
        ref_array.Append(lvl.GetPlaneReference())


with revit.Transaction("Dim Grids Sketch Plane", doc=doc):
    origin = active_view.Origin
    direction = active_view.ViewDirection

    plane = DB.Plane.CreateByNormalAndOrigin(direction, origin)
    sp = DB.SketchPlane.Create(doc, plane)

    active_view.SketchPlane = sp
    doc.Regenerate


pick_point = uidoc.Selection.PickPoint()
line = DB.Line.CreateBound(pick_point, pick_point + DB.XYZ.BasisZ * 100)


with revit.Transaction("Dim Grids", doc=doc):
    doc.Create.NewDimension(active_view, line, ref_array)
