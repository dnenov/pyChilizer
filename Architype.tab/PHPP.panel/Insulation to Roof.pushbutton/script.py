__title__ = "Insulation\nto Roof"
__doc__ = "Creates a new Roof representing the insulation layer"

from pyrevit import revit, DB, script, forms
from pyrevit.framework import List
from rpw.ui.forms import (FlexForm, Label, ComboBox, Separator, Button)
import math

doc = revit.doc

# get document length units for conversion
d_units = DB.Document.GetUnits(doc).GetFormatOptions(DB.UnitType.UT_Length).DisplayUnits


def roof_type_has_ins(r_type):
    # return true if roof has insulation layer(s)
    # get compound structure
    compound_str = r_type.GetCompoundStructure()
    roof_has_insulation = False
    # iterate through layers
    num = compound_str.LayerCount
    for n in range(num - 1):
        # if encounter ins layer - roof has ins layer
        if str(compound_str.GetLayerFunction(n)) == "Insulation":
            roof_has_insulation = True
        else:
            pass
    return roof_has_insulation


def get_ins_layer_width(r_type):
    # get widths of insulation layers
    # check if roof has ins
    if roof_type_has_ins(r_type):
        # get compound structure
        comp_str = r_type.GetCompoundStructure()
        # iterate through layers and not down widths of insulation layers
        num = comp_str.LayerCount
        for n in range(num - 1):
            if str(comp_str.GetLayerFunction(n)) == "Insulation":
                ins_width = comp_str.GetLayerWidth(n)
                return ins_width
    else:
        return


def get_ins_position(r_type):
    # position of ins layer
    ins_layer_position = 0
    # check if roof has ins
    if roof_type_has_ins(r_type):
        # get compound structure
        comp_str = r_type.GetCompoundStructure()
        # iterate through layers and add up the widths of insulation layers
        num = comp_str.LayerCount
        for n in range(num - 1):
            if str(comp_str.GetLayerFunction(n)) != "Insulation":
                ins_layer_position += comp_str.GetLayerWidth(n)
            else:
                return ins_layer_position
        return ins_layer_position
    else:
        return


def convert_units(from_units, to_units=d_units):
    # convert internal to project units

    converted = DB.UnitUtils.ConvertFromInternalUnits(from_units, to_units)
    return converted


def get_hosted(host_id):
    # get ids of elements hosted on element
    elems = DB.FilteredElementCollector(doc).OfClass(DB.FamilyInstance).ToElements()
    hosted_element_ids = [e.Id for e in elems if
                          e.get_Parameter(DB.BuiltInParameter.HOST_ID_PARAM).AsValueString() == str(host_id)]

    return hosted_element_ids


def get_sketch_elements(roof):
    # delete the element and roll back, while catching the IDs of deleted elements
    t1 = DB.Transaction(doc, "temp delete elements")
    t1.Start()
    all_ids = doc.Delete(roof.Id)
    t1.RollBack()

    profile = None
    curves = []
    # pick only sketch elements
    for id in all_ids:
        el = doc.GetElement(id)
        if isinstance(el, DB.Sketch):
            profile = el.Profile
    # formatting: iterate through sketch curve arrays and gather curves
    if not profile:
        return
    else:
        for curve_arr in profile:
            for curve in curve_arr:
                curves.append(curve)
        return List[DB.Curve](curves)


# format roof types dict for ui window
coll_rt = DB.FilteredElementCollector(doc).OfClass(DB.RoofType)
roof_type_dict = {rt.get_Parameter(DB.BuiltInParameter.ALL_MODEL_TYPE_NAME).AsString(): rt for rt in coll_rt}

# format document phases dict for ui window
doc_phases_dict = {ph.Name: ph for ph in doc.Phases}

# rwp UI: pick roof type and phase
components = [Label("Select Roof Type:"),
              ComboBox("combobox1", roof_type_dict),
              Label("Select Phase:"),
              ComboBox("combobox2", doc_phases_dict),
              Separator(),
              Button("Select")]
form = FlexForm("Settings", components)
form.show()
chosen_roof_type = form.values["combobox1"]
chosen_phase = form.values["combobox2"]

