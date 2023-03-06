from collections import defaultdict
from pyrevit import HOST_APP
from pyrevit import forms
from pyrevit import revit, DB
from pyrevit import script
import random
import threedconfig
from pychilizer import database, colorize

logger = script.get_logger()
BIC = DB.BuiltInCategory
doc = revit.doc
overrides_option = threedconfig.get_config()
solid_fill_pattern = database.get_solid_fill_pat(doc=doc)

# colour gradients solution by https://bsouthga.dev/posts/color-gradients-with-python

# [x] revise colours to exclude nearby colours
# [x] include more categories
# [x] set view to open active
# [ ] include which types to colorize
# [ ] test in R2022 R2023
# [ ] work with links?
# [x] fix dependency on the initial 3D view


category_opt_dict = {
    "Windows": BIC.OST_Windows,
    "Doors": BIC.OST_Doors,
    "Floors": BIC.OST_Floors,
    "Walls": BIC.OST_Walls,
    "Generic Model": BIC.OST_GenericModel,
    "Casework": BIC.OST_Casework,
    "Furniture": BIC.OST_Furniture,
    "Furniture Systems": BIC.OST_FurnitureSystems,
    "Plumbing Fixtures": BIC.OST_PlumbingFixtures,
    "Roofs": BIC.OST_Roofs,
    "Specialty Equipment": BIC.OST_SpecialityEquipment,
    "Ceilings": BIC.OST_Ceilings

}

selected_cat = forms.CommandSwitchWindow.show(category_opt_dict, message="Select Category to Colorize", width = 400)

chosen_bic = category_opt_dict[selected_cat]

# get all element categories and return a list of all categories except chosen BIC
all_cats = doc.Settings.Categories
chosen_category = all_cats.get_Item(chosen_bic)
hide_categories_except = [c for c in all_cats if c.Id != chosen_category.Id]

with revit.Transaction("Create Colorized 3D"):
    view_name = "Colorize {} by Type".format(chosen_category.Name)
    if database.delete_existing_view(view_name, doc=doc):
        # create new 3D
        viewtype_id = database.get_3Dviewtype_id(doc=doc)
        database.remove_viewtemplate(viewtype_id, doc=doc)
        view = DB.View3D.CreateIsometric(doc, viewtype_id)
        view.Name = view_name

    # hide other categories
    for cat in hide_categories_except:
        if view.CanCategoryBeHidden(cat.Id):
            view.SetCategoryHidden(cat.Id, True)

    get_view_elements = DB.FilteredElementCollector(doc) \
        .OfCategory(chosen_bic) \
        .WhereElementIsNotElementType() \
        .ToElements()

types_dict = defaultdict(set)
for el in get_view_elements:
    # discard nested shared - group under the parent family
    if selected_cat in ["Floors", "Walls", "Roofs", "Ceilings"]:
        type_id = el.GetTypeId()
    else:
        if el.SuperComponent:
            type_id = el.SuperComponent.GetTypeId()
        else:
            type_id = el.GetTypeId()
    types_dict[type_id].add(el.Id)


# colour dictionary
n = len(types_dict)

if n < 14:
    colours = colorize.basic_colours()
else:
    colours = colorize.rainbow()
col_dict = colorize.polylinear_gradient(colours, n)
chop_col_list = col_dict["hex"][0:n]

revit_colours = [colorize.revit_colour(h) for h in chop_col_list]
for x in range(10):
    random.shuffle(revit_colours)

with revit.Transaction("Isolate and Colorize Types"):
    for type_id, c in zip(types_dict.keys(), revit_colours):
        type_instance = types_dict[type_id]
        override = DB.OverrideGraphicSettings()
        if "Projection Line Colour" in overrides_option:
            override.SetProjectionLineColor(c)
        if "Cut Line Colour" in overrides_option:
            override.SetCutLineColor(c)
        if "Projection Surface Colour" in overrides_option:
            override.SetSurfaceForegroundPatternColor(c)
            override.SetSurfaceForegroundPatternId(solid_fill_pattern.Id)
        if "Cut Pattern Colour" in overrides_option:
            override.SetCutForegroundPatternColor(c)
            override.SetCutForegroundPatternId(solid_fill_pattern.Id)
        for inst in type_instance:
            view.SetElementOverrides(inst, override)
revit.active_view = view
