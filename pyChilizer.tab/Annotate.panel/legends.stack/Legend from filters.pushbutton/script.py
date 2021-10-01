"""Draw Legend based on View Filters of a chosen view"""

from pyrevit import revit, DB, UI, forms
from collections import defaultdict
from rpw.ui.forms import (FlexForm, Label, ComboBox, Separator, Button)
from collections import OrderedDict
from pyrevit.framework import List


def get_solid_fill_pat():
    # get fill pattern element Solid Fill
    fill_pats = DB.FilteredElementCollector(revit.doc).OfClass(DB.FillPatternElement)
    solid_pat = [pat for pat in fill_pats if str(pat.Name) == "<Solid fill>"]
    return solid_pat[0]


def translate_rectg_vert (rec, vert_offset):
    # offset recgtangles with a given vertical offset
    position = vert_offset
    vector = DB.XYZ(0,-1,0) * position
    transform = DB.Transform.CreateTranslation(vector)
    return [cv.CreateTransformed(transform) for cv in rec]


def any_fill_type():
    # get any Filled Region Type
    return DB.FilteredElementCollector(revit.doc).OfClass(DB.FilledRegionType).FirstElement()


col_views = DB.FilteredElementCollector(revit.doc).OfClass(DB.View).WhereElementIsNotElementType()

# TODO: Sort out views with no filters
# prep options
view_dict1 = {v.Name: v for v in col_views}

# get all text styles to choose from
txt_types = DB.FilteredElementCollector(revit.doc).OfClass(DB.TextNoteType)
text_style_dict= {txt_t.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString(): txt_t for txt_t in txt_types}

# construct rwp UI
components = [
    Label("Pick Source View:"),
    ComboBox(name="view_combobox", options=view_dict1),
    Label("Pick Text Style"),
    ComboBox(name="textstyle_combobox", options=text_style_dict),
    Label("Pick Colour Source"),
    ComboBox(name="coloursource_combobox", options=["Cut", "Projection"]),
    Button("Select")
]
form = FlexForm("Select", components)
form.show()
# assign chosen parameters
src_view = form.values["view_combobox"]
text_style = form.values["textstyle_combobox"]
colour_source = form.values["coloursource_combobox"]

legend_view = revit.active_view
view_filters = src_view.GetFilters()

legend_od = OrderedDict()

for f in view_filters:

    overrides = src_view.GetFilterOverrides(f)
    if colour_source == "Projection":
        filter_colour = overrides.SurfaceForegroundPatternColor
    else:
        filter_colour = overrides.CutForegroundPatternColor
    filter_name = revit.doc.GetElement(f).Name
    legend_od[filter_name] = filter_colour


# dims and scale
scale = float(legend_view.Scale)/100
w = 3.25 * scale
h = 1.3 * scale
text_offset = 1 * scale
shift = 2.32 * scale
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

rectangle = [l1, l2, l3, l4]

offset = 0
origin = DB.XYZ(0,0,0)


with revit.Transaction("Draw Legend"):
    for v_filter in legend_od:

        t1 = DB.Transform.CreateTranslation(DB.XYZ(0, -shift, 0))
        rectangle = [line.CreateTransformed(t1) for line in rectangle]
        crv_loop = DB.CurveLoop.Create(List[DB.Curve](rectangle))

        # draw rectangles with filled region
        new_reg = DB.FilledRegion.Create(revit.doc, any_fill_type().Id, legend_view.Id, [crv_loop])

        # override fill and colour
        ogs = DB.OverrideGraphicSettings()
        colour = legend_od[v_filter]
        ogs.SetSurfaceForegroundPatternColor(legend_od[v_filter])
        ogs.SetSurfaceForegroundPatternId(get_solid_fill_pat().Id)
        legend_view.SetElementOverrides(new_reg.Id, ogs)

        # place text next to filled regions
        t2 = DB.Transform.CreateTranslation(DB.XYZ(text_offset, 0, 0))
        label_position = rectangle[1].CreateTransformed(t2).GetEndPoint(1)
        label_txt = str(v_filter)
        text_note = DB.TextNote.Create(revit.doc, legend_view.Id, label_position, label_txt, text_style.Id)