# collect roofs in project that are not in Insulation Phase
coll_all_roofs = DB.FilteredElementCollector(doc) \
    .OfClass(DB.RoofBase) \
    .WhereElementIsNotElementType() \
    .ToElements()

ins_roofs = [w for w in coll_all_roofs if roof_type_has_ins(w.RoofType)
             and w.get_Parameter(DB.BuiltInParameter.PHASE_CREATED) != chosen_phase]

# iterate through collected ins roofs:
for roof in ins_roofs:
    roof_type = roof.RoofType

    # width of insulation layer
    ins_layer_width = get_ins_layer_width(roof.RoofType)

    # calculate the position of the ins layer for later
    roof_thickness = roof.get_Parameter(DB.BuiltInParameter.ROOF_ATTR_THICKNESS_PARAM).AsDouble()
    ins_position = roof_thickness - get_ins_position(roof_type) - ins_layer_width / 2

    with revit.Transaction("Create new roof", doc):

        # For FOOTPRINT ROOF: copy paste roof and change offset from level
        if isinstance(roof, DB.FootPrintRoof):

            new_roof_id = DB.ElementTransformUtils.CopyElement(doc, roof.Id, DB.XYZ(0, 0, 0))
            doc.Regenerate()

            deleted = []
            hosted = get_hosted(roof)
            for h in hosted:
                revit.doc.Delete(h.Id)
                deleted.append(h.Id)
                print (h.Id)

            new_roof = doc.GetElement(new_roof_id[0])
            change_type = new_roof.ChangeTypeId(chosen_roof_type.Id)

            roof_orig_offset = new_roof.get_Parameter(DB.BuiltInParameter.ROOF_LEVEL_OFFSET_PARAM).AsDouble()

            # calculate level offset
            slope = new_roof.get_Parameter(DB.BuiltInParameter.ROOF_SLOPE).AsDouble()
            level_offset = roof_orig_offset + (ins_position / math.cos(math.atan(slope)))

            # set level offset
            change_offset = new_roof.get_Parameter(DB.BuiltInParameter.ROOF_LEVEL_OFFSET_PARAM).Set(level_offset)

        # for EXTRUSION ROOF: create new roof using offset profile
        elif isinstance(roof, DB.ExtrusionRoof):
            try:
                profile = roof.GetProfile()

                # get profile plane
                e1 = profile[0].GeometryCurve.GetEndPoint(0)
                e2 = profile[0].GeometryCurve.GetEndPoint(1)
                h = DB.XYZ(e1.X, e1.Y, 100)
                plane = DB.Plane.CreateByThreePoints(e1, e2, h)

                # use a curve loop to offset the profile polycurve
                curve_loop = DB.CurveLoop()
                for model_curve in profile:
                    curve_loop.Append(model_curve.GeometryCurve)

                offset_distance = get_ins_position(roof_type) + ins_layer_width / 2
                offset_loop = DB.CurveLoop.CreateViaOffset(curve_loop, offset_distance, plane.Normal)

                # store new curves in a curve array
                new_curves = DB.CurveArray()
                for curve in offset_loop:
                    new_curves.Append(curve)

                # create profile reference plane
                ref_plane = doc.Create.NewReferencePlane2(e1, e2, h, revit.active_view)

                # get original roof parameters
                extr_start = roof.get_Parameter(DB.BuiltInParameter.EXTRUSION_START_PARAM).AsDouble()
                extr_end = roof.get_Parameter(DB.BuiltInParameter.EXTRUSION_END_PARAM).AsDouble()
                level = doc.GetElement(roof.get_Parameter(DB.BuiltInParameter.ROOF_CONSTRAINT_LEVEL_PARAM).AsElementId())

                # create new extrusion roof
                new_roof = doc.Create.NewExtrusionRoof(new_curves, ref_plane, level, chosen_roof_type, extr_start, extr_end)
            except:
                pass
        # change new roof phase to chosen phase
        new_roof.CreatedPhaseId = chosen_phase.Id
        new_roof.DemolishedPhaseId = chosen_phase.Id