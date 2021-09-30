__title__ = "Room to\n Generic Model"
__doc__ = "Transforms rooms into Generic Model families. Carries over unit parameters"

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

# check if required parameters exit

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
                        HOST_APP.version + "\Family Templates\English\Metric Generic Model.rft"

    # format parameters for UI
    # gather and organize Room parameters: (only editable text params)
    room_parameter_set = selection[0].Parameters
    room_params_text = [p.Definition.Name for p in room_parameter_set if
                        p.StorageType.ToString() == "String" and p.IsReadOnly == False]
    # collect and organize Generic Model parameters: (only editable text type params)
    gm_parameter_set = helper.param_set_by_cat(DB.BuiltInCategory.OST_GenericModel)
    gm_params_text = [p for p in gm_parameter_set if p.StorageType.ToString() == "String"]
    gm_params_area = [p for p in gm_parameter_set if p.Definition.ParameterType.ToString()=="Area"]

    if not gm_params_area:
        forms.alert(msg="No suitable parameter",
                    sub_msg="There is no suitable parameter to use for Unit Area. Please add a shared parameter 'Unit Area' of Area Type",
                    ok=True,
                    warn_icon=True, exitscript=True)

    gm_dict1 = {p.Definition.Name: p for p in gm_params_text}
    gm_dict2 = {p.Definition.Name: p for p in gm_params_area}
    # construct rwp UI
    components = [
        Label("[Department] Match Room parameters:"),
        ComboBox(name="room_combobox1", options=room_params_text, default="Department"),
        Label("[Description] to Generic Model parameters:"),
        ComboBox("gm_combobox1", gm_dict1, default="Description"),
        Label("[Unit Area] parameter:"),
        ComboBox("gm_combobox2", gm_dict2),
        Button("Select")]
    form = FlexForm("Match parameters", components)
    form.show()
    # assign chosen parameters
    chosen_room_param1 = form.values["room_combobox1"]
    chosen_gm_param1 = form.values["gm_combobox1"]
    chosen_gm_param2 = form.values["gm_combobox2"]



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
                        sub_msg="There is no Generic Model Template",
                        ok=True,
                        warn_icon=True, exitscript=True)
        # Name the Family ( Proj_Ten_Type_Name : Ten_Type)
        # get values of selected Room parameters and replace with default values if empty:
        # Project Number:
        project_number = revit.doc.ProjectInformation.Number
        if not project_number:
            project_number = "H&P"
        # Department:
        dept = room.LookupParameter(chosen_room_param1).AsString()  # chosen parameter for Department
        if not dept:
            dept = "Unit"
        # Room name:
        room_name = room.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()
        #       print (room_name)
        # except:
        #   room_name = str(room.Id)

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
                ref_plane = helper.get_ref_lvl_plane(new_family_doc)
                # create extrusion, assign material, associate with shared parameter
                extrusion = new_family_doc.FamilyCreate.NewExtrusion(True, room_boundaries, ref_plane[0],
                                                                         extrusion_height)
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
            try:
                loaded_f = revit.db.create.load_family(fam_path, doc=revit.doc)
                revit.doc.Regenerate()
                str_type = DB.Structure.StructuralType.NonStructural
                # find family symbol and activate
                fam_symbol = None
                get_fam = DB.FilteredElementCollector(revit.doc).OfClass(DB.FamilySymbol).OfCategory(
                    DB.BuiltInCategory.OST_GenericModel).WhereElementIsElementType().ToElements()
                for fam in get_fam:
                    type_name = fam.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
                    if str.strip(type_name) == fam_name:
                        fam_symbol = fam
                        fam_symbol.Name = fam_type_name
                        # set type parameters
                        fam_symbol.LookupParameter(chosen_gm_param1.Definition.Name).Set(dept)
                        fam_symbol.LookupParameter(chosen_gm_param2.Definition.Name).Set(unit_area)
                        if not fam_symbol.IsActive:
                            fam_symbol.Activate()
                            revit.doc.Regenerate()

                        # place family symbol at postision
                        new_fam_instance = revit.doc.Create.NewFamilyInstance(room.Location.Point, fam_symbol, room.Level,
                                                                              str_type)
                        correct_lvl_offset = new_fam_instance.get_Parameter(
                            DB.BuiltInParameter.INSTANCE_FREE_HOST_OFFSET_PARAM).Set(0)
            except Exception as err:
                logger.error(err)