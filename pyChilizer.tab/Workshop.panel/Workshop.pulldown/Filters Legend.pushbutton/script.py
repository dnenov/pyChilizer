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


def draw_rectangle(y_offset, fill_type, view):
    # draw a filled region of any type with a specified y offset
    rectangle_outlines = translate_rectg_vert(orig_rectangle, y_offset)
    crv_loop = DB.CurveLoop.Create(List[DB.Curve](rectangle_outlines))
    new_reg = DB.FilledRegion.Create(revit.doc, fill_type.Id, view.Id, [crv_loop])
    return new_reg


def any_fill_type():
    # get any Filled Region Type
    return DB.FilteredElementCollector(revit.doc).OfClass(DB.FilledRegionType).FirstElement()


def get_any_text_type_id():
    # get a default text note type - to replace later
    txt_type = revit.doc.GetElement(revit.doc.GetDefaultElementTypeId(DB.ElementTypeGroup.TextNoteType))
    return txt_type.Id


col_views = DB.FilteredElementCollector(revit.doc).OfClass(DB.View).WhereElementIsNotElementType()

# TODO: Sort out views with no filters
# prep options
view_dict1 = {v.Name: v for v in col_views}
#gm_dict2 = {p.Definition.Name: p for p in gm_params_area}


forms.select_views(title="Select Target View", multiple=False)

# construct rwp UI
components = [
    Label("Pick Source View:"),
    ComboBox(name="view_combobox1", options=view_dict1),
    Button("Select")]
form = FlexForm("Pick Source View", components)
form.show()
# assign chosen parameters
src_view = form.values["view_combobox1"]

# TODO: select target view
legend_view = revit.active_view
view_filters = src_view.GetFilters()

legend_od = OrderedDict()

for f in view_filters:
#    print (src_view.GetFilterOverrides(f))
    overrides = src_view.GetFilterOverrides(f)
    foreground_colour = overrides.SurfaceForegroundPatternColor
    filter_name = revit.doc.GetElement(f).Name
    legend_od[filter_name] = foreground_colour


# dims and scale
scale = 1
w = 8 * scale
h = 4 * scale
text_offset = 1 * scale
shift = 6 * scale
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

#print (legend_od)

with revit.Transaction("do smth"):
    for v_filter in legend_od:

        print (v_filter)
        # draw rectangles with filled region
        new_reg = draw_rectangle(offset, any_fill_type(),legend_view)
        # override fill and colour
        ogs = DB.OverrideGraphicSettings()
        colour = legend_od[v_filter]
        print ("Colour", colour)
        ogs.SetSurfaceForegroundPatternColor(legend_od[v_filter])
        ogs.SetSurfaceForegroundPatternId(get_solid_fill_pat().Id)
        legend_view.SetElementOverrides(new_reg.Id, ogs)

        # place text next to filled regions
        label_position = DB.XYZ(w+text_offset, -(offset-h), 0)
        label_txt = str(v_filter)
        text_note = DB.TextNote.Create(revit.doc, legend_view.Id, label_position, label_txt, get_any_text_type_id())

        # keep offsetting y
        offset += shift
        # offset again before starting a new group
        origin = DB.XYZ(origin.X, -(offset), origin.Z)
        offset += shift

