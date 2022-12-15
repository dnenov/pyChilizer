import sys

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
# [no] method gradient or random
# [x] include which types to colorize
# [x] include setting for projection/cut line and surface
# [x] test in R2022
# [ ] test in R2023


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
}

if forms.check_modelview(revit.active_view):
    selected_cat = forms.CommandSwitchWindow.show(sorted(category_opt_dict), message="Select Category to Colorize",
                                                  width=400)
# format the category dictionary
chosen_bic = category_opt_dict[selected_cat]

# get all element categories and return a list of all categories except chosen BIC
all_cats = doc.Settings.Categories
chosen_category = all_cats.get_Item(chosen_bic)
hide_categories_except = [c for c in all_cats if c.Id != chosen_category.Id]

get_view_elements = DB.FilteredElementCollector(doc) \
    .OfCategory(chosen_bic) \
    .WhereElementIsNotElementType() \
    .ToElements()

# dictionary of {filter name : type id}
types_dict = {}
types_in_view = {}
for el in get_view_elements:
    # discard nested shared - group under the parent family
    if selected_cat in ["Floors", "Walls", "Roofs"]:
        types_in_view[database.get_name(el)] = el.GetTypeId()
    else:
        if el.SuperComponent:
            types_in_view[database.family_and_type_names(el.SuperComponent)] = el.SuperComponent.GetTypeId()
        else:
            types_in_view[database.family_and_type_names(el)] = el.GetTypeId()

# pick which types to colour
return_types = \
    forms.SelectFromList.show(sorted(types_in_view),
                              title='Which types to colour',
                              button_name='Proceed',
                              multiselect=True
                              )

if not return_types:
    sys.exit(0)

# iterate through unique types
for type_name in return_types:
    # note: names will be used as keys
    type_id = types_in_view[type_name]
    # type_name = database.get_name(doc.GetElement(type_id))

    if type_name not in types_dict.values():
        types_dict[type_id] = type_name
    # this bit is no longer necessary
    else:
        while type_name in types_dict.values():
            type_name = type_name + "(2)"
        types_dict[type_id] = type_name

# colour dictionary
n = len(types_dict.keys())

if n < 14:
    colours = colorize.basic_colours()
else:
    colours = colorize.rainbow()
col_dict = colorize.polylinear_gradient(colours, n)
chop_col_list = col_dict["hex"][0:n]
# gradient method
revit_colours = [colorize.revit_colour(h) for h in chop_col_list]
# random method
# revit_colours = colorize.random_colour_hsv(len(types_dict))

for x in range(10):
    random.shuffle(revit_colours)

override_filters = 0
type_name_param = DB.BuiltInParameter.ALL_MODEL_TYPE_NAME

with revit.Transaction("Colorize Types"):
    for type_id, c in zip(types_dict.keys(), revit_colours):
        t_name_unique = types_dict[type_id]
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
        filter_exists = database.check_filter_exists(filter_name)
        # print ("Filter_name: {} filter exists:{}".format(filter_name, database.get_name(filter_exists)))
        # print(database.get_name(filter_exists))
        # choose to override or not
        if filter_exists and override_filters == 0:

            use_existent = forms.alert(
                "Filter with the required name already exists. Do you want to use existing filters?", yes=True, no=True)
            if use_existent:
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
            parameter_filter = database.filter_from_rules(f_rules)
            new_filter = database.create_filter(filter_name, [chosen_bic])
            new_filter.SetElementFilter(parameter_filter)
            filter_id = new_filter.Id

        # define overrrides
        override = DB.OverrideGraphicSettings()
        if "Projection Line Colour" in overrides_option:
            override.SetProjectionLineColor(c)
        if "Cut Line Colour" in overrides_option:
            override.SetCutLineColor(c)
        if "Projection Surface Colour" in overrides_option:
            override.SetSurfaceForegroundPatternColor(c)
            override.SetSurfaceForegroundPatternId(database.get_solid_fill_pat().Id)
        if "Cut Pattern Colour" in overrides_option:
            override.SetCutForegroundPatternColor(c)
            override.SetCutForegroundPatternId(database.get_solid_fill_pat().Id)
        # add filter to view
        view.AddFilter(filter_id)
        view.SetFilterOverrides(filter_id, override)
