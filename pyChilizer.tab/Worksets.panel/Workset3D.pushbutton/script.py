"""Create 3D View for each Workset in the project."""

__title__ = 'Worksets\nChecker'

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
# clr.AddReferenceByPartialName('PresentationCore')
# clr.AddReferenceByPartialName("PresentationFramework")
# clr.AddReferenceByPartialName('System.Windows.Forms')
#
# from Autodesk.Revit.UI.Selection import *
# from Autodesk.Revit.DB import XYZ

from pyrevit import revit, DB, forms

# import System.Windows
# import Autodesk.Revit.DB


# set the active Revit application and document
app = __revit__.Application
doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
active_view = doc.ActiveView


# Find us a 3D View to create
def FindViewType(_doc):
    view_family_type = DB.FilteredElementCollector(doc) \
        .OfClass(DB.ViewFamilyType) \

    return next(f for f in view_family_type if f.ViewFamily == DB.ViewFamily.ThreeDimensional)


# Set Workset Visibility based on current Workset
def SetWorksetVisibility(view, workset):
    worksets = DB.FilteredWorksetCollector(doc).OfKind(DB.WorksetKind.UserWorkset)
    for work in worksets:
        if work.Name == workset.Name:
            view.SetWorksetVisibility(work.Id, DB.WorksetVisibility.Visible)
        else:
            view.SetWorksetVisibility(work.Id, DB.WorksetVisibility.Hidden)


# Remove ViewTempalte assinged to ViewType
def RemoveViewTemplate(viewtype_id):
    view_type = doc.GetElement(viewtype_id)
    template_id = view_type.DefaultTemplateId
    if template_id.IntegerValue != -1:
        if forms.alert("You are about to remove the ViewTempalte associated with this View Type. Is that cool with ya?",
                    ok=False, yes=True, no=True, exitscript=True):
            with revit.Transaction("Remove ViewTemplate"):
                view_type.DefaultTemplateId = DB.ElementId(-1)


# Delete existing views based on workset naming
def DeleteExistingView(views, worksets):
    with revit.Transaction("Delete existing views"):
        for view in views:
            for workset in worksets:
                name = "WORKSET VIEW - " + workset.Name
                if view.Name == name:
                    try:
                        doc.Delete(view.Id)
                        break
                    except:
                        forms.alert('Current view was cannot be deleted. Close view and try again.')
                        return False
    return True


if forms.check_workshared(doc, 'Model is not workshared.'):
    viewtype_id = FindViewType(doc).Id
    worksets = DB.FilteredWorksetCollector(doc).OfKind(DB.WorksetKind.UserWorkset)
    views = DB.FilteredElementCollector(doc).OfClass(DB.View).ToElements()

    # Check if the view type found has ViewTemplate associated with it
    # A ViewTemplate will prevent the assignment of correct Workset settings
    RemoveViewTemplate(viewtype_id)

    # Delete all previous Workset views
    # In case the user has opened one of them, warn them and do not execute
    if DeleteExistingView(views, worksets):
        with revit.Transaction("Create 3D Worksets"):
            for workset in worksets:
                name = workset.Name
                view = DB.View3D.CreateIsometric(doc, viewtype_id)
                view.Name = "WORKSET VIEW - " + name
                SetWorksetVisibility(view, workset)
        forms.alert('Successfully created Workset Views')
