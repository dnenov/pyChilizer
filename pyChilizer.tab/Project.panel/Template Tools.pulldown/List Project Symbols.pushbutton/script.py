"""List Project Symbols on a Legend View"""

from pyrevit import revit, DB, UI, forms, script
from pyrevit.framework import List
from collections import OrderedDict
from Autodesk.Revit import Exceptions


def convert_length_to_internal(from_units):
    # convert length units from project  to internal
    d_units = DB.Document.GetUnits(revit.doc).GetFormatOptions(DB.UnitType.UT_Length).DisplayUnits
    converted = DB.UnitUtils.ConvertToInternalUnits(from_units, d_units)
    return converted


def convert_length_from_internal(from_units):
    # convert length units from project  to internal
    d_units = DB.Document.GetUnits(revit.doc).GetFormatOptions(DB.UnitType.UT_Length).DisplayUnits
    converted = DB.UnitUtils.ConvertFromInternalUnits(from_units,d_units)
    return converted


def get_any_text_type_id():
    # get a default text note type - to replace later
    txt_type = revit.doc.GetElement(revit.doc.GetDefaultElementTypeId(DB.ElementTypeGroup.TextNoteType))
    return txt_type.Id


view = revit.active_view
if view.ViewType != DB.ViewType.Legend:
    forms.alert("View is not a Legend View", exitscript=True)

categories = [
    DB.BuiltInCategory.OST_DoorTags,
    DB.BuiltInCategory.OST_WindowTags,
    DB.BuiltInCategory.OST_RoomTags,
    DB.BuiltInCategory.OST_AreaTags,
    DB.BuiltInCategory.OST_WallTags,
    DB.BuiltInCategory.OST_CurtainWallPanelTags,
    DB.BuiltInCategory.OST_SectionHeads,
    DB.BuiltInCategory.OST_CalloutHeads,
    DB.BuiltInCategory.OST_CeilingTags,
    DB.BuiltInCategory.OST_FurnitureTags,
    DB.BuiltInCategory.OST_PlumbingFixtureTags,
    DB.BuiltInCategory.OST_ReferenceViewerSymbol,
    DB.BuiltInCategory.OST_GridHeads,
    DB.BuiltInCategory.OST_LevelHeads,
    DB.BuiltInCategory.OST_SpotElevSymbols,
    DB.BuiltInCategory.OST_ElevationMarks,
    DB.BuiltInCategory.OST_StairsTags,
    DB.BuiltInCategory.OST_StairsLandingTags,
    DB.BuiltInCategory.OST_StairsRunTags,
    DB.BuiltInCategory.OST_StairsSupportTags,
    DB.BuiltInCategory.OST_BeamSystemTags,
    DB.BuiltInCategory.OST_StructuralFramingTags,
    DB.BuiltInCategory.OST_ViewportLabel
]

cat_list = List[DB.BuiltInCategory](categories)
multicat_filter = DB.ElementMulticategoryFilter(cat_list)
collect_tags = DB.FilteredElementCollector(revit.doc)\
    .WherePasses(multicat_filter).WhereElementIsElementType()

ordered_symbols = OrderedDict()

for sym in collect_tags:
    cat = sym.get_Parameter(DB.BuiltInParameter.ELEM_CATEGORY_PARAM).AsValueString()
    fam = sym.get_Parameter(DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM).AsString()
    typ = sym.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
    if cat not in ordered_symbols.keys():
        ordered_symbols[cat]=OrderedDict()
    if fam not in ordered_symbols[cat].keys():
        ordered_symbols[cat][fam]=OrderedDict()
    ordered_symbols[cat][fam][typ] = sym


# any_legend_component = DB.FilteredElementCollector(revit.doc, view.Id) \
#     .OfCategory(DB.BuiltInCategory.OST_LegendComponents) \
#     .FirstElement()

# forms.alert_ifnot(any_legend_component, "No Legend Components in View", exitscript=True)
scale = float(view.Scale)/ 100
offset = 5 *scale
line_length = 2
text_offset = 5 * scale

with forms.WarningBar(title="Pick Point"):
    try:
        pt = revit.uidoc.Selection.PickPoint()
    except Exceptions.OperationCanceledException:
        forms.alert("Cancelled", ok=True, exitscript=True)

position = pt
with revit.Transaction("List Symbols"):
    for cat in sorted(ordered_symbols):
        cat_label_position = DB.XYZ(position.X-text_offset, position.Y, 0)
        cat_text_note = DB.TextNote.Create(revit.doc, view.Id, cat_label_position, cat, get_any_text_type_id())
        cat_txt = cat_text_note.GetFormattedText()
        cat_txt.SetBoldStatus(True)
        cat_txt.SetAllCapsStatus(True)
        cat_text_note.SetFormattedText(cat_txt)
        position = DB.XYZ(pt.X, (position.Y-offset), 0)
        for fam in ordered_symbols[cat]:
            label_position = DB.XYZ(position.X, position.Y, 0)
            f_text_note = DB.TextNote.Create(revit.doc, view.Id, label_position, fam, get_any_text_type_id())
            f_txt= f_text_note.GetFormattedText()
            f_txt.SetBoldStatus(True)
            f_text_note.SetFormattedText(f_txt)
            position = DB.XYZ(pt.X, (position.Y-offset), 0)
            for fam_type in ordered_symbols[cat][fam]:
                sym = ordered_symbols[cat][fam][fam_type]
                if not sym.IsActive:
                    sym.Activate()
                new_tag_symbol = revit.doc.Create.NewFamilyInstance(position, sym, view)
                revit.doc.Regenerate()
                bb = new_tag_symbol.get_BoundingBox(view)
                bb_h = bb.Max.Y - bb.Min.Y
                label_position = DB.XYZ(position.X + text_offset, position.Y, 0)
                text_note = DB.TextNote.Create(revit.doc, view.Id, label_position, fam_type, get_any_text_type_id())
                position = DB.XYZ(pt.X, (position.Y-(bb_h*scale)-offset*0.5), 0)
            position = DB.XYZ(pt.X, (position.Y-offset), 0)
        position = DB.XYZ(pt.X, (position.Y - offset*0.5), 0)
