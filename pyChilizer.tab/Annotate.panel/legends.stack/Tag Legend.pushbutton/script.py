__title__ = "Tag Legend"
__doc__ = "Pick from a list of parameters to annotate legend components in a legend. As tags are not available for legend views, parameter values will be shown as Text Notes"

from itertools import izip
from pyrevit import revit, DB, script, HOST_APP, forms
from rpw.ui.forms import (FlexForm, Label, ComboBox, Separator, Button, CheckBox)
import sys

# select all legend components in active view
view = revit.active_view
if view.ViewType != DB.ViewType.Legend:
    forms.alert("View is not a Legend View", exitscript=True)


legend_components = DB.FilteredElementCollector(revit.doc, view.Id) \
    .OfCategory(DB.BuiltInCategory.OST_LegendComponents) \
    .WhereElementIsNotElementType() \
    .ToElements()

forms.alert_ifnot(legend_components, "No Legend Components in View", exitscript=True)

# get all text styles to choose from
txt_types = DB.FilteredElementCollector(revit.doc).OfClass(DB.TextNoteType)
text_style_dict= {txt_t.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString(): txt_t for txt_t in txt_types}

# list positions for text placement
positions_list = ["Bottom Left", "Bottom Centre","Bottom Right", "Top Left", "Top Centre", "Top Right"]

# construct rwp UI
components = [
    Label("Pick Text Style"),
    ComboBox(name="textstyle_combobox", options=text_style_dict,),
    Label("Pick Text Position"),
    ComboBox(name="positions_combobox", options=positions_list),
    Separator(),
    CheckBox('show_p_name', 'Show Parameter Name'),
    Button("Select")
]
form = FlexForm("Select", components,exit_on_close=True)
select=form.show()
if select:
    text_style = form.values["textstyle_combobox"]
    chosen_position = form.values["positions_combobox"]
    show_p_name = form.values["show_p_name"]
else:
    sys.exit()

#dims and scale
scale = float(view.Scale)/100
text_offset = 2 * scale

# format legend component names to get family and type names:
fam_names = []
type_names = []
for lc in legend_components:
    component_name = lc.get_Parameter(DB.BuiltInParameter.LEGEND_COMPONENT).AsValueString()
    fragments = component_name.split(" : ")
    fam_names.append(fragments[1])
    type_names.append(fragments[-1])

# find types of family and type

types_on_legend = []
for f, t in izip(fam_names, type_names):
    fam_bip_id = DB.ElementId(DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM)
    fam_bip_provider = DB.ParameterValueProvider(fam_bip_id)
    if HOST_APP.is_newer_than(2022):
        fam_filter_rule = DB.FilterStringRule(fam_bip_provider, DB.FilterStringEquals(), f)
    else:
        fam_filter_rule = DB.FilterStringRule(fam_bip_provider, DB.FilterStringEquals(), f, True)
    fam_filter = DB.ElementParameterFilter(fam_filter_rule)

    type_bip_id = DB.ElementId(DB.BuiltInParameter.ALL_MODEL_TYPE_NAME)
    type_bip_provider = DB.ParameterValueProvider(type_bip_id)
    if HOST_APP.is_newer_than(2022):
        type_filter_rule = DB.FilterStringRule(type_bip_provider, DB.FilterStringEquals(), t)
    else:
        type_filter_rule = DB.FilterStringRule(type_bip_provider, DB.FilterStringEquals(), t, True)
    type_filter = DB.ElementParameterFilter(type_filter_rule)

    and_filter = DB.LogicalAndFilter(fam_filter, type_filter)

    collector = DB.FilteredElementCollector(revit.doc) \
        .WherePasses(and_filter) \
        .WhereElementIsElementType() \
        .FirstElement()

    types_on_legend.append(collector)

parameters_names_list = []
for t in types_on_legend:

    element_parameter_set = t.Parameters
    for p in element_parameter_set:
        parameter_name = p.Definition.Name
        if parameter_name not in parameters_names_list:
            parameters_names_list.append(parameter_name)

parameters_names_list.sort()

# show UI form to pick parameters
selected_parameters = forms.SelectFromList.show(parameters_names_list,
                                                button_name="Select Parameters",
                                                multiselect = True)

forms.alert_ifnot(selected_parameters, "No Parameters Selected", exitscript=True)

# TAG TAG TAG
with revit.Transaction("Tag parameter values"):
    for l, ton in izip(legend_components, types_on_legend):
        all_p_txt = []

        for sp in selected_parameters:
            try:
                p = ton.LookupParameter(sp)

                param_value = None
                if p.HasValue:
                    if p.StorageType.ToString() == "ElementId":
                        if p.Definition.Name == "Category":

                            param_value = p.AsValueString()
                        else:
                            param_value = p.AsElementId().IntegerValue
                    elif p.StorageType.ToString() == "Integer":

                        param_value = p.AsInteger()
                    elif p.StorageType.ToString() == "Double":

                        param_value= p.AsValueString()
                    elif p.StorageType.ToString() == "String":

                        param_value = p.AsString()
                if show_p_name:
                    all_p_txt.append("{0} : {1}".format(sp, str(param_value)))
                else:
                    all_p_txt.append(str(param_value))
            except:
                pass

        # position the note

        bb = l.get_BoundingBox(view)
        bbmax = bb.Max
        bbmin = bb.Min
        position_left_bot = DB.XYZ(bbmin.X, bbmin.Y-text_offset, 0)
        position_right_bot = DB.XYZ(bbmax.X, bbmin.Y-text_offset, 0)
        position_left_top = DB.XYZ(bbmin.X, bbmax.Y+text_offset, 0)
        position_right_top = DB.XYZ(bbmax.X, bbmax.Y+text_offset, 0)
        position_center_bot = DB.XYZ((bbmax.X - bbmin.X)/2+bbmin.X, bbmin.Y-text_offset, 0)
        position_center_top = DB.XYZ((bbmax.X - bbmin.X)/2+bbmin.X, bbmax.Y+text_offset, 0)

        opts = DB.TextNoteOptions(text_style.Id)

        if str(chosen_position) == "Bottom Left":
            position = position_left_bot
        elif str(chosen_position) == "Bottom Centre":
            position = position_center_bot
            opts.HorizontalAlignment = DB.HorizontalTextAlignment.Center
        elif str(chosen_position) == "Bottom Right":
            position = position_right_bot
            opts.HorizontalAlignment = DB.HorizontalTextAlignment.Right
        elif str(chosen_position) == "Top Left":
            position = position_left_top
            opts.VerticalAlignment = DB.VerticalTextAlignment.Bottom
        elif str(chosen_position) == "Top Centre":
            position = position_center_top
            opts.VerticalAlignment = DB.VerticalTextAlignment.Bottom
            opts.HorizontalAlignment = DB.HorizontalTextAlignment.Center
        elif str(chosen_position) == "Top Right":
            position = position_right_top
            opts.HorizontalAlignment = DB.HorizontalTextAlignment.Right
            opts.VerticalAlignment = DB.VerticalTextAlignment.Bottom


        txt = "\n".join(all_p_txt)

        tn = DB.TextNote.Create(revit.doc, view.Id, position, txt, opts)

