__title__ = "Room to Generic Model"
__doc__ = "Transforms rooms into Generic Model families and places them in same place. The shape of the family is " \
          "based on the room boundaries and room height. "

from pyrevit import revit, DB, script, forms, HOST_APP
import tempfile
import helper
import re
from Autodesk.Revit import Exceptions

logger = script.get_logger()
output = script.get_output()

selection = helper.select_rooms_filter()

if selection:
    # Create family doc from template
    # get file template from location
    fam_template_path = "C:\ProgramData\Autodesk\RVT " + \
                        HOST_APP.version + "\Family Templates\English\Metric Generic Model.rft"

    # iterate through rooms
    for room in selection:
        # helper: define inverted transform to translate room geometry to origin
        geo_translation = helper.inverted_transform(room)
        # collect room boundaries and translate them to origin
        room_boundaries = helper.room_bound_to_origin(room, geo_translation)

        if not room_boundaries:
            print("Extrusion failed for room {}. Try fixing room boundaries".format(output.linkify(room.Id)))
            break

        # define new family doc
        try:
            new_family_doc = revit.doc.Application.NewFamilyDocument(fam_template_path)
        except:
            forms.alert(msg="No Template",
                        sub_msg="There is no Generic Model Template",
                        ok=True,
                        warn_icon=True, exitscript=True)

        # Room params:
        dept = room.get_Parameter(DB.BuiltInParameter.ROOM_DEPARTMENT).AsString()
        if not dept:
            dept = "Generic Model"
        room_name = room.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()
        room_number = room.get_Parameter(DB.BuiltInParameter.ROOM_NUMBER).AsString()
        room_height = room.get_Parameter(DB.BuiltInParameter.ROOM_HEIGHT).AsValueString()
        # construct family and family type names:
        fam_name = str(dept) + "_" + room_name + "_" + room_number
        # replace bad characters
        fam_name = re.sub(r'[^\w\-_\. ]', '_', fam_name)
        fam_type_name = room_name

        # check if family already exists:
        while helper.get_fam(fam_name):
            fam_name = fam_name + "_Copy 1"

        # Save family in temp folder
        fam_path = tempfile.gettempdir() + "/" + fam_name + ".rfa"
        saveas_opt = DB.SaveAsOptions()
        saveas_opt.OverwriteExistingFile = True
        try:
            new_family_doc.SaveAs(fam_path, saveas_opt)
        except Exceptions.FileAccessException:
            fam_path = fam_path.replace(".rfa", "_Copy 1.rfa")
            new_family_doc.SaveAs(fam_path, saveas_opt)
            fam_name = fam_name + "_Copy 1"
        # Load Family into project
        with revit.Transaction("Load Family", revit.doc):
            try:

                loaded_f = revit.db.create.load_family(fam_path, doc=revit.doc)
                revit.doc.Regenerate()
            except Exception as err:
                logger.error(err)

        # Create extrusion from room boundaries
        with revit.Transaction(doc=new_family_doc, name="Create Extrusion"):

            extr_height = helper.convert_length_to_internal(float(room_height))
            ref_plane = helper.get_ref_lvl_plane(new_family_doc)
            extrusion = None
            # create extrusion, assign material, associate with shared parameter
            try:
                extrusion = new_family_doc.FamilyCreate.NewExtrusion(True, room_boundaries, ref_plane[0],
                                                                     extr_height)
                ext_mat_param = extrusion.get_Parameter(DB.BuiltInParameter.MATERIAL_ID_PARAM)
                # create and associate a material parameter
                new_mat_param = new_family_doc.FamilyManager.AddParameter("Material",
                                                                          DB.BuiltInParameterGroup.PG_MATERIALS,
                                                                          DB.ParameterType.Material,
                                                                          False)
                new_family_doc.FamilyManager.AssociateElementParameterToFamilyParameter(ext_mat_param,
                                                                                        new_mat_param)
            except Exceptions.InternalException:
                print("Extrusion failed for room {}. Try fixing room boundaries".format(output.linkify(room.Id)))
                break
            # save and close family
        save_opt = DB.SaveOptions()
        new_family_doc.Save(save_opt)
        new_family_doc.Close()

        # Reload family with extrusion and place it in the same position as the room
        with revit.Transaction("Reload Family", revit.doc):
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

                    if not fam_symbol.IsActive:
                        fam_symbol.Activate()
                        revit.doc.Regenerate()

                    # place family symbol at position
                    new_fam_instance = revit.doc.Create.NewFamilyInstance(room.Location.Point, fam_symbol,
                                                                          room.Level,
                                                                          str_type)

                    correct_lvl_offset = new_fam_instance.get_Parameter(
                        DB.BuiltInParameter.INSTANCE_FREE_HOST_OFFSET_PARAM).Set(0)
                    print(
                        "Created and placed family instance : {1} - {2} {0} ".format(
                            output.linkify(new_fam_instance.Id),
                            fam_name, fam_type_name))
