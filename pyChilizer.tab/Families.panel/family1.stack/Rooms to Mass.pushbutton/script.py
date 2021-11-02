__title__ = "Room2Mass"
__doc__ = "Transforms rooms into Generic Model families. Carries over unit parameters. Copies tenure from name"

from pyrevit import revit, DB, script, forms, HOST_APP
from rpw.ui.forms import (FlexForm, Label, ComboBox, Separator, Button)
import tempfile
import helper
from pyrevit.revit.db import query

logger = script.get_logger()

# get shared parameter for the extrusion material


sp_unit_material = helper.get_shared_param_by_name_type("Unit Material", DB.ParameterType.Material)
if not sp_unit_material:
    forms.alert(msg="No suitable parameter", \
        sub_msg="There is no suitable parameter to use for Unit Material. Please add a shared parameter 'Unit Material' of Material Type", \
        ok=True, \
        warn_icon=True, exitscript=True)

inst_param_list = [
    "Core Nr",
    "Flat Orientation"
]

type_param_list = [
    "Tenure",
    "Unit Type",
    "Unit Area"
]

not_found = []
# any_gm_inst = DB.FilteredElementCollector(revit.doc).OfCategory(DB.BuiltInCategory.OST_GenericModel).WhereElementIsNotElementType().FirstElement()
# any_gm_type = DB.FilteredElementCollector(revit.doc).OfCategory(DB.BuiltInCategory.OST_GenericModel).WhereElementIsElementType().FirstElement()
# for par in inst_param_list:
#     exists = None
#     el_param_set = any_gm_inst.Parameters
#     for p in el_param_set:
#
#         if p.Definition.Name == par:
#             exists = True
#     if not exists:
#         not_found.append(par)
#
# for par in type_param_list:
#     exists = None
#     el_param_set = any_gm_type.Parameters
#     for p in el_param_set:
#         if p.Definition.Name == par:
#             exists = True
#     if not exists:
#         not_found.append(par)
#
# if not_found:
#     forms.alert("Parameters not found. Please add Shared Parameters: \n\n{}".format("\n".join(not_found)), warn_icon=True, exitscript=True)

# use preselected elements, filtering rooms only
pre_selection = helper.preselection_with_filter("Rooms")
# or select rooms
if pre_selection:
    selection = pre_selection
else:
    selection = helper.select_rooms_filter()

