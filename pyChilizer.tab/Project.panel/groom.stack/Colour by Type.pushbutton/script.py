from collections import defaultdict
from pyrevit import HOST_APP
from pyrevit import forms
from pyrevit import revit, DB
from pyrevit import script
import random
from pychilizer import database
from pychilizer import colorize




logger = script.get_logger()
BIC = DB.BuiltInCategory
doc = revit.doc
view = revit.active_view

# colour gradients solution by https://bsouthga.dev/posts/color-gradients-with-python

# [x] revise colours to exclude nearby colours
# [x] include more categories
# [x] set view to open active
# [ ] method gradient or random
# [ ] include which types to colorize
# [ ] test in R2022 R2023


category_opt_dict = {
    "Windows" : BIC.OST_Windows,
    "Doors" : BIC.OST_Doors,
    "Floors" : BIC.OST_Floors,
    "Walls" : BIC.OST_Walls,
    # "Curtain Panels" : BIC.OST_CurtainWallPanels,
    "Generic Model" : BIC.OST_GenericModel,
    "Casework" : BIC.OST_Casework,
    "Furniture" : BIC.OST_Furniture,
    "Plumbing Fixtures" : BIC.OST_PlumbingFixtures
}

if forms.check_modelview(revit.active_view):
    selected_cat = forms.CommandSwitchWindow.show(category_opt_dict, message="Select Category to Colorize", width = 400)


# which category
# windows, doors, floors, walls, furniture, plumbing, casework,

chosen_bic = category_opt_dict[selected_cat]

# get all element categories and return a list of all categories except chosen BIC
all_cats = doc.Settings.Categories
chosen_category = all_cats.get_Item(chosen_bic)
hide_categories_except = [c for c in all_cats if c.Id != chosen_category.Id]


get_view_elements = DB.FilteredElementCollector(doc) \
        .OfCategory(chosen_bic) \
        .WhereElementIsNotElementType() \
        .ToElements()

# print (get_view_elements)
types_dict = defaultdict(set)
for el in get_view_elements:
    # discard nested shared - group under the parent family
    if selected_cat in ["Floors", "Walls"]:
        type_id = el.GetTypeId()
    else:
        if el.SuperComponent:
            # print ("is super")
            type_id = el.SuperComponent.GetTypeId()
        else:
            # print ("not super")
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
        # override.SetProjectionLineColor(c)
        override.SetSurfaceForegroundPatternColor(c)
        override.SetSurfaceForegroundPatternId(database.get_solid_fill_pat().Id)
        for inst in type_instance:
            view.SetElementOverrides(inst, override)
# revit.active_view = view
