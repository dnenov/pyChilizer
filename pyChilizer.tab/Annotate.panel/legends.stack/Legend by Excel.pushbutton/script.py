"""Create a colour legend from an excel table. The table must consist of two columns, [A] Name [B] Colour in R-G-B format (ex. 255-180-80).
 Find a template in the folder. To open the script folder, ALT+CLICK the button.
 You can chose if you want to use/create the Filled Region types matching the name or use visibility overrides."""
from pyrevit.framework import List
from pyrevit import revit, DB, forms, script
from pyrevit.compat import get_elementid_value_func
import xlrd
from rpw.ui.forms import (FlexForm, Label, ComboBox, Separator, Button, TextBox)
from collections import OrderedDict
from Autodesk.Revit import Exceptions
from pychilizer import units, database


config = script.get_config()

get_elementid_value = get_elementid_value_func()

def translate_rectg_vert(rec, vert_offset):
    # offset recgtangles with a given vertical offset
    position = vert_offset
    vector = DB.XYZ(0, -1, 0) * position
    transform = DB.Transform.CreateTranslation(vector)
    return [cv.CreateTransformed(transform) for cv in rec]


def reformat_colour(col_sting):
    # reformat strings representing colour and create elements of type DB.Color
    new_col = col_sting.replace("-", " ")
    rgb_str = new_col.split()
    r = int(rgb_str[0])
    g = int(rgb_str[1])
    b = int(rgb_str[2])
    return DB.Color(r, g, b)


def get_next_key(cur_key, dict):
    next_key = None
    temp_dict = iter(dict.keys())
    for key in temp_dict:
        if key == cur_key:
            next_key = next(temp_dict, None)
    return next_key


def draw_rectangle(y_offset, fill_type, view, line_style):
    # draw a filled region of any type with a specified y offset
    rectangle_outlines = translate_rectg_vert(orig_rectangle, y_offset)
    crv_loop = DB.CurveLoop.Create(List[DB.Curve](rectangle_outlines))
    new_reg = DB.FilledRegion.Create(revit.doc, fill_type.Id, view.Id, [crv_loop])
    new_reg.SetLineStyleId(line_style.Id)
    return new_reg


def invis_style(doc=revit.doc):
    # get invisible lines graphics style
    for gs in DB.FilteredElementCollector(doc).OfClass(DB.GraphicsStyle):
        # find style using the category Id
        if get_elementid_value(gs.GraphicsStyleCategory.Id) == -2000064:
            return gs


def get_any_text_type_id():
    # get a default text note type - to replace later
    txt_type = revit.doc.GetElement(revit.doc.GetDefaultElementTypeId(DB.ElementTypeGroup.TextNoteType))
    return txt_type.Id


def find_filled_reg(name):
    fr_types = DB.FilteredElementCollector(revit.doc).OfClass(DB.FilledRegionType)
    found = None
    for fr_type in fr_types:
        if fr_type.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString() == name:
            found = fr_type
    return found


view = revit.active_view

# pick excel file and read
with forms.WarningBar(title="Pick excel file with colour scheme"):
    path = forms.pick_file(file_ext='xlsx')
if path:
    book = xlrd.open_workbook(path)

    worksheet = book.sheet_by_index(0)

    # create ordered dictionary to preserve order
    colour_scheme_od = OrderedDict()
    for i in range(0, worksheet.nrows):
        comp = worksheet.cell_value(i, 0)
        colour_raw = worksheet.cell_value(i, 1)
        colour = reformat_colour(colour_raw)
        colour_scheme_od[comp] = colour

    # get all text styles to choose from
    txt_types = DB.FilteredElementCollector(revit.doc).OfClass(DB.TextNoteType)
    text_style_dict = {txt_t.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString(): txt_t for txt_t in txt_types}

    # construct rwp UI
    components = [
        Label("Pick Text Style"),
        ComboBox(name="textstyle_combobox", options=text_style_dict),
        Label("Box Width [mm]"),
        TextBox(name="box_width", Text="1000"),
        Label("Box Height [mm]"),
        TextBox(name="box_height", Text="240"),
        Label("Offset [mm]"),
        TextBox(name="box_offset", Text="80"),
        Label("Create new Filled Region Types"),
        ComboBox(name="create_new", options={"Create New Filled Region Types": True, "Use Overrides": False}),
        Button("Select")]
    form = FlexForm("Appearance", components)
    form.show()
    # assign chosen values to variables
    chosen_text_style = form.values["textstyle_combobox"]
    box_width = int(form.values["box_width"])
    box_height = int(form.values["box_height"])
    box_offset = int(form.values["box_offset"])
    create_new_fill_types = form.values["create_new"]

    # dims and scale
    scale = float(view.Scale) / 100
    w = units.convert_length_to_internal(box_width) * scale
    h = units.convert_length_to_internal(box_height) * scale
    text_offset = 1 * scale
    shift = (units.convert_length_to_internal(box_offset + box_height)) * scale

    with forms.WarningBar(title="Pick Point"):
        try:
            pt = revit.uidoc.Selection.PickPoint()
        except Exceptions.OperationCanceledException:
            forms.alert("Cancelled", ok=True, exitscript=True)


    # create rectrangle
    crv_loop = DB.CurveLoop()
    p1 = DB.XYZ(pt.X, pt.Y, 0)
    p2 = DB.XYZ(pt.X + w, pt.Y, 0)
    p3 = DB.XYZ(pt.X + w, pt.Y + h, 0)
    p4 = DB.XYZ(pt.X, pt.Y + h, 0)

    # create lines between points
    l1 = DB.Line.CreateBound(p1, p2)
    l2 = DB.Line.CreateBound(p2, p3)
    l3 = DB.Line.CreateBound(p3, p4)
    l4 = DB.Line.CreateBound(p4, p1)
    orig_rectangle = [l1, l2, l3, l4]

    offset = 0

    i_s = invis_style()
    a_f_t = database.any_fill_type()
    solid_fill = database.get_solid_fill_pat()

    with revit.Transaction("Draw Legend"):
        for box_name in colour_scheme_od:
            # draw rectangles with filled region
            # if chosen to create new fill types
            if create_new_fill_types:
                type_exists = find_filled_reg(box_name)
                if type_exists:
                    # if there's a filled region with that name, use that type with existing filled region type
                    chosen_fr_type = type_exists
                    chosen_fr_type.ForegroundPatternColor = colour_scheme_od[box_name]
                else:
                    chosen_fr_type = a_f_t.Duplicate(box_name)
                    chosen_fr_type.ForegroundPatternColor = colour_scheme_od[box_name]
                    chosen_fr_type.ForegroundPatternId = solid_fill.Id
                # draw a region of that existing or created filled region type
                new_reg = draw_rectangle(offset, chosen_fr_type, view, i_s)
            # if user chose to use overrides
            else:
                new_reg = draw_rectangle(offset, a_f_t, view, i_s)
                # override fill and colour
                ogs = DB.OverrideGraphicSettings()
                ogs.SetSurfaceForegroundPatternColor(colour_scheme_od[box_name])
                ogs.SetSurfaceForegroundPatternId(solid_fill.Id)
                view.SetElementOverrides(new_reg.Id, ogs)

            # place text next to filled regions
            label_position = DB.XYZ(pt.X+w + text_offset, pt.Y-(offset - h), 0)
            label_txt = str(box_name)
            text_note = DB.TextNote.Create(revit.doc, view.Id, label_position, label_txt, chosen_text_style.Id)

            # keep offsetting y
            offset += shift

