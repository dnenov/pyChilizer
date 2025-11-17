import sys

from pyrevit import DB, UI, revit, HOST_APP
from pyrevit import script, forms, coreutils
from pyrevit.framework import List

import os
import xlrd
import math

doc = revit.doc
FEC = DB.FilteredElementCollector
BIC = DB.BuiltInCategory
output = script.get_output()
output.close_others()
results_table = []
output.print_md("# QAQC Model Check")
worksets = DB.FilteredWorksetCollector(doc).OfKind(DB.WorksetKind.UserWorkset).ToWorksets()



nrm_parameters = ["ALD_Classification.NRM.1.Description",
              "ALD_Classification.NRM.1.Number"
              ]

uniclass_parameters = [
              "ALD_Classification.Uniclass.EF.Description",
              "ALD_Classification.Uniclass.EF.Number",
              "ALD_Classification.Uniclass.Ss.Description",
              "ALD_Classification.Uniclass.Ss.Number",
              "ALD_Classification.Uniclass.Pr.Description",
              "ALD_Classification.Uniclass.Pr.Number"
              ]

category_dict = {
    "Casework": BIC.OST_Casework,
    "Air Terminals": BIC.OST_DuctTerminal,
    "Audio Visual Devices": BIC.OST_AudioVisualDevices,
    "Cable Tray Fittings": BIC.OST_CableTrayFitting,
    "Cable Trays": BIC.OST_CableTray,
    "Ceilings": BIC.OST_Ceilings,
    "Columns": BIC.OST_Columns,
    "Communication Devices": BIC.OST_CommunicationDevices,
    "Conduit Fittings": BIC.OST_ConduitFitting,
    "Conduits": BIC.OST_Conduit,
    "Curtain Panels": BIC.OST_CurtainWallPanels,
    "Curtain Wall Mullions": BIC.OST_CurtainWallMullions,
    "Data Devices": BIC.OST_DataDevices,
    "Doors": BIC.OST_Doors,
    "Duct Accessories": BIC.OST_DuctAccessory,
    "Duct Fittings": BIC.OST_DuctFitting,
    "Duct Insulations": BIC.OST_DuctInsulations,
    "Duct Linings": BIC.OST_DuctLinings,
    "Ducts": BIC.OST_DuctCurves,
    "Electrical Equipment": BIC.OST_ElectricalEquipment,
    "Electrical Fixtures": BIC.OST_ElectricalFixtures,
    "Entourage": BIC.OST_Entourage,
    "Expansion Joints": BIC.OST_ExpansionJoints,
    "Fire Alarm Devices": BIC.OST_FireAlarmDevices,
    "Flex Ducts": BIC.OST_FlexDuctCurves,
    "Flex Pipes": BIC.OST_FlexPipeCurves,
    "Floors": BIC.OST_Floors,
    "Food Service Equipment": BIC.OST_FoodServiceEquipment,
    "Furniture": BIC.OST_Furniture,
    "Hardscape": BIC.OST_Hardscape,
    "Lighting Devices": BIC.OST_LightingDevices,
    "Lighting Fixtures": BIC.OST_LightingFixtures,
    "Mechanical Control Devices": BIC.OST_MechanicalControlDevices,
    "Mechanical Equipment": BIC.OST_MechanicalEquipment,
    "Medical Equipment": BIC.OST_MedicalEquipment,
    "Nurse Call Devices": BIC.OST_NurseCallDevices,
    "Parking": BIC.OST_Parking,
    "Pipe Accessories": BIC.OST_PipeAccessory,
    "Pipe Fittings": BIC.OST_PipeFitting,
    "Pipe Insulations": BIC.OST_PipeInsulations,
    "Pipes": BIC.OST_PipeCurves,
    "Planting": BIC.OST_Planting,
    "Plumbing Equipment": BIC.OST_PlumbingEquipment,
    "Plumbing Fixtures": BIC.OST_PlumbingFixtures,
    "Railings": BIC.OST_StairsRailing,
    "Ramps": BIC.OST_Ramps,
    "Roads": BIC.OST_Roads,
    "Roofs": BIC.OST_Roofs,
    "Security Devices": BIC.OST_SecurityDevices,
    "Signage": BIC.OST_Signage,
    "Site": BIC.OST_Site,
    "Speciality Equipment": BIC.OST_SpecialityEquipment,
    "Sprinklers": BIC.OST_Sprinklers,
    "Stairs": BIC.OST_Stairs,
    "Structural Area Reinforcement": BIC.OST_AreaRein,
    "Structural Beam Systems": BIC.OST_StructuralFramingSystem,
    "Structural Columns": BIC.OST_StructuralColumns,
    "Structural Connections": BIC.OST_StructConnections,
    "Structural Fabric Reinforcement": BIC.OST_FabricReinforcement,
    "Structural Foundations": BIC.OST_StructuralFoundation,
    "Structural Framing": BIC.OST_StructuralFraming,
    "Structural Path Reinforcement": BIC.OST_PathRein,
    "Structural Rebar": BIC.OST_Rebar,
    "Structural Rebar Couplers": BIC.OST_Coupler,
    "Structural Stiffeners": BIC.OST_StructuralStiffener,
    "Structural Trusses": BIC.OST_StructuralTruss,
    "Telephone Devices": BIC.OST_TelephoneDevices,
    "Temporary Structures": BIC.OST_TemporaryStructure,
    "Topography": BIC.OST_Topography,
    "Walls": BIC.OST_Walls,
    "Windows": BIC.OST_Windows
}

