"""First attempt to create a colour legend from excel"""


import itertools
from collections import defaultdict
from pyrevit.framework import List
from pyrevit import HOST_APP
from pyrevit import forms
from pyrevit import revit, DB
from pyrevit import script
from pyrevit import revit, DB, forms, script
import xlrd
from rpw.ui.forms import (FlexForm, Label, ComboBox, Separator, Button)
import sys
from itertools import izip
from collections import OrderedDict


def any_fill_type():
    # get any Filled Region Type
    return DB.FilteredElementCollector(revit.doc).OfClass(DB.FilledRegionType).FirstElement()


def translate_rectg_vert (rec, vert_offset):
    # offset recgtangles with a given vertical offset
    position = vert_offset
    vector = DB.XYZ(0,-1,0) * position
    transform = DB.Transform.CreateTranslation(vector)
    return [cv.CreateTransformed(transform) for cv in rec]


def get_solid_fill_pat(doc=revit.doc):
    # get fill pattern element Solid Fill
    fill_pats = DB.FilteredElementCollector(doc).OfClass(DB.FillPatternElement)
    solid_pat = [pat for pat in fill_pats if str(pat.Name) == "<Solid fill>"]
    return solid_pat[0]


def reformat_colour(col_sting):
    # reformat strings representing colour and create elements of type DB.Color
    new_col = col_sting.replace("-", " ")
    rgb_str = new_col.split()
    r = int(rgb_str[0])
    g = int(rgb_str[1])
    b = int(rgb_str[2])
    return DB.Color(r,g,b)


def place_header_text (header_text, header_position, text_style):
    header_note = DB.TextNote.Create(revit.doc, view.Id, header_position, header_text, text_style.Id)
    return header_note


def header_pos(crv_loop):
    start_pt = crv_loop[0].GetEndPoint(0)
    header_position = DB.XYZ(start_pt.X, start_pt.Y + h_offset, 0 )
    return header_position


def get_next_key(cur_key, dict):
    next_key = None
#    temp_dict = iter(colour_od.keys())
    temp_dict = iter(dict.keys())
    for key in temp_dict:
        if key == cur_key:
            next_key = next(temp_dict, None)
    return next_key


def draw_rectangle(y_offset, fill_type, view):
    # draw a filled region of any type with a specified y offset
    rectangle_outlines = translate_rectg_vert(orig_rectangle, y_offset)
    crv_loop = DB.CurveLoop.Create(List[DB.Curve](rectangle_outlines))
    new_reg = DB.FilledRegion.Create(revit.doc, fill_type.Id, view.Id, [crv_loop])
    return new_reg


view = revit.active_view

# pick excel file and read
with forms.WarningBar(title="Pick excel file with colour scheme"):
    path = forms.pick_file(file_ext='xlsx', init_dir="M:\BIM\BIM Manual\Colour Scheme Table")

book = xlrd.open_workbook(path)
worksheet = book.sheet_by_index(0)

def get_any_text_type_id():
    # get a default text note type - to replace later
    txt_type = revit.doc.GetElement(revit.doc.GetDefaultElementTypeId(DB.ElementTypeGroup.TextNoteType))
    return txt_type.Id

# create ordered dictionary
colour_scheme_od = OrderedDict()
for i in range(0, worksheet.nrows):
    h1 = worksheet.cell_value(i,0)
    comp = worksheet.cell_value(i, 1)
    colour_raw = worksheet.cell_value(i, 2)
    colour = reformat_colour(colour_raw)
    if h1 not in colour_scheme_od.keys():
        colour_scheme_od[h1] = OrderedDict()
    colour_scheme_od[h1][comp] = colour

txt_types = DB.FilteredElementCollector(revit.doc).OfClass(DB.TextNoteType)


text_style_dict= {txt_t.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString(): txt_t for txt_t in txt_types}
#gm_dict2 = {p.Definition.Name: p for p in gm_params_area}
# construct rwp UI
components = [
    Label("Pick Text Style:"),
    ComboBox(name="textstyle_combobox1", options=text_style_dict),
    Button("Select")]
form = FlexForm("Appearance", components)
form.show()
# assign chosen parameters
chosen_text_style = form.values["textstyle_combobox1"]

# dims and scale
scale = 1
w = 6.25 * scale
h = 2.6 * scale
text_offset = 1 * scale
shift = 5 * scale
h_offset = 10*scale
# create rectrangle
crv_loop = DB.CurveLoop()

p1 = DB.XYZ(0, 0, 0)
p2 = DB.XYZ(w, 0, 0)
p3 = DB.XYZ(w, h, 0)
p4 = DB.XYZ(0, h, 0)

# create lines between points
l1 = DB.Line.CreateBound(p1, p2)
l2 = DB.Line.CreateBound(p2, p3)
l3 = DB.Line.CreateBound(p3, p4)
l4 = DB.Line.CreateBound(p4, p1)

orig_rectangle = [l1, l2, l3, l4]

offset = 0
origin = DB.XYZ(0,shift,0)

with revit.Transaction("Draw Legend"):
    for header in colour_scheme_od:
        # place header for group of items
        header_position = origin
        header_text = place_header_text(header, header_position, chosen_text_style)
        formatted = header_text.GetFormattedText()
        formatted.SetBoldStatus(True)
        header_text.SetFormattedText(formatted)


        offset += shift*0.75
        origin = DB.XYZ(origin.X, -(offset), origin.Z)
        for component in colour_scheme_od[header]:
            # draw rectangles with filled region
            new_reg = draw_rectangle(offset, any_fill_type(), view)
            # override fill and colour
            ogs = DB.OverrideGraphicSettings()
            ogs.SetSurfaceForegroundPatternColor(colour_scheme_od[header][component])
            ogs.SetSurfaceForegroundPatternId(get_solid_fill_pat().Id)
            view.SetElementOverrides(new_reg.Id, ogs)

            # place text next to filled regions
            label_position = DB.XYZ(w+text_offset, -(offset-h), 0)
            label_txt = str(component)
            text_note = DB.TextNote.Create(revit.doc, view.Id, label_position, label_txt, chosen_text_style.Id)

            # keep offsetting y
            offset += shift
        # offset again before starting a new group
        origin = DB.XYZ(origin.X, -(offset), origin.Z)
        offset += shift


