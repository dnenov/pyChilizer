import sys

from pyrevit import revit, DB, forms
from pyrevit import script
import random
from pychilizer import database
from pychilizer import colorize
from pyrevit.framework import List
import filterbyvalueconfig
from collections import defaultdict
from pyrevit.revit.db import query
from pyrevit.forms import reactive, WPF_VISIBLE, WPF_COLLAPSED

logger = script.get_logger()
BIC = DB.BuiltInCategory
doc = revit.doc
view = revit.active_view

overrides_option = filterbyvalueconfig.get_config()


# colour gradients solution by https://bsouthga.dev/posts/color-gradients-with-python

# [ ] test in R2022
# [x] test in R2023
# [ ] exclude irrelevant builtin params
# [ ] use labels instead of hard-coded names for BIC
class ParameterOption(forms.TemplateListItem):
    """Wrapper for selecting parameters from a list"""

    def __init__(self, param, param_dict):
        super(ParameterOption, self).__init__(param)
        self.param_dict = param_dict

    @property
    def name(self):
        return str(self.param_dict[self.item])


def match_bip_by_id (el, id):
    element_i_params = el.Parameters
    element_t_params = query.get_type(el).Parameters

    for p in element_i_params:
        # print (p.Definition.Name)
        # print (p.Id, "- " , id)
        if p.Id == id:
            return p
    for p in element_t_params:
        # print(p.Id, "- ", id)
        if p.Id == id:
            return p
    return None


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
    "Electrical Equipment": BIC.OST_ElectricalEquipment,
    "Electrical Fixtures": BIC.OST_ElectricalFixtures,
    "Parking": BIC.OST_Parking,
    "Site": BIC.OST_Site,
    "Entourage": BIC.OST_Entourage,
    "Ceilings": BIC.OST_Ceilings,
    "Curtain Wall Panels": BIC.OST_CurtainWallPanels,
    "Curtain Wall Mullions": BIC.OST_CurtainWallMullions,
    "Topography":BIC.OST_Topography,
    "Structural Columns":BIC.OST_StructuralColumns,
    "Structural Framing":BIC.OST_StructuralFraming,
    "Stairs":BIC.OST_Stairs,
    "Ramps":BIC.OST_Ramps,
}

if forms.check_modelview(revit.active_view):
    selected_cat = forms.SelectFromList.show(sorted(category_opt_dict),
                                             message="Select Category to Colorize",
                                             multiselect=True,
                                            width=400)
if selected_cat == None:
    script.exit()
# format the category dictionary
chosen_bics = [category_opt_dict[c] for c in selected_cat]
# print (chosen_bics)
# get all element categories and return a list of all categories except chosen BIC
all_cats = doc.Settings.Categories
chosen_category_ids = [all_cats.get_Item(bic).Id for bic in chosen_bics]

# hide_categories_except = [c for c in all_cats if c.Id != chosen_category.Id]

# get_view_elements = DB.FilteredElementCollector(doc) \
#     .OfCategory(chosen_bic[0]) \
#     .WhereElementIsNotElementType() \
#     .FirstElement()

get_any_element = DB.FilteredElementCollector(doc) \
    .OfCategory(chosen_bics[0]) \
    .WhereElementIsNotElementType() \
    .FirstElement()

_param_dict = {}
# type_param_dict = {}
# inst
param_dict = {}

# a list of Ids
filterable_parameters = DB.ParameterFilterUtilities.GetFilterableParametersInCommon(doc, List[DB.ElementId](chosen_category_ids))



for x in filterable_parameters:
    if x.IntegerValue <0:
        bip = match_bip_by_id(get_any_element, x)
        if bip:
            # print (bip.Definition.Name)
            param_dict[bip] = bip.Definition.Name
        # else:
        #     print ("no match")
    else:
        # Shared Parameter or (?) Builtin parameter
        shared_param = doc.GetElement(x)
        param_dict[shared_param] = shared_param.Name


# show UI form to pick parameters
p_class = [ParameterOption(x, param_dict) for x in param_dict.keys()]
p_ops = sorted(p_class, key=lambda x:x.name)

selected_parameter = forms.SelectFromList.show(p_ops,
                                                button_name="Select Parameters",
                                                multiselect = False)

forms.alert_ifnot(selected_parameter, "No Parameters Selected", exitscript=True)

print (selected_parameter)

# get elements in current view
multicatfilter = DB.ElementMulticategoryFilter(List[BIC](chosen_bics))
get_view_elements = DB.FilteredElementCollector(doc, view.Id).WherePasses(multicatfilter).ToElements()

# selected_p_storage_type = database.p_storage_type(database.get_parameter_from_name(get_view_elements[0], selected_parameter))
# print (selected_p_storage_type)
# # sys.exit()

print (len(get_view_elements))


# {value of parameter : element id}
# need a nested dictionary
values_dict = defaultdict(list)