# --- Load the Excel workbook ---
def pick_excel():
    # Set default directory
    default_dir = os.path.dirname(__file__)

    # Open the file dialog with the default path
    excel_file_path = forms.pick_file(file_ext="xlsx", init_dir=default_dir)

    # Check if a file was selected
    if not excel_file_path:
        raise FileNotFoundError("No Excel file selected.")

    return excel_file_path


def get_category_by_name(name):
    # Loop through all BuiltInCategory enum names
    for bic in DB.BuiltInCategory.GetValues(DB.BuiltInCategory):
        try:
            category = DB.Category.GetCategory(doc, bic)
            if category and category.Name == name:
                return bic
        except:
            continue  # Some BuiltInCategories don't resolve (e.g., invalid in context)
    return None


def check_units(doc):
    units = doc.GetUnits()
    # Get the FormatOptions for Length
    format_options = units.GetFormatOptions(DB.SpecTypeId.Length)
    # Check if the unit type is millimeters
    check_pass = format_options.GetUnitTypeId() == DB.UnitTypeId.Millimeters
    if format_options.GetUnitTypeId() == DB.UnitTypeId.Millimeters:
        ch_result = "Pass"
    else:
        ch_result="Fail"
    ch_notes = "N/A"
    if not ch_result:
        ch_notes = format_options
    results_table.append({"Check Number": "CH02-04",
                          "Description": "Check units millimeters",
                          "Result": str(ch_result),
                          "Notes": str(ch_notes)})
    return


def check_base_and_survey_points(doc):
    collector = FEC(doc)

    # Get Base Points (both Project Base Point and Survey Point)
    base_points = collector.OfClass(DB.BasePoint).ToElements()
    ch_notes = []
    for bp in base_points:
        if bp.IsShared:  # Survey Point
            point_type = "Survey Point"
        else:  # Project Base Point
            point_type = "Project Base Point"

        positionX = bp.get_Parameter(DB.BuiltInParameter.BASEPOINT_EASTWEST_PARAM).AsValueString()
        positionY = bp.get_Parameter(DB.BuiltInParameter.BASEPOINT_NORTHSOUTH_PARAM).AsValueString()
        positionZ = bp.get_Parameter(DB.BuiltInParameter.BASEPOINT_ELEVATION_PARAM).AsValueString()
        point_position = "".join([point_type, " Position: X=", positionX, " Y=", positionY, " Z=", positionZ])
        ch_notes.append(point_position)

    results_table.append({"Check Number": "CH03-02",
                          "Description": "Location",
                          "Result": "-",
                          "Notes": str(", ".join(ch_notes))})
    return


def check_revit_links_pinned(doc):
    collector = FEC(doc).OfClass(DB.RevitLinkInstance)

    ch_result = True
    ch_notes = "N/A"
    count = 0
    for link in collector:
        is_pinned = link.Pinned
        if not is_pinned:
            count += 1
    if count > 0:
        ch_result = "Fail"
        ch_notes = "".join([str(count)," Links not pinned"])

    results_table.append({"Check Number": "CH04-02",
                          "Description": "Check Links are pinned",
                          "Result": str(ch_result),
                          "Notes": str(ch_notes)})

    return


