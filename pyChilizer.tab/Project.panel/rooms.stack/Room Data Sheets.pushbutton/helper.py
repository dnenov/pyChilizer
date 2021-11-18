from pyrevit import revit, DB, script, forms, HOST_APP, coreutils
from rpw.ui.forms import (FlexForm, Label, ComboBox, Separator, Button)
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
from Autodesk.Revit import Exceptions
import tempfile
import rpw
from pyrevit.revit.db import query
import math
from pyrevit.framework import List


# selection filter for rooms
class RoomsFilter(ISelectionFilter):
    def AllowElement(self, elem):
        try:
            if elem.Category.Id.IntegerValue == int(DB.BuiltInCategory.OST_Rooms):
                return True
            else:
                return False
        except AttributeError:
            return False

    def AllowReference(self, reference, position):
        try:
            if isinstance(revit.doc.GetElement(reference), DB.Room):
                return True
            else:
                return False
        except AttributeError:
            return False


def select_rooms_filter():
    # select elements while applying category filter
    try:
        with forms.WarningBar(title="Pick Rooms to transform"):
            selection = [revit.doc.GetElement(reference) for reference in rpw.revit.uidoc.Selection.PickObjects(
                ObjectType.Element, RoomsFilter())]
            return selection
    except Exceptions.OperationCanceledException:
        forms.alert("Cancelled", ok=True, warn_icon=False, exitscript=True)


def convert_length_to_internal(from_units):
    # convert length units from project  to internal
    d_units = DB.Document.GetUnits(revit.doc).GetFormatOptions(DB.UnitType.UT_Length).DisplayUnits
    converted = DB.UnitUtils.ConvertToInternalUnits(from_units, d_units)
    return converted


def param_set_by_cat(cat):
    # get all project type parameters of a given category
    # can be used to gather parameters for UI selection
    all_gm = DB.FilteredElementCollector(revit.doc).OfCategory(cat).WhereElementIsElementType().ToElements()
    parameter_set = []
    for gm in all_gm:
        params = gm.Parameters
        for p in params:
            if p not in parameter_set and p.IsReadOnly == False:
                parameter_set.append(p)
    return parameter_set


def preselection_with_filter(cat_name):
    # use pre-selection of elements, but filter them by given category name
    pre_selection = []
    for id in rpw.revit.uidoc.Selection.GetElementIds():
        sel_el = revit.doc.GetElement(id)
        if sel_el.Category.Name == cat_name:
            pre_selection.append(sel_el)
    return pre_selection


def inverted_transform(element, view):
    # get element location and return its inverted transform
    # can be used to translate geometry to 0,0,0 origin to recreate geometry inside a family
    el_location = element.Location.Point
    bb = element.get_BoundingBox(view)
    orig_cs = bb.Transform
    # Creates a transform that represents a translation via the specified vector.
    translated_cs = orig_cs.CreateTranslation(el_location)
    # Transform from the room location point to origin
    return translated_cs.Inverse


def room_bound_to_origin(room, translation):
    room_boundaries = DB.CurveArrArray()
    # get room boundary segments
    room_segments = room.GetBoundarySegments(DB.SpatialElementBoundaryOptions())
    # iterate through loops of segments and add them to the array
    for seg_loop in room_segments:
        curve_array = DB.CurveArray()
        for s in seg_loop:
            old_curve = s.GetCurve()
            new_curve = old_curve.CreateTransformed(translation)  # move curves to origin
            curve_array.Append(new_curve)
        room_boundaries.Append(curve_array)
    return room_boundaries


def get_ref_lvl_plane(family_doc):
    # from given family doc, return Ref. Level reference plane
    find_planes = DB.FilteredElementCollector(family_doc).OfClass(DB.SketchPlane)
    return [plane for plane in find_planes if plane.Name == "Ref. Level"]


def get_fam(some_name):
    fam_name_filter = query.get_biparam_stringequals_filter({DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM: some_name})
    found_fam = DB.FilteredElementCollector(revit.doc) \
        .OfCategory(DB.BuiltInCategory.OST_GenericModel) \
        .WherePasses(fam_name_filter) \
        .WhereElementIsNotElementType().ToElements()

    return found_fam


def get_sheet(some_number):
    sheet_nr_filter = query.get_biparam_stringequals_filter({DB.BuiltInParameter.SHEET_NUMBER: str(some_number)})
    found_sheet = DB.FilteredElementCollector(revit.doc) \
        .OfCategory(DB.BuiltInCategory.OST_Sheets) \
        .WherePasses(sheet_nr_filter) \
        .WhereElementIsNotElementType().ToElements()

    return found_sheet


def get_view(some_name):
    view_name_filter = query.get_biparam_stringequals_filter({DB.BuiltInParameter.VIEW_NAME: some_name})
    found_view = DB.FilteredElementCollector(revit.doc) \
        .OfCategory(DB.BuiltInCategory.OST_Views) \
        .WherePasses(view_name_filter) \
        .WhereElementIsNotElementType().ToElements()

    return found_view


