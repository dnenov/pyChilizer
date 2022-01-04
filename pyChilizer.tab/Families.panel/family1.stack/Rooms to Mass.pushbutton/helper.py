"""Transform rooms to families"""

from pyrevit import revit, DB, script, forms, HOST_APP
from rpw.ui.forms import (FlexForm, Label, ComboBox, Separator, Button)
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
from Autodesk.Revit import Exceptions
import tempfile
import rpw
from pyrevit.revit.db import query


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


def convert_length_to_internal(d_units):
    # convert length units from display units to internal
    units = revit.doc.GetUnits()
    if HOST_APP.is_newer_than(2021):
        internal_units = units.GetFormatOptions(DB.SpecTypeId.Length).GetUnitTypeId()
    else:  # pre-2021
        internal_units = units.GetFormatOptions(DB.UnitType.UT_Length).DisplayUnits
    converted = DB.UnitUtils.ConvertToInternalUnits(d_units, internal_units)
    return converted


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


def get_fam(family_name):
    # get family symbol by family name, get any type
    fam_bip_id = DB.ElementId(DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM)
    fam_bip_provider = DB.ParameterValueProvider(fam_bip_id)
    fam_filter_rule = DB.FilterStringRule(fam_bip_provider, DB.FilterStringEquals(), family_name, True)
    fam_filter = DB.ElementParameterFilter(fam_filter_rule)

    collector = DB.FilteredElementCollector(revit.doc) \
        .WherePasses(fam_filter) \
        .WhereElementIsElementType() \
        .FirstElement()

    return collector
