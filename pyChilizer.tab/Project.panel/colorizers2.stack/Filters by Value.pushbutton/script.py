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
from Autodesk.Revit import Exceptions
logger = script.get_logger()
BIC = DB.BuiltInCategory
BIP = DB.BuiltInParameter
doc = revit.doc
view = revit.active_view

overrides_option = filterbyvalueconfig.get_config()


# colour gradients solution by https://bsouthga.dev/posts/color-gradients-with-python

# [ ] test in R2022
# [x] test in R2023
# [ ] exclude irrelevant builtin params
# [ ] use labels instead of hard-coded names for BIC

# OTHER NOTES
# for parameters with storage type Double
EPSILON = 0.01


class ParameterOption(forms.TemplateListItem):
    """Wrapper for selecting parameters from a list"""

    def __init__(self, param, param_dict):
        super(ParameterOption, self).__init__(param)
        self.param_dict = param_dict

    @property
    def name(self):
        return str(self.param_dict[self.item])


def match_bip_by_id(categories_list, id):
    for bic in categories_list:
        # iterating through each category helps address cases where some selected categories are not present in the model
        any_element_of_cat = DB.FilteredElementCollector(doc).OfCategory(bic).WhereElementIsNotElementType().FirstElement()
        if any_element_of_cat:
            element_i_params = any_element_of_cat.Parameters
            element_t_params = query.get_type(any_element_of_cat).Parameters
            for p in element_i_params:
                if p.Id == id:
                    return p.Definition.BuiltInParameter
            for p in element_t_params:
                if p.Id == id:
                    return p.Definition.BuiltInParameter
    return None

def get_multicat_param_storage_type(categories_list, parameter):
    for bic in categories_list:
        any_element_of_cat = DB.FilteredElementCollector(doc)\
            .OfCategory(bic)\
            .WhereElementIsNotElementType()\
            .FirstElement()
        if any_element_of_cat:
            instance_parameter = any_element_of_cat.get_Parameter(parameter)
            if instance_parameter:
                return database.p_storage_type(instance_parameter)
            type_parameter = query.get_type(any_element_of_cat).get_Parameter(parameter)
            if type_parameter:
                return database.p_storage_type(type_parameter)

def id_from_guid(categories_list, guid):

    for bic in categories_list:

        # iterating through each category helps address cases where some selected categories are not present in the model
        any_element_of_cat = DB.FilteredElementCollector(doc).OfCategory(bic).WhereElementIsNotElementType().ToElements()
        for el in any_element_of_cat:
            element_i_params = el.Parameters
            for p in element_i_params:
                try:
                    if p.GUID== guid:
                        return p.Id
                except Exceptions.InvalidOperationException:
                    pass
            element_t_params = query.get_type(el).Parameters
            for p in element_t_params:
                try:
                    if p.GUID and p.GUID == guid:
                        return p.Id
                except Exceptions.InvalidOperationException:
                    pass
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
    "Topography": BIC.OST_Topography,
    "Structural Columns": BIC.OST_StructuralColumns,
    "Structural Framing": BIC.OST_StructuralFraming,
    "Stairs": BIC.OST_Stairs,
    "Ramps": BIC.OST_Ramps,
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
# get all element categories and return a list of all categories except chosen BIC
all_cats = doc.Settings.Categories
chosen_category_ids = [all_cats.get_Item(bic).Id for bic in chosen_bics]

# get elements in current view
multicatfilter = DB.ElementMulticategoryFilter(List[BIC](chosen_bics))
get_view_elements = DB.FilteredElementCollector(doc, view.Id).WherePasses(multicatfilter).ToElements()

param_dict = {}

# a list of Ids
filterable_parameter_ids = DB.ParameterFilterUtilities.GetFilterableParametersInCommon(doc, List[DB.ElementId](
    chosen_category_ids))

forms.alert_ifnot(filterable_parameter_ids.Count != 0, "No parameters are common for selected categories", exitscript=True)



for id in filterable_parameter_ids:
    # the Id of BuiltInParameters is a negative one
    if id.IntegerValue < 0:
        # iterate through all parameters of an element of category(ies)
        # until the Id of the parameter matches the id from the list of filterable parameters
        bip = match_bip_by_id(chosen_bics, id)
        if bip:
            param_dict[bip] = database.get_builtin_label(bip)
    else:
        # Shared Parameter or (?) Builtin parameter
        shared_param = doc.GetElement(id)
        param_dict[shared_param.GuidValue] = shared_param.Name + " [Shared Parameter]"

forms.alert_ifnot(param_dict, "No parameters or elements found for selected categories", exitscript=True)
# show UI form to pick parameters
p_class = [ParameterOption(x, param_dict) for x in param_dict.keys()]
p_ops = sorted(p_class, key=lambda x: x.name)

selected_parameter = forms.SelectFromList.show(p_ops,
                                               button_name="Select Parameters",
                                               multiselect=False)

forms.alert_ifnot(selected_parameter, "No Parameters Selected", exitscript=True)

values = []

# this is a list of parameters that exist for instance elements, but their values will be empty
# this list will be used to prevent the empty values to be used
symbol_parameters = [DB.BuiltInParameter.SYMBOL_NAME_PARAM,
                       DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM]