for el in get_view_elements:
    el_param = el.get_Parameter(selected_parameter)
    print (el_param)
    # if selected_parameter in inst_param_dict.keys():
    #     el_parameter = el.get_Parameter(selected_parameter)
    #     if el_parameter:
    #         param_value = database.get_param_value_as_string(el_parameter)
    #         # values_dict[param_value] = []
    #         values_dict[param_value].append(el.Id)
    # else:
    #     el_type =query.get_type(el)
    #     element_type_parameter = el_type.get_Parameter(selected_parameter)
    #     if element_type_parameter:
    #         param_value = database.get_param_value_as_string(element_type_parameter)
    #         values_dict[param_value].append(el.Id)

# debug value groups
# for i in values_dict.keys():
#     print (len(values_dict[i]))

# for el in get_view_elements:
#     # discard nested shared - group under the parent family
#     if selected_cat in ["Floors", "Walls", "Roofs"]:
#         types_in_view[database.get_name(el)] = el.GetTypeId()
#     else:
#         if el.SuperComponent:
#             types_in_view[database.family_and_type_names(el.SuperComponent)] = el.SuperComponent.GetTypeId()
#         else:
#             types_in_view[database.family_and_type_names(el)] = el.GetTypeId()
#
#
# # iterate through unique types
# for type_name in return_types:
#     # note: names will be used as keys
#     type_id = types_in_view[type_name]
#     # type_name = database.get_name(doc.GetElement(type_id))
#
#     if type_name not in types_dict.values():
#         types_dict[type_id] = type_name
#     # this bit is no longer necessary
#     else:
#         while type_name in types_dict.values():
#             type_name = type_name + "(2)"
#         types_dict[type_id] = type_name

# colour dictionary
n = len(values_dict.keys())
print ("values nr", n)
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
# type_name_param = DB.BuiltInParameter.ALL_MODEL_TYPE_NAME
# dictionary of parameters{param value as string : [ids]}
with revit.Transaction("Colorize by Value"):
    for param_value, c in zip(values_dict.keys(), revit_colours):

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
        for el_id in values_dict[param_value]:

            # t_name_unique = types_dict[type_id]
            # el_type = doc.GetElement(type_id)
            # type_param = el_type.get_Parameter(type_name_param)
            # type_name = type_param.AsValueString()
            # if not type_name:
            #     type_name = type_param.AsString()
            # also record family name for filters
            # fam_param = el_type.get_Parameter(DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM)
            # fam_name = fam_param.AsValueString()
            # if not fam_name:
            #     fam_name = fam_param.AsString()

            # create a filter for each param value
            # filter_name = selected_cat + " - " + str(param_value)
            # filter_id = None
            # check if the filter with the given name already exists
            # filter_exists = database.check_filter_exists(filter_name)
            # print ("Filter_name: {} filter exists:{}".format(filter_name, database.get_name(filter_exists)))
            # print(database.get_name(filter_exists))
            # choose to override or not
            # if filter_exists and override_filters == 0:
            #
            #     use_existent = forms.alert(
            #         "Filter with the required name already exists. Do you want to use existing filters?", yes=True, no=True)
            #     if use_existent:
            #         override_filters = 1
            #     else:
            #         override_filters = -1
            #
            # if override_filters == -1:
            #     filter_id = filter_exists.Id
            # else:
            #     if filter_exists:
            #         # delete filters
            #         doc.Delete(filter_exists.Id)
            #     # todo: here a check needs to happen for parameter storage type
            #     p = database.get_parameter_from_name(el, selected_parameter)
            #     # if selected_p_storage_type == "ElementId":
            #     #     equals_rule = DB.ParameterFilterRuleFactory.CreateEqualsRule(p.Id, DB.ElementId(param_value))
            #     # elif selected_p_storage_type == "Integer":
            #     #     equals_rule = DB.ParameterFilterRuleFactory.CreateEqualsRule(p.Id, int(param_value))
            #     # elif selected_p_storage_type == "Double":
            #     #     equals_rule = DB.ParameterFilterRuleFactory.CreateEqualsRule(p.Id, float(param_value), 0)
            #     # elif selected_p_storage_type == "String":
            #     #     #todo: choose if case sensitive!
            #     #     equals_rule = DB.ParameterFilterRuleFactory.CreateEqualsRule(p.Id, param_value, True)
            #     equals_rule = DB.ParameterFilterRuleFactory.CreateEqualsRule(p.Id, param_value, True)
            #     # type_equals_rule = DB.ParameterFilterRuleFactory.CreateEqualsRule(type_param.Id, param_value, False)
            #     # fam_equals_rule = DB.ParameterFilterRuleFactory.CreateEqualsRule(fam_param.Id, fam_name, False)
            #     f_rules = List[DB.FilterRule]([equals_rule])
            #     parameter_filter = database.filter_from_rules(f_rules)
            #     new_filter = database.create_filter(filter_name, [chosen_bic])
            #     new_filter.SetElementFilter(parameter_filter)
            #     filter_id = new_filter.Id

            # define overrrides

            # add filter to view
            # #todo! remove if filter already applied
            # view.AddFilter(filter_id)
            # view.SetFilterOverrides(filter_id, override)
            view.SetElementOverrides(el_id, override)