def check_no_imported_cads(doc):
    # Collect all instances of ImportInstance (includes imported CAD files)
    imported_cads = [i.Id for i in FEC(doc).OfClass(DB.ImportInstance) if not i.IsLinked]

    if len(imported_cads) == 0:
        ch_result = "Pass"
        ch_notes = "N/A"
    else:
        ch_result = "Fail"
        ch_notes = len(imported_cads)

    results_table.append({"Check Number": "CH04-03",
                          "Description": "Check no CAD imports",
                          "Result": str(ch_result),
                          "Notes": str(ch_notes)})
    return


def check_grids_and_levels_pinned(doc):
    pinned_grids = True
    pinned_levels = True
    ch_result = "Fail"
    ch_notes = "N/A"
    # Collect all grids
    grids = FEC(doc).OfClass(DB.Grid).ToElements()
    for grid in grids:
        if not grid.Pinned:
            pinned_grids = False

    # Collect all levels
    levels = FEC(doc).OfClass(DB.Level).WhereElementIsNotElementType().ToElements()
    for level in levels:
        if not level.Pinned:
            pinned_levels = False

    # Report
    if pinned_levels and pinned_grids:
        ch_result = "Pass"
    else:
        ch_notes = ""
        if not pinned_levels:
            ch_notes = ch_notes + " Levels not pinned"
        if not pinned_grids:
            ch_notes = ch_notes +" Grids not pinned"

    results_table.append({"Check Number": "CH05-02",
                          "Description": "Check Levels&Grids pinned",
                          "Result": str(ch_result),
                          "Notes": str(ch_notes)})
    return


def check_worksets_with_levels_and_grids(doc):
    workset_ids_with_levels_grids = set()

    # Collect Levels
    levels = FEC(doc).OfClass(DB.Level).ToElements()
    for lvl in levels:
        workset_ids_with_levels_grids.add(lvl.WorksetId.IntegerValue)

    # Collect Grids
    grids = FEC(doc).OfClass(DB.Grid).ToElements()
    for grd in grids:
        workset_ids_with_levels_grids.add(grd.WorksetId.IntegerValue)

    # Collect all user worksets
    worksets = DB.FilteredWorksetCollector(doc).OfKind(DB.WorksetKind.UserWorkset)

    workset_map = {ws.Id.IntegerValue: ws.Name for ws in worksets}
    worksets_count = 0
    workset_names = []
    for ws_id in sorted(workset_ids_with_levels_grids):
        workset_names.append(workset_map.get(ws_id, "<Unknown Workset>"))
        worksets_count += 1
    ch_notes = ",".join(workset_names)
    if worksets_count == 1:
        ch_result = "Pass"
    else:
        ch_result = "Fail"
    results_table.append({"Check Number": "CH05-03",
                          "Description": "Check Levels&Grids are on the correct workset",
                          "Result": str(ch_result),
                          "Notes": str(ch_notes)})
    return


def check_startup_view_name(doc):
    # Get the StartingViewSettings object
    starting_view_settings = DB.StartingViewSettings.GetStartingViewSettings(doc)

    # Get the view ID set as the startup view
    view_id = starting_view_settings.ViewId

    if view_id and view_id != DB.ElementId.InvalidElementId:
        startup_view = doc.GetElement(view_id)
        # print("Startup View: {}".format(startup_view.Name))
        ch_notes = startup_view.Name
    else:
        ch_notes = "No startup view"
    results_table.append({"Check Number": "CH07-01",
                          "Description": "Check startup view",
                          "Result": "-",
                          "Notes": str(ch_notes)})
    return


def check_unplaced_views(doc):
    viewports = List[DB.ElementId] \
        ([i.ViewId for i in FEC(doc).OfCategory(DB.BuiltInCategory.OST_Viewports).WhereElementIsNotElementType()])

    views = List[DB.ElementId] \
        ([i.Id for i in
          FEC(doc).OfCategory(DB.BuiltInCategory.OST_Views).WhereElementIsNotElementType()])

    # unplaced_views = List[DB.ElementId]([v for v in views if v not in viewports])
    unplaced_views = [doc.GetElement(v) for v in views if v not in viewports]
    if unplaced_views:
        ch_result = "Fail"
        ch_notes = str(len(unplaced_views)) + " unplaced views"
    else:
        ch_result = "Pass"
        ch_notes = "No unplaced views"
    results_table.append({"Check Number": "CH07-03",
                          "Description": "Check unplaced views",
                          "Result": str(ch_result),
                          "Notes": str(ch_notes)})
    return


