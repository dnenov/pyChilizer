import sys

from pyrevit import revit, DB, forms
from pyrevit import script
from pychilizer import database
from pychilizer import colorize
from pyrevit.framework import List
import filterbyvalueconfig
from pyrevit.revit.db import query
from pyrevit.forms import reactive, WPF_VISIBLE, WPF_COLLAPSED
from Autodesk.Revit import Exceptions

logger = script.get_logger()
BIC = DB.BuiltInCategory
BIP = DB.BuiltInParameter
doc = revit.doc
view = revit.active_view

overrides_option = filterbyvalueconfig.get_config()

# TODO - disabled for now, let's see .. Line 141-ish
# OTHER NOTES
EPSILON = 0.001  # for parameters with storage type Double
SHARED_PARAMETER_LABEL = " [Shared Parameter]"


class ParameterOption(forms.TemplateListItem):
    """Wrapper for selecting parameters from a list"""

    def __init__(self, param, param_dict):
        super(ParameterOption, self).__init__(param)
        self.param_dict = param_dict

    @property
    def name(self):
        return str(self.param_dict[self.item])


def match_bip_by_id(categories_list, id):
    # get the BIP from the provided Id
    for bic in categories_list:
        # iterating through each category helps address cases where some selected categories are not present in the model
        any_element_of_cat = DB.FilteredElementCollector(doc).OfCategory(
            bic).WhereElementIsNotElementType().FirstElement()
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
    # get the storage type of parameter, aided by a given categories list
    for bic in categories_list:
        any_element_of_cat = DB.FilteredElementCollector(doc) \
            .OfCategory(bic) \
            .WhereElementIsNotElementType() \
            .FirstElement()
        if any_element_of_cat:
            instance_parameter = any_element_of_cat.get_Parameter(parameter)
            if instance_parameter:
                return database.p_storage_type(instance_parameter)
            type_parameter = query.get_type(any_element_of_cat).get_Parameter(parameter)
            if type_parameter:
                return database.p_storage_type(type_parameter)


def add_param_value(param, param_storage_type, values):
    el_parameter_value = database.get_param_value_by_storage_type(param)
    if el_parameter_value and param_storage_type == "Double":
        # special approach for values stored as a Double :
        # {pretty AsValueString name for the filter name : actual value as a double}
        display_value = param.AsValueString()
        values_set = display_value, el_parameter_value
        if len(values) > 0 and display_value not in [x[0] for x in values]:
            values.append(values_set)
        elif len(values) == 0:
            return values.append(values_set)
    elif el_parameter_value is not None \
            and el_parameter_value not in values \
            and el_parameter_value != DB.ElementId.InvalidElementId \
            and param_storage_type != "Double":
        return values.append(el_parameter_value)
    return


# banned list - parameters that exist for instance elements, but their values will be empty
banned_symbol_parameters = [DB.BuiltInParameter.SYMBOL_NAME_PARAM,
                            DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM]

categories_for_selection = database.common_cat_dict()
sorted_cats = sorted(categories_for_selection.keys(), key=lambda x: x)

# ask the user for category/categories from the list
if forms.check_modelview(revit.active_view):
    selected_cat = forms.SelectFromList.show(sorted_cats,
                                             message="Select Category to Colorize",
                                             multiselect=True,
                                             width=400)
if selected_cat == None:
    script.exit()
# format the category dictionary
chosen_bics = [categories_for_selection[c] for c in selected_cat]
# get all element categories and return a list of all categories except chosen BIC
all_cats = doc.Settings.Categories
chosen_category_ids = [all_cats.get_Item(bic).Id for bic in chosen_bics]

# get elements of chosen categories in current view
multicatfilter = DB.ElementMulticategoryFilter(List[BIC](chosen_bics))
get_view_elements = DB.FilteredElementCollector(doc, view.Id).WherePasses(multicatfilter).ToElements()

param_dict = {}

# a list of Ids of parameters that can be used for filters
filterable_parameter_ids = DB.ParameterFilterUtilities.GetFilterableParametersInCommon(doc, List[DB.ElementId](
    chosen_category_ids))

forms.alert_ifnot(filterable_parameter_ids.Count != 0, "No parameters are common for selected categories",
                  exitscript=True)