# get the storage type of the selected parameter - used when constructing filters
selected_param_storage_type = get_multicat_param_storage_type(chosen_bics, selected_parameter)

# iterate through elements in view and gather all unique values of selected parameter
for el in get_view_elements:
    # print (database.get_name(el), el.Id, type(el))
    el_param = el.get_Parameter(selected_parameter)
    # if the element is an instance parameter and not a symbol parameter, query its value

    if el_param and database.get_param_value_by_storage_type(el_param) and selected_parameter not in symbol_parameters:
        el_param_value = database.get_param_value_by_storage_type(el_param)

        if el_param_value:
            if selected_param_storage_type != "Double":
                if el_param_value and el_param_value not in values:

                    values.append(el_param_value)
            else:
                display_value = el_param.AsValueString()
                values_set = {display_value : el_param_value}
                if len(values) >0:
                    ks = [list(x)[0] for x in values]
                    if display_value not in ks:
                        values.append(values_set)
                else:
                    values.append(values_set)
    # if not - look for the parameter of the type of the element
    else:

        el_type = query.get_type(el)

        el_type_param = el_type.get_Parameter(selected_parameter)
        if el_type_param:

            el_type_param_value = database.get_param_value_by_storage_type(el_type_param)

            if selected_param_storage_type != "Double":
                if el_type_param_value and el_type_param_value not in values:
                    values.append(el_type_param_value)
            else:
                # print ("got type with value double, {} ".format( el_type_param.Id))
                display_value = el_type_param.AsValueString()

                if el_type_param_value:
                    values_set = {display_value : el_type_param_value}
                    if len(values) >0:
                        for v in values:
                            ks = [list(x)[0] for x in values]
                            if display_value not in ks:
                                values.append(values_set)
                    else:
                        values.append(values_set)

# colour dictionary
n = len(values)
# print ("Values {} ".format(values))


forms.alert_ifnot(n > 0, "There are no values found for the selected parameter.", exitscript=True)
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

# parameter id for filters
if isinstance(selected_parameter, DB.BuiltInParameter):
    parameter_id = DB.ElementId(selected_parameter)

else:
    parameter_id = id_from_guid(chosen_bics, selected_parameter)
    forms.alert_ifnot(parameter_id, "no id found for parameter {}".format(selected_parameter), exitscript=True)

def create_filter(filter_name, bics_list, doc=revit.doc):
    cat_list = List[DB.ElementId](DB.ElementId(cat) for cat in bics_list)
    filter = DB.ParameterFilterElement.Create(doc, filter_name, cat_list)
    return filter

with revit.Transaction("Filters by Value", doc):
    for param_value, c in zip(values, revit_colours):
        override = DB.OverrideGraphicSettings()
        if "Projection Line Colour" in overrides_option:
            override.SetProjectionLineColor(c)
        if "Cut Line Colour" in overrides_option:
            override.SetCutLineColor(c)
        if "Projection Surface Colour" in overrides_option:
            override.SetSurfaceForegroundPatternColor(c)
            override.SetSurfaceForegroundPatternId(database.get_solid_fill_pat(doc).Id)
        if "Cut Pattern Colour" in overrides_option:
            override.SetCutForegroundPatternColor(c)
            override.SetCutForegroundPatternId(database.get_solid_fill_pat(doc).Id)

        # create a filter for each param value
        if selected_param_storage_type == "ElementId":
            value_name = database.get_name(doc.GetElement(param_value))
        elif selected_param_storage_type == "Double":
            value_name = list(param_value)[0]
            param_value = param_value[value_name]
        else:
            value_name = str(param_value)
        filter_name = param_dict[selected_parameter].replace(" [Shared Parameter]", "") + " - " + value_name
        filter_id = None
        # check if the filter with the given name already exists
        filter_exists = database.check_filter_exists(filter_name, doc)
        # choose to override or not. Remember the choice and not ask again within the same run
        if filter_exists and override_filters == 0:
            use_existent = forms.alert(
                "Filter with the required name already exists. Do you want to use existing filters?", yes=True,
                no=True)
            if use_existent:
                override_filters = 1
            else:
                override_filters = -1

        if override_filters == 1 and filter_exists:

            filter_id = filter_exists.Id
        else:
            if filter_exists:
                # delete filters
                doc.Delete(filter_exists.Id)
            if selected_param_storage_type == "ElementId":
                equals_rule = DB.ParameterFilterRuleFactory.CreateEqualsRule(parameter_id, param_value)
            elif selected_param_storage_type == "Integer":
                equals_rule = DB.ParameterFilterRuleFactory.CreateEqualsRule(parameter_id, int(param_value))
            elif selected_param_storage_type == "Double":
                equals_rule = DB.ParameterFilterRuleFactory.CreateEqualsRule(parameter_id, param_value, EPSILON)
            elif selected_param_storage_type == "String":
                equals_rule = DB.ParameterFilterRuleFactory.CreateEqualsRule(parameter_id, param_value)
            f_rules = List[DB.FilterRule]([equals_rule])
            parameter_filter = database.filter_from_rules(f_rules)
            new_filter = create_filter(filter_name, chosen_bics)
            new_filter.SetElementFilter(parameter_filter)
            filter_id = new_filter.Id
            # add filter to view
            # #todo! remove if filter already applied
            view.AddFilter(filter_id)
        view.SetFilterOverrides(filter_id, override)
