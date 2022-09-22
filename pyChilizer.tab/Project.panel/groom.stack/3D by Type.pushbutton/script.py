from collections import defaultdict
from pyrevit import HOST_APP
from pyrevit import forms
from pyrevit import revit, DB
from pyrevit import script
import random
from pychilizer import database

logger = script.get_logger()
BIC = DB.BuiltInCategory
doc = revit.doc


# colour gradients solution by https://bsouthga.dev/posts/color-gradients-with-python

# [x] revise colours to exclude nearby colours
# [x] include more categories
# [x] set view to open active
# [ ] method gradient or random
# [ ] include which types to colorize
# [ ] test in R2022 R2023


def hex_to_rgb(hex):
    return [int(hex[i:i + 2], 16) for i in range(1, 6, 2)]


def rgb_to_hex(rgb):
    rgb = [int(x) for x in rgb]
    return "#" + "".join(["0{0:x}".format(v) if v < 16 else "{0:x}".format(v) for v in rgb])


def color_dict(gradient):
    """Takes in a list of RGB sub-lists and returns dictionary of
        colors in RGB and hex form for use in a graphing function
        defined later on """
    return {
        "hex": [rgb_to_hex(rgb) for rgb in gradient],
        "r": [rgb[0] for rgb in gradient],
        "g": [rgb[1] for rgb in gradient],
        "b": [rgb[2] for rgb in gradient],
    }


def linear_gradient(start_hex, finish_hex, n=10):
    """ returns a gradient list of (n) colors between
        two hex colors. start_hex and finish_hex
        should be the full six-digit color string,
        including the number sign ("#FFFFFF") """
    # Starting and ending colors in RGB form
    s = hex_to_rgb(start_hex)
    f = hex_to_rgb(finish_hex)
    # Initilize a list of the output colors with the starting color
    rgb_list = [s]
    # Calcuate a color at each evenly spaced value of t from 1 to n
    for t in range(1, n):
        # Interpolate RGB vector for color at the current value of t
        curr_vector = [int(s[j] + (float(t) / (n - 1)) * (f[j] - s[j])) for j in range(3)]
        # Add it to our list of output colors
        rgb_list.append(curr_vector)
    return color_dict(rgb_list)


def polylinear_gradient(colors, n):
    ''' returns a list of colors forming linear gradients between
          all sequential pairs of colors. "n" specifies the total
          number of desired output colors '''
    # The number of colors per individual linear gradient
    n_out = int(float(n) / (len(colors) - 1)) + 2
    # returns dictionary defined by color_dict()
    gradient_dict = linear_gradient(colors[0], colors[1], n_out)

    if len(colors) > 1:
        for col in range(1, len(colors) - 1):
            next = linear_gradient(colors[col], colors[col + 1], n_out)
            for k in ("hex", "r", "g", "b"):
                # Exclude first point to avoid duplicates
                gradient_dict[k] += next[k][1:]
    return gradient_dict


# def generate_rand_colour_hsv(n):
#     hsv_tuples = [(i * 1.0 / n, 0.75, 0.75) for i in range(n)]
#     # print (hsv_tuples)
#     rgb_out = []
#     for rgb in hsv_tuples:
#         rgb = map(lambda x: int(x * 255), colorsys.hsv_to_rgb(*rgb))
#         revit_colour = DB.Color(rgb[0], rgb[1], rgb[2])
#         rgb_out.append(revit_colour)
#     return rgb_out


def revit_colour(hex):
    rgb = hex_to_rgb(hex)
    revit_clr = DB.Color(rgb[0], rgb[1], rgb[2])
    return revit_clr


def get_3Dviewtype_id():
    view_fam_type = DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType)
    return next(vt.Id for vt in view_fam_type if vt.ViewFamily == DB.ViewFamily.ThreeDimensional)


def delete_existing_view(view_name):
    for view in DB.FilteredElementCollector(revit.doc).OfClass(DB.View).ToElements():
        if view.Name == view_name:
            try:
                doc.Delete(view.Id)
                break
            except:

                forms.alert('Current view was cannot be deleted. Close view and try again.')
                return False
    return True


def remove_vt(vt_id):
    viewtype = doc.GetElement(vt_id)
    template_id = viewtype.DefaultTemplateId
    if template_id.IntegerValue != -1:
        if forms.alert(
                "You are about to remove the View Template"
                " associated with this View Type. Is that cool with ya?",
                ok=False, yes=True, no=True, exitscript=True):
            viewtype.DefaultTemplateId = DB.ElementId(-1)

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

with revit.Transaction("Create Colorized 3D"):
    view_name = "Colorize {} by Type".format(chosen_category.Name)
    if delete_existing_view(view_name):
        # create new 3D
        viewtype_id = get_3Dviewtype_id()
        remove_vt(viewtype_id)
        view = DB.View3D.CreateIsometric(doc, viewtype_id)
        view.Name = view_name

    # hide other categories
    for cat in hide_categories_except:
        if view.CanCategoryBeHidden(cat.Id):
            view.SetCategoryHidden(cat.Id, True)

    # get_view_elements = DB.FilteredElementCollector(doc) \
    #     .OfClass(DB.FamilyInstance) \
    #     .OfCategory(chosen_bic) \
    #     .WhereElementIsNotElementType() \
    #     .ToElements()

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
# colours = generate_rand_colour_hsv(len(types_dict))
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
col_dict = polylinear_gradient(colours, n)
chop_col_list = col_dict["hex"][0:n]

revit_colours = [revit_colour(h) for h in chop_col_list]
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
revit.active_view = view
