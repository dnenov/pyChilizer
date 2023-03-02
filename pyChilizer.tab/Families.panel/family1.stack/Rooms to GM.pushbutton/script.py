from pyrevit import revit, DB, script, forms, HOST_APP
import tempfile
from pychilizer import geo, select, database
import re
import config
from Autodesk.Revit import Exceptions
from os.path import isfile


logger = script.get_logger()
output = script.get_output()

selection = select.select_with_cat_filter(DB.BuiltInCategory.OST_Rooms, "Pick Rooms to Transform")

if selection:
    # Create family doc from template
    fam_template_path = __revit__.Application.FamilyTemplatePath + database.get_generic_family_template_name()
    # check family template exists
    if not isfile(fam_template_path):
        forms.alert(title="No Generic Template Found",
                    msg="There is no Generic Model Template in the default location. Can you point where to get it?",
                    ok=True)
        fam_template_path = forms.pick_file(file_ext="rft",
                                            init_dir="C:\ProgramData\Autodesk\RVT " + HOST_APP.version + "\Family Templates")
    # iterate through rooms
    for room in selection:

        # define new family doc
        try:
            new_family_doc = revit.doc.Application.NewFamilyDocument(fam_template_path)
        except NameError:
            forms.alert(msg="No Template",
                        sub_msg="There is no Generic Model Template in the default location.",
                        ok=True,
                        warn_icon=True, exitscript=True)

        # To name the room, collect its parameters:
        project_number = revit.doc.ProjectInformation.Number
        if not project_number:
            project_number = "Project"
        dept = room.get_Parameter(DB.BuiltInParameter.ROOM_DEPARTMENT).AsString()
        if not dept:
            dept = "Department"
        room_name = room.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()
        room_number = room.get_Parameter(DB.BuiltInParameter.ROOM_NUMBER).AsString()

        # construct family and family type names:
        fam_name = str(dept) + "_" + room_name + "_" + room_number
        # replace bad characters
        fam_name = re.sub(r'[^\w\-_\. ]', '', fam_name)
        fam_type_name = re.sub(r'[^\w\-_\. ]', '', room_name)

        # check if family already exists:
        while database.get_fam_any_type(fam_name):
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

        # Create extrusion from room boundaries
        with revit.Transaction(doc=new_family_doc, name="Create Extrusion"):
            if config.get_config() == "Extrusion":
                geo.room_to_extrusion(room, new_family_doc)
                placement_point = room.Location.Point
            else:
                geo.room_to_freeform(room, new_family_doc)
                placement_point = room.get_BoundingBox(None).Min
        # save and close family
        save_opt = DB.SaveOptions()
        new_family_doc.Save(save_opt)
        new_family_doc.Close()

        # Load family with extrusion and place it in the same position as the room
        with revit.Transaction("Load Family", revit.doc):
            loaded_f = revit.db.create.load_family(fam_path, doc=revit.doc)
            # find family symbol and activate
            fam_symbol = database.get_fam_any_type(fam_name)
            if not fam_symbol.IsActive:
                fam_symbol.Activate()
                revit.doc.Regenerate()
            # place family symbol at position

            new_fam_instance = revit.doc.Create.NewFamilyInstance(placement_point, fam_symbol,
                                                                  room.Level,
                                                                  DB.Structure.StructuralType.NonStructural)
            correct_lvl_offset = new_fam_instance.get_Parameter(
                DB.BuiltInParameter.INSTANCE_FREE_HOST_OFFSET_PARAM).Set(0)
            print(
                "Created and placed family instance : {1} - {2} {0} ".format(
                    output.linkify(new_fam_instance.Id),
                    fam_name, fam_type_name))
