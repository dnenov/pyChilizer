"""List Project Symbols on a Legend View

Shitf-Click
Pick Symbol Categories
"""

from pyrevit import revit, DB, UI, forms, script
from pyrevit.framework import List
from collections import OrderedDict
from Autodesk.Revit import Exceptions
import listsymbolsconfig


def convert_length_to_internal(from_units):
    # convert length units from project  to internal
    d_units = DB.Document.GetUnits(revit.doc).GetFormatOptions(DB.UnitType.UT_Length).DisplayUnits
    converted = DB.UnitUtils.ConvertToInternalUnits(from_units, d_units)
    return converted


def get_any_text_type_id():
    # get a default text note type - to replace later
    txt_type = revit.doc.GetElement(revit.doc.GetDefaultElementTypeId(DB.ElementTypeGroup.TextNoteType))
    return txt_type.Id


view = revit.active_view
if view.ViewType != DB.ViewType.Legend:
    forms.alert("View is not a Legend View", exitscript=True)

categories = listsymbolsconfig.get_categories()
if not categories:
    categories = listsymbolsconfig.categories

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


scale = float(view.Scale)/ 100
offset = 5 *scale
text_offset = 5 * scale
column_offset = 30

with forms.WarningBar(title="Pick Point"):
    try:
        pt = revit.uidoc.Selection.PickPoint()
    except Exceptions.OperationCanceledException:
        forms.alert("Cancelled", ok=True, exitscript=True)

position = pt
counter = 1


with revit.Transaction("List Symbols"):
    for cat in sorted(ordered_symbols):
        counter +=1
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
