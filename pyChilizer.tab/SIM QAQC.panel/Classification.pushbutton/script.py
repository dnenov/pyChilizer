import sys

from pyrevit import DB, UI, revit, HOST_APP
from pyrevit import script, forms, coreutils
from csv import writer, reader
import os
import xlrd
import math
import csv

doc = revit.doc
FEC = DB.FilteredElementCollector
BIC = DB.BuiltInCategory
export_file_path = forms.pick_file(file_ext="csv")

parameters = ["ALD_Classification.NRM.1.Description",
              "ALD_Classification.NRM.1.Number",
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

worksets = DB.FilteredWorksetCollector(doc).OfKind(DB.WorksetKind.UserWorkset).ToWorksets()


def write_parameter_scores_to_csv(doc, parameters, category_dict, csv_path):
    """
    Writes a CSV with headers = parameter names, rows = category names,
    and values = % of instances with a value for each parameter.
    """
    try:
        with open(csv_path, mode="wb") as file:
            writer_obj = csv.writer(file, lineterminator="\n")

            # Write headers
            header_row = ["Category"] + parameters
            writer_obj.writerow(header_row)

            for category_name, bic in sorted(category_dict.items()):
                instances = FEC(doc).OfCategory(bic).WhereElementIsNotElementType().ToElements()
                not_placeholders = []
                for i in instances:
                    workset_id = i.WorksetId
                    for w in worksets:
                        if w.Id == workset_id:
                            if "XX" not in str(w.Name) and "Enscape" not in str(w.Name) and "AA_Site Context" not in str(w.Name):
                                not_placeholders.append(i)
                total = len(not_placeholders)
                if total == 0:
                    continue

                row = [category_name]
                for param_name in parameters:
                    has_value = 0
                    for el in not_placeholders:
                        try:
                            param = el.LookupParameter(param_name)
                            param_value = param.AsValueString() if param else None
                        except:
                            param_value = None

                        if param_value and len(param_value.strip()) > 0:
                            has_value += 1

                    score = round((float(has_value) / total) * 100, 2)
                    score_values.append(score)
                    row.append(score)
                writer_obj.writerow(row)
    except Exception as e:
        forms.alert(str(e), exitscript=True)


# def get_workset_by_id(w_id):
#     worksets = DB.FilteredWorksetCollector(doc).OfKind(DB.WorksetKind.UserWorkset).ToWorksets()
#     for w in worksets:
#         if w.Id == w_id:
#             return w

score_values = []
write_parameter_scores_to_csv(doc, parameters, category_dict, export_file_path)
# print (score_values)
average = round(float(sum(score_values)) / len (score_values), 2)
print ("Overall score : {}".format(average))

for category_name in category_dict.keys():
    bic = category_dict[category_name]
    instances_of_category = FEC(doc).OfCategory(bic).WhereElementIsNotElementType().ToElements()
    not_placeholders = []
    for i in instances_of_category:
        workset_id = i.WorksetId
        for w in worksets:
            if w.Id == workset_id:
                if "XX" not in str(w.Name) and "Enscape" not in str(w.Name):
                    not_placeholders.append(i)
    if len(not_placeholders) == 0:
        continue
    # Write category name
    # print("CATEGORY {}\n \t Instances : {} ".format(category_name, len(instances_of_category)))
    for param_name in parameters:
        has_value = 0
        no_value = 0
        param_not_added = 0
        total = len(not_placeholders)
        for el_instance in not_placeholders:
            param_value = None
            try:
                param = el_instance.LookupParameter(param_name)
                param_value = param.AsValueString() if param else None
            except AttributeError:
                param_not_added += 1
            if not param_value:
                no_value += 1
            elif len(param_value) > 0:
                has_value += 1
        if not total == 0:
            score = round((float(has_value) / total) * 100, 2)
        else:
            score = "N/A"
        # if score != "N/A":
        #     print("-- Parameter : {} \t\tScore: {:.2f}% \t({}/{})".format(param_name, score, has_value, total))
        # else:
        #     print("-- Parameter : {} \t\tScore: {} \t({}/{})".format(param_name, score, has_value, total))