def get_family_slow_way(name):
    # look for loaded families, workaround to deal with extra space
    get_loaded = DB.FilteredElementCollector(revit.doc) \
        .OfCategory(DB.BuiltInCategory.OST_GenericModel) \
        .WhereElementIsNotElementType() \
        .ToElements()
    if get_loaded:
        for el in get_loaded:
            el_f_name = el.get_Parameter(DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM).AsString()
            if el_f_name.strip(" ") == name:
                return el


# 0001
def create_sheet(sheet_num, sheet_name, titleblock):
    sheet_num = str(sheet_num)

    # #cur_sheet_num = sheet.SheetNumber
    # sheetnum_p = sheet.Parameter[DB.BuiltInParameter.SHEET_NUMBER]
    # sheetnum_p.Set(
    #     coreutils.increment_str(sheet.SheetNumber, shift=1)
    # )
    # new_sheet_num = sheet.SheetNumber
    new_datasheet = DB.ViewSheet.Create(revit.doc, titleblock)
    new_datasheet.Name = sheet_name

    while get_sheet(sheet_num):
        sheet_num = coreutils.increment_str(sheet_num, 1)
    new_datasheet.SheetNumber = str(sheet_num)

    return new_datasheet


def find_crop_box(view):
    with DB.TransactionGroup(revit.doc, "Temp to find crop") as tg:
        tg.Start()
        with DB.Transaction(revit.doc, "temp") as t2:
            t2.Start()
            view.CropBoxVisible = False
            t2.Commit()
            hidden = DB.FilteredElementCollector(revit.doc, view.Id).ToElementIds()
            t2.Start()
            view.CropBoxVisible = True
            t2.Commit()
            crop_box_el = DB.FilteredElementCollector(revit.doc, view.Id).Excluding(hidden).FirstElement()
            tg.RollBack()
            if crop_box_el:
                return crop_box_el
            else:
                print("CROP NOT FOUND")
                return None


def degree_conv(x):
    return (x * 180) / math.pi


def point_equal_list(pt, lst):
    for el in list(lst):
        if pt.IsAlmostEqualTo(el, 0.003):
            return el
    else:
        return None


def set_anno_crop(v):
    anno_crop = v.get_Parameter(DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE)
    anno_crop.Set(1)


def get_open_ends(curves_list):
    endpoints = []
    for curve in curves_list:
        for i in range(2):
            duplicate = point_equal_list(curve.GetEndPoint(i), endpoints)
            if duplicate:
                endpoints.remove(duplicate)
            else:
                endpoints.append(curve.GetEndPoint(i))
    if endpoints:
        return endpoints
    else:
        return None


def get_room_bound(r):
    room_boundaries = DB.CurveLoop()
    # get room boundary segments
    room_segments = r.GetBoundarySegments(DB.SpatialElementBoundaryOptions())
    # iterate through loops of segments and add them to the array
    outer_loop = room_segments[0]
    # for curve in outer_loop:
    curve_loop = [s.GetCurve() for s in outer_loop]
    open_ends = get_open_ends(curve_loop)
    if open_ends:
        return None
    for curve in curve_loop:
        # try:
        room_boundaries.Append(curve)
        # except Exceptions.ArgumentException:
        #     print (curve)
    return room_boundaries


def get_longest_boundary(r):
    # get the rooms's longest boundary that is not an arc
    bound = r.GetBoundarySegments(DB.SpatialElementBoundaryOptions())
    longest = None
    for loop in bound:
        for b in loop:
            curve = b.GetCurve()
            if curve.Length > longest and isinstance(curve, DB.Line):
                longest = curve
    return longest


