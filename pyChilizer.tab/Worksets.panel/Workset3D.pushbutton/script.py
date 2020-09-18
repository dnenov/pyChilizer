"""Create 3D View for each Workset in the project."""

__title__ = 'Worksets 3D'

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


# set the active Revit application and document
app = __revit__.Application
doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
active_view = doc.ActiveView

def FindViewType(_doc):
    view_family_type = DB.FilteredElementCollector(doc) \
        .OfClass(DB.ViewFamilyType) \

    return next(f for f in view_family_type if f.ViewFamily == DB.ViewFamily.ThreeDimensional)

def


viewtype_id = FindViewType(doc).Id
worksets = DB.FilteredWorksetCollector(doc).OfKind(DB.WorksetKind.UserWorkset)

with revit.Transaction("Create 3D Worksets"):
    for workset in worksets:
        name = workset.Name
        view = DB.View3D.CreateIsometric(doc, viewtype_id)
        view.Name = "WORKSET VIEW - " + name

