"""List Family Symbols on a Legend View
"""

from pyrevit import revit, DB, UI, forms, script
from pyrevit.framework import List
from collections import OrderedDict
from Autodesk.Revit import Exceptions
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
from Autodesk.Revit.UI.Selection import Selection
import rpw
import sys
from pychilizer import database

BIC = DB.BuiltInCategory
doc = revit.doc

legend = revit.active_view
if legend.ViewType != DB.ViewType.Legend:
    forms.alert("View is not a Legend View", exitscript=True)

common_categories = [BIC.OST_Windows,
                     BIC.OST_Doors,
                     BIC.OST_Floors,
                     BIC.OST_Walls,
                     BIC.OST_GenericModel,
                     BIC.OST_Casework,
                     BIC.OST_Furniture,
                     BIC.OST_FurnitureSystems,
                     BIC.OST_PlumbingFixtures,
                     BIC.OST_Roofs,
                     BIC.OST_ElectricalEquipment,
                     BIC.OST_ElectricalFixtures,
                     # BIC.OST_Parking,
                     # BIC.OST_Site,
                     BIC.OST_Entourage,
                     BIC.OST_Ceilings
                     ]


def common_cat_dict():
    # a dictionary of common categories used for colorizers
    # formatted as {Category name : BIC}
    category_opt_dict = {}
    for cat in common_categories:
        category_opt_dict[database.get_builtin_label(cat)] = cat

    return category_opt_dict


categories_for_selection = common_cat_dict()

sorted_cats = sorted(categories_for_selection.keys(), key=lambda x: x)

selected_cat = forms.CommandSwitchWindow.show(sorted_cats, message="Select Category to Colorize",
                                              width=400)
if selected_cat == None:
    script.exit()

chosen_bic = categories_for_selection[selected_cat]

if chosen_bic in [BIC.OST_Walls]:
    view_directions = {"Section": -5, "Floor Plan": -8}
elif chosen_bic in [BIC.OST_Roofs, BIC.OST_Ceilings, BIC.OST_Floors]:
    view_directions = {"Section": -5}
elif chosen_bic in [BIC.OST_Windows, BIC.OST_Doors]:
    view_directions = {"Back": -6, "Front": -7, "Floor Plan": -8}
elif chosen_bic in [BIC.OST_GenericModel,
                    BIC.OST_Casework,
                    BIC.OST_ElectricalEquipment,
                    BIC.OST_ElectricalFixtures,
                    BIC.OST_Furniture,
                    BIC.OST_FurnitureSystems,
                    BIC.OST_PlumbingFixtures,
                    BIC.OST_Entourage,
                    ]:
    view_directions = {"Back": -6, "Front": -7, "Floor Plan": -8, "Right": -9, "Left": -10}
else:
    view_directions = {"Section": -5, "Back": -6, "Front": -7, "Floor Plan": -8, "Right": -9, "Left": -10}
view_dir = forms.SelectFromList.show(view_directions.keys(),
                                     button_name="Select view direction",
                                     title="View Direction",
                                     height=300,
                                     width=350,
                                     multiselect=False)
if not view_dir:
    sys.exit()
chosen_view_direction = view_directions[view_dir]

source_legend_component = DB.FilteredElementCollector(doc, legend.Id).OfCategory(
    BIC.OST_LegendComponents).FirstElement()
forms.alert_ifnot(source_legend_component, "The legend must have at least one source Legend Component to copy",
                  exitscript=True)

collect_symbols = DB.FilteredElementCollector(doc) \
    .OfCategory(chosen_bic).WhereElementIsElementType()

source_element = source_legend_component
ordered_symbols = {}

for sym in collect_symbols:
    # cat = sym.get_Parameter(DB.BuiltInParameter.ELEM_CATEGORY_PARAM).AsValueString()
    fam = sym.get_Parameter(DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM).AsString()
    typ = sym.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
    if fam not in ordered_symbols.keys():
        ordered_symbols[fam] = {}
    ordered_symbols[fam][typ] = sym

spacing = 1


def transform_point(point, transform):
    x = point.X
    y = point.Y
    z = point.Z

    basisX = transform.get_Basis(0)
    basisY = transform.get_Basis(1)
    basisZ = transform.get_Basis(2)
    origin = transform.Origin

    xnew = x * basisX.X + y * basisY.X + z * basisZ.X + origin.X
    ynew = x * basisX.Y + y * basisY.Y + z * basisZ.Y + origin.Y
    znew = x * basisX.Z + y * basisY.Z + z * basisZ.Z + origin.Z

    return DB.XYZ(xnew, ynew, znew)


with forms.WarningBar(title="Pick Placement Point"):
    try:
        pt = revit.uidoc.Selection.PickPoint()
    except Exceptions.OperationCanceledException:
        forms.alert("Cancelled", ok=True, exitscript=True)

bbox_source_element = source_element.get_BoundingBox(legend)
bbox_source_center = bbox_source_element.Max - bbox_source_element.Min
source_transform = [x for x in source_element.get_Geometry(DB.Options())][0].Transform.Inverse

initial_translation = transform_point(pt, source_transform)
added_translation = DB.XYZ(0, 0, 0)
with revit.Transaction("List Symbols"):
    for fam in ordered_symbols:
        for fam_type in ordered_symbols[fam]:
            symbol = ordered_symbols[fam][fam_type]
            # CHANGE TYPE HERE
            try:
                copy_component_id = DB.ElementTransformUtils.CopyElement(doc, source_element.Id, initial_translation)[0]
                new_component = doc.GetElement(copy_component_id)
                new_component.get_Parameter(DB.BuiltInParameter.LEGEND_COMPONENT).Set(symbol.Id)

                new_component.get_Parameter(DB.BuiltInParameter.LEGEND_COMPONENT_VIEW).Set(chosen_view_direction)
                doc.Regenerate()
                bb = new_component.get_BoundingBox(legend)
                bb_width = bb.Max.X - bb.Min.X
                added_translation = added_translation + DB.XYZ(bb_width + spacing, 0, 0)
                DB.ElementTransformUtils.MoveElement(doc, copy_component_id, added_translation)
            except EnvironmentError:
                pass
        added_translation = added_translation + DB.XYZ(spacing * 2, 0, 0)
