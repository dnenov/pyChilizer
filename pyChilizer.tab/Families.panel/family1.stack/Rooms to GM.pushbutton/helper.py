"""Transform rooms to generic model families"""

from pyrevit import revit, DB, script, forms, HOST_APP
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
from Autodesk.Revit import Exceptions
import rpw
from pyrevit.revit.db import query
import re


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
        forms.alert("Cancelled", ok=True, warn_icon=False)


def preselection_with_filter(bic):
    # use pre-selection of elements, but filter them by given category name
    pre_selection = []
    for id in rpw.revit.uidoc.Selection.GetElementIds():
        sel_el = revit.doc.GetElement(id)
        if sel_el.Category.Id.IntegerValue == int(bic):
            pre_selection.append(sel_el)
    return pre_selection


def inverted_transform(element):
    # get element location and return its inverted transform
    # can be used to translate geometry to 0,0,0 origin to recreate geometry inside a family
    el_location = element.Location.Point
    bb = element.get_BoundingBox(revit.doc.ActiveView)
    orig_cs = bb.Transform
    # Creates a transform that represents a translation via the specified vector.
    translated_cs = orig_cs.CreateTranslation(el_location)
    # Transform from the room location point to origin
    return translated_cs.Inverse


def point_equal_list(pt, lst):
    for el in list(lst):
        if pt.IsAlmostEqualTo(el, 0.003):
            return el
    else:
        return None


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


def room_bound_to_origin(room, translation):
    # iterate through room boundaries and translate them close to the origin
    # also query open ends and return none if the loop is open
    room_boundaries = DB.CurveArrArray()
    # get room boundary segments
    room_segments = room.GetBoundarySegments(DB.SpatialElementBoundaryOptions())
    # iterate through loops of segments and add them to the array
    for seg_loop in room_segments:
        curve_loop = [s.GetCurve() for s in seg_loop]
        open_ends = get_open_ends(curve_loop)

        if open_ends:
            print(open_ends)
            return None
        curve_array = DB.CurveArray()
        for old_curve in curve_loop:
            # old_curve = s.GetCurve()
            new_curve = old_curve.CreateTransformed(translation)  # move curves to origin
            curve_array.Append(new_curve)
        room_boundaries.Append(curve_array)
    return room_boundaries


def get_ref_lvl_plane(family_doc):
    # from given family doc, return Ref. Level reference plane
    find_planes = DB.FilteredElementCollector(family_doc).OfClass(DB.SketchPlane)
    return [plane for plane in find_planes if plane.Name == "Ref. Level"]


def convert_length_to_internal(d_units):
    # convert length units from display units to internal
    units = revit.doc.GetUnits()
    if HOST_APP.is_newer_than(2021):
        internal_units = units.GetFormatOptions(DB.SpecTypeId.Length).GetUnitTypeId()
    else: # pre-2021
        internal_units = units.GetFormatOptions(DB.UnitType.UT_Length).DisplayUnits
    converted = DB.UnitUtils.ConvertToInternalUnits(d_units, internal_units)
    return converted


def get_fam_type(family_name, type_name):
    # not used here
    fam_bip_id = DB.ElementId(DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM)
    fam_bip_provider = DB.ParameterValueProvider(fam_bip_id)
    fam_filter_rule = DB.FilterStringRule(fam_bip_provider, DB.FilterStringEquals(), family_name, True)
    fam_filter = DB.ElementParameterFilter(fam_filter_rule)

    type_bip_id = DB.ElementId(DB.BuiltInParameter.ALL_MODEL_TYPE_NAME)
    type_bip_provider = DB.ParameterValueProvider(type_bip_id)
    type_filter_rule = DB.FilterStringRule(type_bip_provider, DB.FilterStringEquals(), type_name, True)
    type_filter = DB.ElementParameterFilter(type_filter_rule)

    and_filter = DB.LogicalAndFilter(fam_filter, type_filter)

    collector = DB.FilteredElementCollector(revit.doc) \
        .WherePasses(and_filter) \
        .FirstElement()

    return collector


def get_fam(family_name):
    fam_bip_id = DB.ElementId(DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM)
    fam_bip_provider = DB.ParameterValueProvider(fam_bip_id)
    fam_filter_rule = DB.FilterStringRule(fam_bip_provider, DB.FilterStringEquals(), family_name, True)
    fam_filter = DB.ElementParameterFilter(fam_filter_rule)

    collector = DB.FilteredElementCollector(revit.doc) \
        .WherePasses(fam_filter) \
        .WhereElementIsElementType() \
        .FirstElement()

    return collector


def room_to_freeform(r, family_doc):
    room_geo = r.ClosedShell
    for geo in room_geo:
        if isinstance(geo, DB.Solid) and geo.Volume > 0.0:
            freeform = DB.FreeFormElement.Create(family_doc, geo)
            family_doc.Regenerate()
            delta = DB.XYZ(0, 0, 0) - freeform.get_BoundingBox(None).Min
            move_ff = DB.ElementTransformUtils.MoveElement(
                family_doc, freeform.Id, delta
            )
            # create and associate a material parameter
            ext_mat_param = freeform.get_Parameter(DB.BuiltInParameter.MATERIAL_ID_PARAM)
            new_mat_param = family_doc.FamilyManager.AddParameter("Material",
                                                                  DB.BuiltInParameterGroup.PG_MATERIALS,
                                                                  DB.ParameterType.Material,
                                                                  True)
            family_doc.FamilyManager.AssociateElementParameterToFamilyParameter(ext_mat_param,
                                                                                new_mat_param)
    return freeform


def room_to_extrusion(r, family_doc):
    room_height = r.get_Parameter(DB.BuiltInParameter.ROOM_HEIGHT).AsDouble()
    # helper: define inverted transform to translate room geometry to origin
    geo_translation = inverted_transform(r)
    # collect room boundaries and translate them to origin
    room_boundaries = room_bound_to_origin(r, geo_translation)
    # skip if the boundaries are not a closed loop (can happen with misaligned boundaries)
    if not room_boundaries:
        print("Extrusion failed for room {}. Try fixing room boundaries".format(output.linkify(r.Id)))
        return

    ref_plane = get_ref_lvl_plane(family_doc)
    # create extrusion, assign material, associate with shared parameter
    try:
        extrusion = family_doc.FamilyCreate.NewExtrusion(True, room_boundaries, ref_plane[0],
                                                         room_height)
        ext_mat_param = extrusion.get_Parameter(DB.BuiltInParameter.MATERIAL_ID_PARAM)
        # create and associate a material parameter
        new_mat_param = family_doc.FamilyManager.AddParameter("Material",
                                                              DB.BuiltInParameterGroup.PG_MATERIALS,
                                                              DB.ParameterType.Material,
                                                              False)
        family_doc.FamilyManager.AssociateElementParameterToFamilyParameter(ext_mat_param,
                                                                            new_mat_param)
        return extrusion
    except Exceptions.InternalException:
        print("Extrusion failed for room {}. Try fixing room boundaries".format(output.linkify(r.Id)))
        return