def check_unplaced_rooms(doc):
    rooms = FEC(doc).OfCategory(DB.BuiltInCategory.OST_Rooms).WhereElementIsNotElementType().ToElements()
    not_placed = []
    for room in rooms:
        if room.Location is None:
            not_placed.append(room)
    if not_placed:
        ch_result = "Fail"
        ch_notes = str(len(not_placed)) + " Unplaced Rooms"
    else:
        ch_result = "Pass"
        ch_notes = "N/A"

    results_table.append({"Check Number": "CH010-01",
                          "Description": "Check unplaced rooms",
                          "Result": str(ch_result),
                          "Notes": str(ch_notes)})
    return


def check_unenclosed_rooms(doc):
    rooms = FEC(doc).OfCategory(DB.BuiltInCategory.OST_Rooms).WhereElementIsNotElementType().ToElements()
    unenclosed = []
    for room in rooms:
        if room.Area == 0:
            unenclosed.append(room)
    if unenclosed:
        ch_result = "Fail"
        ch_notes = str(len(unenclosed)) + " Unenclosed Rooms"
    else:
        ch_result = "Pass"
        ch_notes = "N/A"

    results_table.append({"Check Number": "CH010-03",
                          "Description": "Check unenclosed rooms",
                          "Result": str(ch_result),
                          "Notes": str(ch_notes)})
    return


def check_inplace(doc):
    # Collect all family instances
    family_instances = FEC(doc) \
        .OfClass(DB.FamilyInstance) \
        .WhereElementIsNotElementType() \
        .ToElements()

    in_place_families = []

    for instance in family_instances:
        family = instance.Symbol.Family
        if family.IsInPlace:
            in_place_families.append(instance)
    if in_place_families:
        from System.Collections.Generic import List
        element_ids = List[DB.ElementId]([instance.Id for instance in in_place_families])
        uidoc = revit.uidoc
        uidoc.Selection.SetElementIds(element_ids)
        ch_result = "Fail"
        ch_notes = str(len(in_place_families)) + " In-Place Elements"
    else:
        ch_result = "Pass"
        ch_notes = "N/A"

    results_table.append({"Check Number": "CH010-19",
                          "Description": "Check in-place elements",
                          "Result": str(ch_result),
                          "Notes": str(ch_notes)})
    return


def check_generic_model_instances(doc):
    # Collect all placed Generic Model family instances (not types)
    generic_models = FEC(doc) \
        .OfCategory(DB.BuiltInCategory.OST_GenericModel) \
        .WhereElementIsNotElementType() \
        .ToElements()

    if generic_models:
        ch_result = "Fail"
        ch_notes = str(len(generic_models)) + " Generic Model Elements"
    else:
        ch_result = "Pass"
        ch_notes = "N/A"

    results_table.append({"Check Number": "CH010-20",
                          "Description": "Check Generic Model elements",
                          "Result": str(ch_result),
                          "Notes": str(ch_notes)})
    return


def check_used_phases(doc):
    # Get all elements in the model (excluding element types)
    elements = FEC(doc) \
        .WhereElementIsNotElementType() \
        .ToElements()

    # Use sets to collect unique Phase Ids
    used_phase_ids = set()

    for el in elements:
        created_phase = el.get_Parameter(DB.BuiltInParameter.PHASE_CREATED)
        demolished_phase = el.get_Parameter(DB.BuiltInParameter.PHASE_DEMOLISHED)

        if created_phase and created_phase.HasValue and created_phase.AsElementId() != DB.ElementId.InvalidElementId:
            used_phase_ids.add(created_phase.AsElementId())

        if demolished_phase and demolished_phase.HasValue and demolished_phase.AsElementId() != DB.ElementId.InvalidElementId:
            used_phase_ids.add(demolished_phase.AsElementId())

    # Get actual phase elements from ids
    used_phases = [doc.GetElement(pid) for pid in used_phase_ids if doc.GetElement(pid)]

    # Report
    if used_phases:
        ch_notes = ", ".join([p.Name for p in used_phases])
    else:
        ch_notes = "N/A"

    results_table.append({"Check Number": "CH12-02",
                          "Description": "Check Phases used",
                          "Result": "-",
                          "Notes": str(ch_notes)})

    return


