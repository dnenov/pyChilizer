from pyrevit import forms
from pyrevit import revit, DB
from pyrevit import script
import random
from pychilizer import database
from pychilizer import colorize
from pyrevit.framework import List
import config

logger = script.get_logger()
BIC = DB.BuiltInCategory

doc = revit.doc
view = revit.active_view

overrides_option = config.get_config()

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

# types_dict = defaultdict(set)
# types_set = set()
# dictionary to keep track of identical type names across families
# the method will treat the types as different, but the filter name will be given a suffix to avoid long names
types_dict={}
for el in get_view_elements:
    # discard nested shared - group under the parent family
    if selected_cat in ["Floors", "Walls"]:
        type_id = el.GetTypeId()
    else:
        if el.SuperComponent:
            type_id = el.SuperComponent.GetTypeId()
        else:
            type_id = el.GetTypeId()
    # # note: names will be used as keys to distinguish between identically-named family types
    type_name = database.get_name(doc.GetElement(type_id))
    if type_name not in types_dict.keys():
        types_dict[type_name] = type_id
    else:
        while type_name in types_dict.keys():
            type_name = type_name + "(2)"
        types_dict[type_name] = type_id

# # old method
# colours = random_colour_hsv(len(types_dict))

# colour dictionary
n = len(types_dict.keys())

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

def create_filter_from_rules(rules):
    elem_filters = List[DB.ElementFilter]()
    for rule in rules:
        elem_param_filter = DB.ElementParameterFilter(rule)
        elem_filters.Add(elem_param_filter)
    el_filter = DB.LogicalAndFilter(elem_filters)
    return el_filter


if n < 14:
    colours = basic_colours
else:
    colours = rainbow
col_dict = colorize.polylinear_gradient(colours, n)
chop_col_list = col_dict["hex"][0:n]

revit_colours = [colorize.revit_colour(h) for h in chop_col_list]
for x in range(10):
    random.shuffle(revit_colours)

def check_filter_exists(filter_name):
    all_view_filters = DB.FilteredElementCollector(doc).OfClass(DB.FilterElement).ToElements()

    for vf in all_view_filters:
        if filter_name == str(vf.Name):
            return vf


def create_filter(filter_name, bics_list):

    cat_list = List[DB.ElementId](DB.ElementId(cat) for cat in bics_list)
    filter = DB.ParameterFilterElement.Create(doc, filter_name, cat_list)
    return filter


def filter_from_rules(rules, or_rule=False):
    elem_filters = List[DB.ElementFilter]()
    for rule in rules:
        elem_parameter_filter = DB.ElementParameterFilter(rule)
        elem_filters.Add(elem_parameter_filter)
    if or_rule:
        elem_filter = DB.LogicalOrFilter(elem_filters)
    else:
        elem_filter = DB.LogicalAndFilter(elem_filters)
    return elem_filter


override_filters = 0
type_name_param = DB.BuiltInParameter.ALL_MODEL_TYPE_NAME

with revit.Transaction("Isolate and Colorize Types"):
    for t_name_unique, c in zip(types_dict.keys(), revit_colours):
        type_id = types_dict[t_name_unique]
        el_type = doc.GetElement(type_id)
        type_param = el_type.get_Parameter(type_name_param)
        type_name = type_param.AsValueString()
        if not type_name:
            type_name = type_param.AsString()
        # also record family name for filters
        fam_param = el_type.get_Parameter(DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM)
        fam_name = fam_param.AsValueString()
        if not fam_name:
            fam_name = fam_param.AsString()
        # create a filter for each type
        filter_name = selected_cat + " - " + t_name_unique
        filter_id = None
        # check if the filter with the given name already exists
        filter_exists = check_filter_exists(filter_name)
            # print ("Filter_name: {} filter exists:{}".format(filter_name, database.get_name(filter_exists)))
            # print(database.get_name(filter_exists))
        # choose to override or not
        if filter_exists and override_filters==0:

            choose_to_override = forms.alert("Filter with the required name already exists. Do you want to override the filters?", yes=True, no=True)
            if choose_to_override:
                override_filters = 1
            else:
                override_filters = -1

        if override_filters == -1:
            filter_id = filter_exists.Id
        else:
            if filter_exists:
                # delete filters
                doc.Delete(filter_exists.Id)

            type_equals_rule = DB.ParameterFilterRuleFactory.CreateEqualsRule(type_param.Id, type_name, False)
            fam_equals_rule = DB.ParameterFilterRuleFactory.CreateEqualsRule(fam_param.Id, fam_name, False)
            f_rules = List[DB.FilterRule]([type_equals_rule, fam_equals_rule])
            parameter_filter = filter_from_rules(f_rules)
            new_filter = create_filter(filter_name, [chosen_bic])
            new_filter.SetElementFilter(parameter_filter)
            filter_id = new_filter.Id

        # define overrrides
        override = DB.OverrideGraphicSettings()
        # override.SetProjectionLineColor(c)
        override.SetSurfaceForegroundPatternColor(c)
        override.SetSurfaceForegroundPatternId(database.get_solid_fill_pat().Id)
        # revit.active_view = view
        # add filter to view
        view.AddFilter(filter_id)
        view.SetFilterOverrides(filter_id, override)


