__title__ = "Tag legend"
__doc__ = "Pick from a list of parameters to annotate legend components in a legend"


from itertools import izip
from pyrevit import revit, DB, script, forms

# select all legend components in active view

legend = revit.active_view
legend_components = DB.FilteredElementCollector(revit.doc, legend.Id) \
    .OfCategory(DB.BuiltInCategory.OST_LegendComponents) \
    .WhereElementIsNotElementType() \
    .ToElements()

# get a default text note type - to replace later
txt_type = revit.doc.GetElement(revit.doc.GetDefaultElementTypeId(DB.ElementTypeGroup.TextNoteType))
options = txt_type.Id

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
    fam_filter_rule = DB.FilterStringRule(fam_bip_provider, DB.FilterStringEquals(), f, True)
    fam_filter = DB.ElementParameterFilter(fam_filter_rule)

    type_bip_id = DB.ElementId(DB.BuiltInParameter.ALL_MODEL_TYPE_NAME)
    type_bip_provider = DB.ParameterValueProvider(type_bip_id)
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
selected_parameters = forms.SelectFromList.show(parameters_names_list,
                                                button_name="Select Parameters",
                                                multiselect = True)
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
                        param_value = p.AsElementId().IntegerValue
                    elif p.StorageType.ToString() == "Integer":
                        param_value = p.AsInteger()
                    elif p.StorageType.ToString() == "Double":
                        param_value= p.AsValueString()
                    elif p.StorageType.ToString() == "String":
                        param_value = p.AsString()

                all_p_txt.append("{0} : {1}".format(sp, str(param_value)))
            except:
                pass

# position the note center-below the legend component

        bb = l.get_BoundingBox(legend)
        bbmax = bb.Max
        bbmin = bb.Min
        position_bottom = DB.XYZ(bbmin.X, bbmin.Y, 0)
        txt = "\n".join(all_p_txt)
        tn = DB.TextNote.Create(revit.doc, legend.Id, position_bottom, txt, options)

