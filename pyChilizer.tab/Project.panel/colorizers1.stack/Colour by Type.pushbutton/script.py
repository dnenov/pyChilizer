from collections import defaultdict
from pyrevit import HOST_APP
from pyrevit import forms
from pyrevit import revit, DB
from pyrevit import script
import random
import inviewconfig
from pychilizer import database
from pychilizer import colorize

logger = script.get_logger()
BIC = DB.BuiltInCategory
doc = revit.doc
view = revit.active_view
overrides_option = inviewconfig.get_config()
solid_fill_pattern = database.get_solid_fill_pat(doc=doc)

categories_for_selection = database.common_cat_dict()
sorted_cats = sorted(categories_for_selection.keys(), key=lambda x: x)

if forms.check_modelview(revit.active_view):
    selected_cat = forms.CommandSwitchWindow.show(sorted_cats, message="Select Category to Colorize", width = 400)
    if selected_cat == None:
        script.exit()

chosen_bic = [categories_for_selection[selected_cat]]
if selected_cat in ["Curtain Wall Panels", "Curtain Wall Mullions"]: # not so elegant way to support curtain panels by adding walls category
    chosen_bic.append(BIC.OST_Walls)

# get all element categories and return a list of all categories except chosen BIC
all_cats = doc.Settings.Categories
chosen_category = [all_cats.get_Item(i) for i in chosen_bic]
hide_categories_except = [c for c in all_cats if c.Id not in [i.Id for i in chosen_category]]


get_view_elements = DB.FilteredElementCollector(doc) \
        .OfCategory(chosen_bic[0]) \
        .WhereElementIsNotElementType() \
        .ToElements()

types_dict = defaultdict(set)
for el in get_view_elements:
    # discard nested shared - group under the parent family
    if selected_cat in ["Floors", "Walls", "Ceilings"]:
        type_id = el.GetTypeId()
    else:
        try:
            type_id = el.SuperComponent.GetTypeId()
        except:
            type_id = el.GetTypeId()
    types_dict[type_id].add(el.Id)

n = len(types_dict)
revit_colours = colorize.get_colours(n)

with revit.Transaction("Isolate and Colorize Types"):
    for type_id, colour in zip(types_dict.keys(), revit_colours):
        type_instance = types_dict[type_id]
        override = colorize.set_colour_overrides_by_option(overrides_option, colour, doc)
        for inst in type_instance:
            view.SetElementOverrides(inst, override)
