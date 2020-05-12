"""Create Dimension Lines between Grids."""

__title__ = 'Dim Levels'

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

with forms.WarningBar(title="Pick grid lines."):
    try:
        grids = uidoc.Selection.PickElementsByRectangle(CustomISelectionFilter("Grids"),
                                           "Select Grids")
    except:
        TaskDialog.Show("Failed", "Yup, failed")

ref_array = ReferenceArray()
s = ""

for gr in grids:
    crv = gr.Curve
    p = crv.GetEndPoint(0)
    q = crv.GetEndPoint(1)
    v = p - q
    up = DB.XYZ.BasisZ
    direction = up.CrossProduct(v)

    opt = DB.Options()
    opt.ComputeReferences = True
    opt.IncludeNonVisibleObjects  = True
    opt.View = active_view
    for obj in gr.get_Geometry(opt):
        s = s + str(type(obj)) + "\n"
        if isinstance(obj, DB.Line):
            ref = obj.Reference
            ref_array.Append(ref)

pick_point = uidoc.Selection.PickPoint()
line = DB.Line.CreateBound(pick_point, pick_point + direction * 100)

with revit.Transaction("Dim Grids", doc=doc):
    doc.Create.NewDimension(active_view, line, ref_array)