def set_crop_to_bb(element, view, crop_offset):
    # set the crop box of the view to elements's bounding box in that view
    # draw 2 sets of outlines for each orientation (front/back, left/right)
    bb = element.get_BoundingBox(view)

    pt1 = DB.XYZ(bb.Max.X, bb.Max.Y, bb.Min.Z)
    pt2 = DB.XYZ(bb.Max.X, bb.Max.Y, bb.Max.Z)
    pt3 = DB.XYZ(bb.Min.X, bb.Min.Y, bb.Max.Z)
    pt4 = DB.XYZ(bb.Min.X, bb.Min.Y, bb.Min.Z)

    pt7 = DB.XYZ(bb.Min.X, bb.Max.Y, bb.Min.Z)
    pt8 = DB.XYZ(bb.Min.X, bb.Max.Y, bb.Max.Z)
    pt5 = DB.XYZ(bb.Max.X, bb.Min.Y, bb.Max.Z)
    pt6 = DB.XYZ(bb.Max.X, bb.Min.Y, bb.Min.Z)

    l1 = DB.Line.CreateBound(pt1, pt2)
    l2 = DB.Line.CreateBound(pt2, pt3)
    l3 = DB.Line.CreateBound(pt3, pt4)
    l4 = DB.Line.CreateBound(pt4, pt1)

    l5 = DB.Line.CreateBound(pt6, pt5)
    l6 = DB.Line.CreateBound(pt5, pt8)
    l7 = DB.Line.CreateBound(pt8, pt7)
    l8 = DB.Line.CreateBound(pt7, pt6)

    curves_set1 = [l1, l2, l3, l4]
    curves_set2 = [l5, l6, l7, l8]

    crsm = view.GetCropRegionShapeManager()
    view_direction = view.ViewDirection

    try:
        # try with set 1, if doesn't work try with set 2
        crop_loop = DB.CurveLoop.Create(List[DB.Curve](curves_set1))
        # offset the crop with the specified offset
        curve_loop_offset = DB.CurveLoop.CreateViaOffset(crop_loop, crop_offset, view_direction)
        # in case the offset works inwards, correct it to offset outwards
        if curve_loop_offset.GetExactLength() < crop_loop.GetExactLength():
            curve_loop_offset = DB.CurveLoop.CreateViaOffset(crop_loop, crop_offset, -view_direction)
        crsm.SetCropShape(curve_loop_offset)
    except:
        crop_loop = DB.CurveLoop.Create(List[DB.Curve](curves_set2))
        curve_loop_offset = DB.CurveLoop.CreateViaOffset(crop_loop, crop_offset, view_direction)
        if curve_loop_offset.GetExactLength() < crop_loop.GetExactLength():
            curve_loop_offset = DB.CurveLoop.CreateViaOffset(crop_loop, crop_offset, -view_direction)
        crsm.SetCropShape(curve_loop_offset)
    return


def room_rotation_angle(room):
    # get the angle of the room's longest boundary to Y axis
    # choose one longest curve to use as reference for rotation
    longest_boundary = get_longest_boundary(room)
    p = longest_boundary.GetEndPoint(0)
    q = longest_boundary.GetEndPoint(1)
    v = q - p
    # get angle and correct value
    bbox_angle = v.AngleTo(DB.XYZ.BasisY)
    # correct angles
    if degree_conv(bbox_angle) > 90:
        bbox_angle = bbox_angle - math.radians(90)
    elif degree_conv(bbox_angle) < 45:
        bbox_angle = -bbox_angle
    else:
        bbox_angle = bbox_angle
    return bbox_angle


def get_bb_axis_in_view(element, view):
    # return the central axis of element's bounding box in view
    # get viewplan bbox, center
    bbox = element.get_BoundingBox(view)
    center = 0.5 * (bbox.Max + bbox.Min)
    axis = DB.Line.CreateBound(center, center + DB.XYZ.BasisZ)
    return axis


def apply_vt(v, vt):
    if vt:
        v.ViewTemplateId = vt.Id
    return


def is_metric(doc):
    display_units = DB.Document.GetUnits(doc).GetFormatOptions(DB.UnitType.UT_Length).DisplayUnits
    metric_units = [
        DB.DisplayUnitType.DUT_METERS,
        DB.DisplayUnitType.DUT_CENTIMETERS,
        DB.DisplayUnitType.DUT_DECIMETERS,
        DB.DisplayUnitType.DUT_MILLIMETERS,
        DB.DisplayUnitType.DUT_METERS_CENTIMETERS
    ]
    if display_units in set(metric_units):
        return True
    else:
        return False


def correct_input_units(val):
    import re
    try:
        digits = float(val)
    except ValueError:
        # format the string using regex
        digits = re.findall("[0-9.]+", val)[0]
    if is_metric(revit.doc):
        return DB.UnitUtils.ConvertToInternalUnits(float(digits), DB.DisplayUnitType.DUT_MILLIMETERS)
    else:
        return DB.UnitUtils.ConvertToInternalUnits(float(digits), DB.DisplayUnitType.DUT_DECIMAL_INCHES)


def get_aligned_crop(geo, transform):

    rotated_geo = geo.GetTransformed(transform)
    revit.doc.Regenerate()
    rb = rotated_geo.GetBoundingBox()
    bb_outline = get_bb_outline(rb)
    # rotate the curves back using the opposite direction
    tr_back = transform.Inverse
    rotate_curves_back = [c.CreateTransformed(tr_back) for c in bb_outline]
    crop_loop = DB.CurveLoop.Create(List[DB.Curve](rotate_curves_back))

    return crop_loop


def get_bb_outline(bb):

    r1 = DB.XYZ(bb.Min.X, bb.Min.Y, bb.Min.Z)
    r2 = DB.XYZ(bb.Max.X, bb.Min.Y, bb.Min.Z)
    r3 = DB.XYZ(bb.Max.X, bb.Max.Y, bb.Min.Z)
    r4 = DB.XYZ(bb.Min.X, bb.Max.Y, bb.Min.Z)

    l1 = DB.Line.CreateBound(r1, r2)
    l2 = DB.Line.CreateBound(r2, r3)
    l3 = DB.Line.CreateBound(r3, r4)
    l4 = DB.Line.CreateBound(r4, r1)

    curves_set = [l1, l2, l3, l4]
    return curves_set