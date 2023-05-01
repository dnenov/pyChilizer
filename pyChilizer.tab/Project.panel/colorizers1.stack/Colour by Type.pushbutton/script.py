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

# colour gradients solution by https://bsouthga.dev/posts/color-gradients-with-python

category_opt_dict = {
    "Windows" : BIC.OST_Windows,
    "Doors" : BIC.OST_Doors,
    "Floors" : BIC.OST_Floors,
    "Walls" : BIC.OST_Walls,
    "Generic Model" : BIC.OST_GenericModel,
    "Casework" : BIC.OST_Casework,
    "Furniture" : BIC.OST_Furniture,
    "Furniture Systems": BIC.OST_FurnitureSystems,
    "Plumbing Fixtures" : BIC.OST_PlumbingFixtures,
    "Roofs": BIC.OST_Roofs,
    "Specialty Equipment": BIC.OST_SpecialityEquipment,
    "Ceilings": BIC.OST_Ceilings,
    "Curtain Wall Panels": BIC.OST_CurtainWallPanels
}

if forms.check_modelview(revit.active_view):
    selected_cat = forms.CommandSwitchWindow.show(category_opt_dict, message="Select Category to Colorize", width = 400)
    if selected_cat == None:
        script.exit()


# which category
# windows, doors, floors, walls, furniture, plumbing, casework,

chosen_bic = [category_opt_dict[selected_cat]]
if selected_cat == "Curtain Wall Panels": # not so elegant way to support curtain panels by adding walls category
    chosen_bic.append(BIC.OST_Walls)

# get all element categories and return a list of all categories except chosen BIC
all_cats = doc.Settings.Categories
chosen_category = [all_cats.get_Item(i) for i in chosen_bic]
hide_categories_except = [c for c in all_cats if c.Id not in [i.Id for i in chosen_category]]


get_view_elements = [DB.FilteredElementCollector(doc) \
        .OfCategory(cb) \
        .WhereElementIsNotElementType() \
        .ToElements() for cb in chosen_bic 
        ]

# print (get_view_elements)
types_dict = defaultdict(set)
for vl in get_view_elements:
    for el in vl:
        # discard nested shared - group under the parent family
        if selected_cat in ["Floors", "Walls", "Ceilings"]:
            type_id = el.GetTypeId()
        else:
            try:
                type_id = el.SuperComponent.GetTypeId()
            except:
                type_id = el.GetTypeId()
        types_dict[type_id].add(el.Id)
    
# # old method
# colours = random_colour_hsv(len(types_dict))

# colour dictionary
n = len(types_dict)

# colour presets
basic_colours = [
    "#40DFFF",
    "#803ABA",
    "#E6B637",
    "#A8DA84"
    "#8337E6",
    "#EBE70E",
    "#D037E6",
    "#074FE0",  # blue
    "#03A64A",
    "#662400",
    "#FF6B1A",
    "#FF4858",
    "#747F7F",
    "#919151"
]
dark = "#42371E"
red = "#F10800"
orange = "#F27405"
yellow = "#FFF14E"
green = "#016B31"
pink = "#F587FF"
blue = "#6DDEF0"
violet = "#550580"
cyan = "#40DFFF"
rainbow = [dark, red, yellow, green, cyan, violet, pink]

if n < 14:
    colours = basic_colours
else:
    colours = rainbow
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
# revit.active_view = view
