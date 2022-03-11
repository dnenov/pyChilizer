"""Allows you to quickly renubmer the Viewports on a Sheet by the order of selection."""

__title__ = 'Renumber\nViewports'

#import libraries and reference the RevitAPI and RevitAPIUI
from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Architecture import *
from Autodesk.Revit.DB.Analysis import *
from Autodesk.Revit.UI import *

from pyrevit import revit, DB
from pyrevit import forms

from pyrevit import coreutils

import msvcrt

#THIS IS NOT NECESSARY, BUT COULD BE HANDY
import clr
clr.AddReferenceByPartialName('PresentationCore')
clr.AddReferenceByPartialName("PresentationFramework")
clr.AddReferenceByPartialName('System.Windows.Forms')

import System.Windows

#set the active Revit application and document
app = __revit__.Application
doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
active_view = doc.ActiveView

vsheet = active_view;

# Check if we are on a Sheet
if vsheet.ViewType != DB.ViewType.DrawingSheet:
    forms.alert("You're not on a Sheet. You need to be on a Sheet to use this command.",
                exitscript=True)

# Get all viewports of the current Sheet
vport_element_ids = vsheet.GetAllViewports()
vports = []

for vp_id in vport_element_ids:
	vports.Add(doc.GetElement(vp_id))

counter = 0
carry = ''

# Keep renumbering until you escape
# TO DO: Fix it for silly inputs - always renumber from (00)1
try:
    while True:
        counter += 1
        finished = False
        selection_element = revit.pick_element_by_category(DB.BuiltInCategory.OST_Viewports, 'Pick Viewport') # select a viewport       
        detail_number = selection_element.LookupParameter("Detail Number") # take it's detail number parameter

        with revit.Transaction("Renumber", doc=doc):
            # check if the desired detail number is already in use
            for vp in vports:
                cur_vp_param = vp.LookupParameter("Detail Number")
                cur_vp = str(cur_vp_param.AsString())
                # if it is, make a swap and set it out
                # mark as finished so we don't do it again
                if cur_vp == str(counter):         
                    carry = str(detail_number.AsString())
                    detail_number.Set("99")
                    cur_vp_param.Set(carry)
                    detail_number.Set(str(counter))
                    finished = True
            if not finished:
                # if we didn't find a duplicate, just set it up
                detail_number.Set(str(counter))
except:   
    pass

