"""Allows you to quickly renubmer the Viewports on a Sheet by the order of selection."""

__title__ = 'Renumber\nViewports'

#import libraries and reference the RevitAPI and RevitAPIUI

from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Architecture import *
from Autodesk.Revit.DB.Analysis import *
from Autodesk.Revit.UI import *

from pyrevit import revit, DB
from pyrevit import forms

import msvcrt

#THIS IS NOT NECESSARY, BUT COULD BE HANDY
import clr
# clr.AddReferenceByName("PresentationFramework, Version=3.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35")
# clr.AddReferenceByName("PresentationCore, Version=3.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35")
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

#if isinstance(vsheet, None):
if vsheet is None:
    forms.alert("You're not on a Sheet. You need to be on a Sheet to use this command.",
                exitscript=True)

vport_element_ids = vsheet.GetAllViewports()

vports = []

for vp_id in vport_element_ids:
	vports.Add(doc.GetElement(vp_id))

counter = 0
carry = ''

try:
    while True:
        counter += 1
        selection_element = revit.pick_element('Anything')        
        detail_number = selection_element.LookupParameter("Detail Number")

        with revit.Transaction("Toggle", doc=doc):
            for vp in vports:
                cur_vp_param = vp.LookupParameter("Detail Number")
                cur_vp = str(cur_vp_param.AsString())
                if cur_vp == str(counter):
                    carry = str(detail_number.AsString())
                    detail_number.Set("99")
                    cur_vp_param.Set(carry)
                    detail_number.Set(str(counter))
except:    
    TaskDialog.Show('Test', 'Done')
    pass

# TaskDialog.Show('Test', str(len(vports)))