if selection:
    # Create family doc from template
    # get file template from location
    fam_template_path = "C:\ProgramData\Autodesk\RVT " + \
                        HOST_APP.version + "\Family Templates\English\Conceptual Mass\Metric Mass.rft"

    # iterate through rooms
    for room in selection:
        # helper: define inverted transform to translate room geometry to origin
        geo_translation = helper.inverted_transform(room)
        # collect room boundaries and translate them to origin
        room_boundaries = helper.room_bound_to_origin(room, geo_translation)

        # define new family doc
        try:
            new_family_doc = revit.doc.Application.NewFamilyDocument(fam_template_path)
        except:
            forms.alert(msg="No Template",
                        sub_msg="There is no Conceptual Mass Template",
                        ok=True,
                        warn_icon=True, exitscript=True)
        # Name the Family ( Proj_Ten_Type_Name : Ten_Type)
        # get values of selected Room parameters and replace with default values if empty:
        # Project Number:
        project_number = revit.doc.ProjectInformation.Number
        if not project_number:
            project_number = "H&P"
        # Department:
        dept = room.get_Parameter(DB.BuiltInParameter.ROOM_DEPARTMENT).AsString()  # chosen parameter for Department
        if not dept:
            dept = "Unit"

        # Room name:
        room_name = room.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()

        # Tenure:
        if "SR" in room_name:
            tenure_code = "Social Rent"
        elif "SO" in room_name:
            tenure_code = "Shared Ownership"
        elif "PS" in room_name:
            tenure_code = "Private"
        elif "PR" in room_name:
            tenure_code = "PRS"
        else:
            tenure_code = ""

        # Unit Type:
        if "1B1P" in room_name:
            unit_type = "1B1P"
            dept = "Flat"
        elif "1B2P(A)" in room_name or "1B2P (A)" in room_name:
            unit_type = "1B2P(A)"
            dept = "Flat"
        elif "1B2P" in room_name:
            unit_type = "1B2P"
            dept = "Flat"
        elif "2B3P(A)" in room_name or "2B3P (A)" in room_name:
            unit_type = "2B3P(A)"
            dept = "Flat"
        elif "2B3P" in room_name:
            unit_type = "2B3P"
            dept = "Flat"
        elif "2B4P(A)" in room_name or "2B4P (A)" in room_name:
            unit_type = "2B4P(A)"
            dept = "Flat"
        elif "2B4P" in room_name:
            unit_type = "2B4P"
            dept = "Flat"
        elif "3B5P(D)"in room_name or "3B5P (D)" in room_name:
            unit_type = "3B5P(D)"
            dept = "Flat"
        elif "3B5P" in room_name:
            unit_type = "3B5P"
            dept = "Flat"
        elif "4B6P(D)"in room_name or "4B6P (D)" in room_name:
            unit_type = "4B6P(D)"
            dept = "Flat"
        elif "3B6P" in room_name:
            unit_type = "3B6P"
            dept = "Flat"
        elif "4B6P" in room_name:
            unit_type = "4B6P"
            dept = "Flat"

        else:
            unit_type = ""


        # Room area:
        unit_area = room.get_Parameter(DB.BuiltInParameter.ROOM_AREA).AsDouble()

        # Room number (to be used as layout type differentiation)
        room_number = room.get_Parameter(DB.BuiltInParameter.ROOM_NUMBER).AsString()
        # if not room_number:
        #    room_number = str(room.Id)

        # construct family and family type names:
        fam_name = project_number + "_" + str(dept) + "_" + room_name + "_" + room_number
        # replace spaces
        fam_name = fam_name.strip(" ")
        fam_type_name = room_name

        # check if family already exists:
        if helper.get_fam(fam_name):
            while helper.get_fam(fam_name):
                fam_name = fam_name + "_Copy 1"

        # Save family in temp folder
        fam_path = tempfile.gettempdir() + "/" + fam_name + ".rfa"
        saveas_opt = DB.SaveAsOptions()
        saveas_opt.OverwriteExistingFile = True
        new_family_doc.SaveAs(fam_path, saveas_opt)

        # Load Family into project
        with revit.Transaction("Load Family", revit.doc):
            try:
                loaded_f = revit.db.create.load_family(fam_path, doc=revit.doc)
                revit.doc.Regenerate()
            except Exception as err:
                logger.error(err)

        # Create extrusion from room boundaries
        with revit.Transaction(doc=new_family_doc, name="Create Extrusion"):

            try:
                extrusion_height = helper.convert_length_to_internal(2500)
                room_ref_array = DB.ReferenceArray()
                for bnd in room_boundaries:
                    endpoints = []
                    for curve in bnd:
                        endpoints.append(new_family_doc.FamilyCreate.NewReferencePoint(curve.GetEndPoint(1)))

                    for i in range(len(endpoints)):
                        #print(i)

                        refptarr = DB.ReferencePointArray()
                        if i < len(endpoints) - 1:

                            refptarr.Append(endpoints[i])
                            refptarr.Append(endpoints[i + 1])
                            line = new_family_doc.FamilyCreate.NewCurveByPoints(refptarr)
                            room_ref_array.Append(line.GeometryCurve.Reference)
                        else:
                            refptarr.Append(endpoints[i])
                            refptarr.Append(endpoints[0])
                            line = new_family_doc.FamilyCreate.NewCurveByPoints(refptarr)
                            room_ref_array.Append(line.GeometryCurve.Reference)

                ref_plane = helper.get_ref_lvl_plane(new_family_doc)
                # create extrusion, assign material, associate with shared parameter
                #extrusion = new_family_doc.FamilyCreate.NewExtrusion(True, room_boundaries, ref_plane[0],extrusion_height)
                extrusion = new_family_doc.FamilyCreate.NewExtrusionForm(True, room_ref_array,
                                                                          DB.XYZ(0, 0, extrusion_height))
                ext_mat_param = extrusion.get_Parameter(DB.BuiltInParameter.MATERIAL_ID_PARAM)
                try:
                    new_mat_param = new_family_doc.FamilyManager.AddParameter(sp_unit_material,
                    DB.BuiltInParameterGroup.PG_MATERIALS, False)
                    new_family_doc.FamilyManager.AssociateElementParameterToFamilyParameter(ext_mat_param, new_mat_param)
                except Exception as err:
                    logger.error(err)

            except Exception as err:
                logger.error(err)

        # save and close family
        save_opt = DB.SaveOptions()
        new_family_doc.Save(save_opt)
        new_family_doc.Close()

        # Reload family with extrusion and place it in the same position as the room
        with revit.Transaction("Reload Family", revit.doc):
            # try:
            loaded_f = revit.db.create.load_family(fam_path, doc=revit.doc)
            revit.doc.Regenerate()
            str_type = DB.Structure.StructuralType.NonStructural
            # find family symbol and activate
            fam_symbol = None
            get_fam = DB.FilteredElementCollector(revit.doc).OfClass(DB.FamilySymbol).OfCategory(
                DB.BuiltInCategory.OST_Mass).WhereElementIsElementType().ToElements()
            for fam in get_fam:
                type_name = fam.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
                if str.strip(type_name) == fam_name:
                    fam_symbol = fam
                    fam_symbol.Name = fam_type_name
                    # set type parameters
                    fam_symbol.get_Parameter(DB.BuiltInParameter.ALL_MODEL_DESCRIPTION).Set(dept)
#                        fam_symbol.LookupParameter("Unit Area").Set(unit_area)
                    if not fam_symbol.IsActive:
                        fam_symbol.Activate()
                        revit.doc.Regenerate()

                    # try:
                    #     # set tenure
                    #     fam_symbol.LookupParameter("Tenure").Set(tenure_code)
                    # except:
                    #     pass
                    # try:
                    #     # set unit type
                    #     fam_symbol.LookupParameter("Unit Type").Set(unit_type)
                    # except:
                    #     pass
                    # # place family symbol at position
                    # new_fam_instance = revit.doc.Create.NewFamilyInstance(room.Location.Point, fam_symbol, room.Level,
                    #                                                       str_type)

                    new_fam_instance = revit.doc.Create.NewFamilyInstance(room.Level.GetPlaneReference(),
                                                                          room.Location.Point,
                                                                          DB.XYZ(1,0,0),
                                                                          fam_symbol
                                                                          )
                    # correct_lvl_offset = new_fam_instance.get_Parameter(
                    #     DB.BuiltInParameter.INSTANCE_FREE_HOST_OFFSET_PARAM).Set(0)

                    #new_fam_instance.get_Parameter(DB.BuiltInParameter.FAMILY_LEVEL_PARAM).Set(room.Level.Id.IntegerValue)

                    # set instance parameters
                    # get Core Nr

                    # core_nr = room.LookupParameter("Core Nr").AsString()
                    # flat_orientation = room.LookupParameter("Flat Orientation").AsString()
                    # new_fam_instance.LookupParameter("Core Nr").Set(core_nr)
                    # new_fam_instance.LookupParameter("Flat Orientation").Set(flat_orientation)




           # except Exception as err:
               # logger.error(err)
            # except:
            #     pass