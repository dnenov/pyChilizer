"""Draw a Legend based on View Filters of a chosen view.
View Filters with no overrides will be discarded."""

from pyrevit import revit, DB, UI, forms
from rpw.ui.forms import (FlexForm, Label, ComboBox, Separator, Button, TextBox)
from pyrevit.framework import List
from Autodesk.Revit import Exceptions
from pychilizer import units, database


def translate_rectg_vert(rec, vert_offset):
    # offset recgtangles with a given vertical offset
    position = vert_offset
    vector = DB.XYZ(0, -1, 0) * position
    transform = DB.Transform.CreateTranslation(vector)
    return [cv.CreateTransformed(transform) for cv in rec]


def draw_rectangle(y_offset, fill_type, view, line_style):
    # draw a filled region of any type with a specified y offset
    rectangle_outlines = translate_rectg_vert(rectangle, y_offset)
    crv_loop = DB.CurveLoop.Create(List[DB.Curve](rectangle_outlines))
    new_reg = DB.FilledRegion.Create(revit.doc, fill_type.Id, view.Id, [crv_loop])
    new_reg.SetLineStyleId(line_style.Id)
    return new_reg


col_views = DB.FilteredElementCollector(revit.doc).OfClass(DB.View).WhereElementIsNotElementType()

allowed_view_types = [
    DB.ViewType.FloorPlan,
    DB.ViewType.CeilingPlan,
    DB.ViewType.Elevation,
    DB.ViewType.ThreeD,
    DB.ViewType.DraftingView,
    DB.ViewType.AreaPlan,
    DB.ViewType.Section,
    DB.ViewType.Detail,
    DB.ViewType.Legend
]

views_with_filters = [view for view in col_views if view.ViewType in allowed_view_types and view.GetFilters()]

# prep options
view_dict1 = {v.Name: v for v in views_with_filters}
forms.alert_ifnot(view_dict1, "No views with filters", exitscript=True)

# get all text styles to choose from
txt_types = DB.FilteredElementCollector(revit.doc).OfClass(DB.TextNoteType)
text_style_dict = {txt_t.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString(): txt_t for txt_t in txt_types}

# construct rwp UI
components = [
    Label("Pick Source View:"),
    ComboBox(name="view_combobox", options=view_dict1),
    Label("Pick Text Style"),
    ComboBox(name="textstyle_combobox", options=text_style_dict),
    Label("Pick Colour Source"),
    ComboBox(name="coloursource_combobox", options=["Cut", "Projection"]),
    Label("Box Width [mm]"),
    TextBox(name="box_width", Text="1000"),
    Label("Box Height [mm]"),
    TextBox(name="box_height", Text="240"),
    Label("Offset [mm]"),
    TextBox(name="box_offset", Text="80"),
    Button("Select")
]
form = FlexForm("Select", components)
result = form.show()
if not result:
    forms.alert("Cancelled", ok=True, exitscript=True)

# assign chosen parameters
src_view = form.values["view_combobox"]
chosen_text_style = form.values["textstyle_combobox"]
colour_source = form.values["coloursource_combobox"]
box_width = int(form.values["box_width"])
box_height = int(form.values["box_height"])
box_offset = int(form.values["box_offset"])

view = revit.active_view
view_filters = src_view.GetFilters()

legend_od = {}

for f in view_filters:
    overrides = src_view.GetFilterOverrides(f)
    filter_name = None
    filter_colour = None
    filter_pat_id = None
    # record override colour while discarding filters with no overrides
    if colour_source == "Projection" and (
            overrides.SurfaceForegroundPatternColor.IsValid or overrides.SurfaceBackgroundPatternColor.IsValid):
        filter_colour = overrides.SurfaceForegroundPatternColor
        filter_pat_id = overrides.SurfaceForegroundPatternId
        # if the foreground override is empty, use background override
        if not filter_colour.IsValid:
            filter_colour = overrides.SurfaceBackgroundPatternColor
            filter_pat_id = overrides.SurfaceBackgroundPatternId

        filter_name = revit.doc.GetElement(f).Name
        legend_od[filter_name] = {filter_colour: filter_pat_id}
    elif colour_source == "Projection" and (not overrides.SurfaceForegroundPatternColor.IsValid) and (not overrides.SurfaceBackgroundPatternColor.IsValid):
        filter_colour = overrides.ProjectionLineColor
        filter_pat_id = database.get_solid_fill_pat().Id

        filter_name = revit.doc.GetElement(f).Name
        legend_od[filter_name] = {filter_colour: filter_pat_id}
    # same for cut settings
    elif colour_source == "Cut" and (
            overrides.CutForegroundPatternColor.IsValid or overrides.CutBackgroundPatternColor.IsValid):
        filter_colour = overrides.CutForegroundPatternColor
        filter_pat_id = overrides.CutForegroundPatternId
        if not filter_colour.IsValid:
            filter_colour = overrides.CutBackgroundPatternColor
            filter_pat_id = overrides.CutBackgroundPatternId
        filter_name = revit.doc.GetElement(f).Name
        legend_od[filter_name] = {filter_colour: filter_pat_id}

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
rectangle = [l1, l2, l3, l4]
offset = 0

# geting these two def out of the loop to avoid repetition
i_s = database.invis_style()
a_f_t = database.any_fill_type()
solid_fill = database.get_solid_fill_pat()

with revit.Transaction("Draw Legend"):
    for v_filter in sorted(legend_od):

        # draw rectangles with filled region
        new_reg = draw_rectangle(offset, a_f_t, view, i_s)

        # override fill and colour
        ogs = DB.OverrideGraphicSettings()
        colour = legend_od[v_filter].keys()[0]
        ogs.SetSurfaceForegroundPatternColor(colour)
        pat_id = legend_od[v_filter].values()[0]
        if pat_id == DB.ElementId.InvalidElementId:
            pat_id = solid_fill.Id
        ogs.SetSurfaceForegroundPatternId(pat_id)
        view.SetElementOverrides(new_reg.Id, ogs)

        # place text next to filled regions
        label_position = DB.XYZ(pt.X + w + text_offset, pt.Y - (offset - h), 0)
        label_txt = str(v_filter)
        text_note = DB.TextNote.Create(revit.doc, view.Id, label_position, label_txt, chosen_text_style.Id)

        offset += shift