def check_warnings_count(doc):

    failure_messages = doc.GetWarnings()

    results_table.append({"Check Number": "CH13-01 ",
                          "Description": "Check warnings",
                          "Result": "-",
                          "Notes": str(len(failure_messages))})

    return


def check_duplicate_instance_warnings(doc):
    duplicate_warnings = []
    warnings = doc.GetWarnings()

    for warning in warnings:
        warning_text = warning.GetDescriptionText()
        if "identical instances in the same place" in warning_text:
            duplicate_warnings.append(warning)

    if duplicate_warnings:
        ch_result = "Fail"
        ch_notes = str(len(duplicate_warnings)) + " warnings"
    else:
        ch_result = "Pass"
        ch_notes = "N/A"

    results_table.append({"Check Number": "CH13-02",
                          "Description": "Duplicate instances warning",
                          "Result": str(ch_result),
                          "Notes": str(ch_notes)})
    return


def check_overlap_warnings(doc):
    overlap_warnings = []
    warnings = doc.GetWarnings()

    for warning in warnings:
        warning_text = warning.GetDescriptionText()
        if any(keyword in warning_text for keyword in ("floors overlap", "walls overlap")):
            overlap_warnings.append(warning)

    if overlap_warnings:
        ch_result = "Fail"
        ch_notes = str(len(overlap_warnings)) + " warnings"
    else:
        ch_result = "Pass"
        ch_notes = "N/A"

    results_table.append({"Check Number": "CH13-04",
                          "Description": "Element Overlap warning",
                          "Result": str(ch_result),
                          "Notes": str(ch_notes)})
    return


def check_parameters_score(parameters, cat_dict, doc):
    score_values = []
    for category_name, bic in sorted(cat_dict.items()):
        instances = FEC(doc).OfCategory(bic).WhereElementIsNotElementType().ToElements()
        not_placeholders = []
        for i in instances:
            workset_id = i.WorksetId
            for w in worksets:
                if w.Id == workset_id:
                    if "XX" not in str(w.Name) and "Enscape" not in str(w.Name):
                        not_placeholders.append(i)
        total = len(not_placeholders)

        if total == 0:
            continue
        for param_name in parameters:
            has_value = 0
            for el in not_placeholders:
                try:
                    param = el.LookupParameter(param_name)
                    param_value = param.AsValueString() if param else None
                except:
                    param_value = None
                if param_value and len(param_value.strip()) > 0:
                    has_value +=1
            param_score = round((float(has_value) / total) * 100, 2)
            score_values.append(param_score)
    try:
        average_score = round(float(sum(score_values)) / len(score_values), 2)
    except ZeroDivisionError:
        average_score = "N/A"
    return average_score


def check_nrm_score(doc):
    ch_notes = check_parameters_score(nrm_parameters, category_dict, doc)
    results_table.append({"Check Number": "CH10-13",
                          "Description": "Report NRM assigned %",
                          "Result": "-",
                          "Notes": str(ch_notes)+"%"})
    return


def check_uniclass_score(doc):
    ch_notes = check_parameters_score(uniclass_parameters, category_dict, doc)
    results_table.append({"Check Number": "CH10-10",
                          "Description": "Report Uniclass assigned %",
                          "Result": "-",
                          "Notes": str(ch_notes)+"%"})
    return


# ----Run checks -----------------------

check_units(doc)
check_base_and_survey_points(doc)
check_revit_links_pinned(doc)
check_no_imported_cads(doc)
check_grids_and_levels_pinned(doc)
check_worksets_with_levels_and_grids(doc)
check_startup_view_name(doc)
check_unplaced_views(doc)
check_unplaced_rooms(doc)
check_unenclosed_rooms(doc)
check_inplace(doc)
check_generic_model_instances(doc)
check_used_phases(doc)
check_warnings_count(doc)
check_duplicate_instance_warnings(doc)
check_overlap_warnings(doc)
check_nrm_score(doc)
check_uniclass_score(doc)
# -------Reformat results to report as a table ---------

table_data = []

for row in results_table:
    row_set = [row["Check Number"], row["Description"], row["Result"], row["Notes"]]
    table_data.append(row_set)

file_name = doc.PathName

output.print_md("_{}_".format(file_name))
output.print_table(table_data=table_data, columns=["Check Number", "Description", "Result", "Notes"])
