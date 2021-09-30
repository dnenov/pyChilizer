"""List Detail Items"""

from pyrevit import revit, DB, UI, HOST_APP, forms, script


def get_any_text_type_id():
    # get a default text note type - to replace later
    txt_type = revit.doc.GetElement(revit.doc.GetDefaultElementTypeId(DB.ElementTypeGroup.TextNoteType))
    return txt_type.Id


coll_dc_types = DB.FilteredElementCollector(revit.doc).OfCategory(DB.BuiltInCategory.OST_DetailComponents).OfClass(DB.FamilySymbol).WhereElementIsElementType()

dc_viewbased = [dc for dc in coll_dc_types if dc.Family.FamilyPlacementType == DB.FamilyPlacementType.ViewBased]
dc_curvebased = [dc for dc in coll_dc_types if dc.Family.FamilyPlacementType == DB.FamilyPlacementType.CurveBasedDetail]


view = revit.active_view

symbol_origin = DB.XYZ(0,0,0)
text_origin = DB.XYZ(2,0,0)
vertical_spacing = 2
line_length = 2

with revit.Transaction("do something"):
    for dc in dc_viewbased:

        new_dc_viewbased = revit.doc.Create.NewFamilyInstance(symbol_origin, dc, view)
        fam_name = " : ".join(["Family", dc.Family.Name])
        type_name = " : ".join(["Type", str(dc.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString())])
        label_text = "\n".join([fam_name, type_name])

        text_note = DB.TextNote.Create(revit.doc, view.Id, text_origin, label_text, get_any_text_type_id())

        symbol_origin = DB.XYZ(0, symbol_origin.Y - vertical_spacing, 0)
        text_origin = DB.XYZ(text_origin.X, text_origin.Y - vertical_spacing, 0)



    for dcc in dc_curvebased:

        p1 = DB.XYZ(0, symbol_origin.Y, 0)
        p2 = DB.XYZ(line_length, symbol_origin.Y, 0 )

        curve = DB.Line.CreateBound(p1, p2)
        new_dc_curvebased = revit.doc.Create.NewFamilyInstance(curve, dcc, view)

        fam_name = " : ".join(["Family", dcc.Family.Name])
        type_name = " : ".join(["Type", str(dcc.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString())])
        label_text = "\n".join([fam_name, type_name])

        text_note = DB.TextNote.Create(revit.doc, view.Id, text_origin, label_text, get_any_text_type_id())

        symbol_origin = DB.XYZ(0, symbol_origin.Y - vertical_spacing, 0)
        text_origin = DB.XYZ(text_origin.X, text_origin.Y - vertical_spacing, 0)