for id in filterable_parameter_ids:
    # the Id of BuiltInParameters is a negative one
    if id.IntegerValue < 0:
        # iterate through all parameters of an element of category(ies)
        # until the Id of the parameter matches the id from the list of filterable parameters
        bip = match_bip_by_id(chosen_bics, id)
        if bip:
            param_dict[bip] = database.get_builtin_label(bip)
    else:
        # Shared Parameter or (?) Project parameter
        shared_param = doc.GetElement(id)
        try:
            # It's a shared parameter
            param_dict[shared_param.GuidValue] = shared_param.Name + SHARED_PARAMETER_LABEL
        except:
            # It's a project parameter - we are not using project parameters ? 
            # param_dict[shared_param.Id] = shared_param.Name + "PROJECT PARAMETER"
            pass
 

forms.alert_ifnot(param_dict, "No parameters or elements found for selected categories", exitscript=True)
# show UI form to pick parameters
p_class = [ParameterOption(x, param_dict) for x in param_dict.keys()]
p_ops = sorted(p_class, key=lambda x: x.name)

selected_parameter = forms.SelectFromList.show(p_ops,
                                               button_name="Select Parameters",
                                               multiselect=False)

forms.alert_ifnot(selected_parameter, "No Parameters Selected", exitscript=True)

values = []

# get the storage type of the selected parameter - used when constructing filters
selected_param_storage_type = get_multicat_param_storage_type(chosen_bics, selected_parameter)

# iterate through elements in view and gather all unique values of selected parameter
# accounts for cases where:
# * shared parameters can be both type and instance
# BIP can exist for both type and instance
# parameters can exist for both main and nested elements
for el in get_view_elements:
    el_param = el.get_Parameter(selected_parameter)
    # if the element is an instance parameter and not a symbol parameter, query its value
    if el_param \
        and database.get_param_value_by_storage_type(el_param) is not None \
        and selected_parameter not in banned_symbol_parameters:
        add_param_value(el_param, selected_param_storage_type, values)
    # if not - look for the parameter of the type of the element
    elif selected_parameter != BIP.ELEM_PARTITION_PARAM:  # excluded workset parameter to ignore non user-created worksets
        el_type = query.get_type(el)  # get type of the element
        el_type_param = el_type.get_Parameter(selected_parameter)
        if el_type_param:
            add_param_value(el_type_param, selected_param_storage_type, values)  # add value

# colour dictionary
n = len(values)
forms.alert_ifnot(n > 0, "There are no values found for the selected parameter.", exitscript=True)
revit_colours = colorize.get_colours(n)
# keep record of the decision to override filters or not
override_filters = 0
# parameter id for filters
if isinstance(selected_parameter, DB.BuiltInParameter):
    parameter_id = DB.ElementId(selected_parameter)

else:
    parameter_id = database.shared_param_id_from_guid(chosen_bics, selected_parameter, doc)
    forms.alert_ifnot(parameter_id, "no id found for parameter {}".format(selected_parameter), exitscript=True)

with revit.Transaction("Filters by Value", doc):
    for param_value, colour in zip(values, revit_colours):
        override = colorize.set_colour_overrides_by_option(overrides_option, colour, doc)
        # create a filter for each param value
        if selected_param_storage_type == "ElementId":
            value_name = database.get_name(doc.GetElement(param_value))
        elif selected_param_storage_type == "Double":
            value_name = param_value[0]
            param_value = param_value[1]
        else:
            value_name = str(param_value)
        filter_name = param_dict[selected_parameter].replace(SHARED_PARAMETER_LABEL, "") + " - " + value_name
        # replace forbidden characters:
        filter_name = filter_name.strip("{}[]:\|?/<>*")
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
                try:
                    equals_rule = DB.ParameterFilterRuleFactory.CreateEqualsRule(parameter_id, param_value)
                except TypeError:  # different method in versions earlier than R2023
                    equals_rule = DB.ParameterFilterRuleFactory.CreateEqualsRule(parameter_id, param_value, True)
            f_rules = List[DB.FilterRule]([equals_rule])
            parameter_filter = database.filter_from_rules(f_rules)
            new_filter = database.create_filter_by_name_bics(filter_name, chosen_bics, doc)
            new_filter.SetElementFilter(parameter_filter)
            filter_id = new_filter.Id
            # add filter to view
            view.AddFilter(filter_id)
        view.SetFilterOverrides(filter_id, override)
