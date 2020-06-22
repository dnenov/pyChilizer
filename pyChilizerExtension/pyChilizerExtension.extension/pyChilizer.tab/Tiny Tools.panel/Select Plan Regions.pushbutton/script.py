__title__="Select \nPlan Region\nin current view"


from System.Collections.Generic import List

import Autodesk.Revit.DB as DB
import clr
from collections import defaultdict

from pyrevit import revit, DB
from pyrevit import script

from pyrevit import forms

from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, BuiltInParameter

#note: to add multi view option

plan_regions = DB.FilteredElementCollector(revit.doc, revit.active_view.Id) \
    .OfCategory(DB.BuiltInCategory.OST_PlanRegion) \
    .WhereElementIsNotElementType() \
    .ToElementIds()

revit.get_selection().set_to(plan_regions)



