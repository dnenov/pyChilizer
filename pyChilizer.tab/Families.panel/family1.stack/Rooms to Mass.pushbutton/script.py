__title__ = "Room to Mass"
__doc__ = "Transforms rooms into Mass families."

from pyrevit import revit, DB, script, forms, HOST_APP
from rpw.ui.forms import (FlexForm, Label, ComboBox, Separator, Button)
import tempfile
import helper
from pyrevit.revit.db import query

logger = script.get_logger()

# use preselected elements, filtering rooms only
pre_selection = helper.preselection_with_filter("Rooms")
# or select rooms
if pre_selection and forms.alert("You have selected {} elements. Do you want to use them?".format(len(pre_selection))):
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
        # geo_translation = helper.inverted_transform(room)
        # collect room boundaries and translate them to origin
        # room_boundaries = helper.room_bound_to_origin(room, geo_translation)


        mass_placement_point = room.get_BoundingBox(None).Min
        # define new family doc
        try:
            new_family_doc = revit.doc.Application.NewFamilyDocument(fam_template_path)
        except:
            forms.alert(msg="No Template",
                        sub_msg="There is no Conceptual Mass Template",
                        ok=True,
                        warn_icon=True, exitscript=True)

        # Name the Family ( Proj_Type_Name : Type)
        # get values of selected Room parameters and replace with default values if empty:
        # Project Number:
        project_number = revit.doc.ProjectInformation.Number
        if not project_number:
            project_number = "Project"
        # Department:
        dept = room.get_Parameter(DB.BuiltInParameter.ROOM_DEPARTMENT).AsString()  # chosen parameter for Department
        if not dept:
            dept = "Department"
        # Room name:
        room_name = room.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()

        # construct family and family type names:
        fam_name = project_number + "_" + str(dept) + "_" + room_name
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
        with revit.Transaction(doc=new_family_doc, name="Create FreeForm Element"):

            room_geo = room.ClosedShell
            for geo in room_geo:
                if isinstance(geo, DB.Solid) and geo.Volume > 0.0:
                    freeform = DB.FreeFormElement.Create(new_family_doc, geo)
                    new_family_doc.Regenerate()
                    delta = DB.XYZ(0,0,0) - freeform.get_BoundingBox(None).Min
                    move_ff = DB.ElementTransformUtils.MoveElement(
                        new_family_doc, freeform.Id, delta
                    )
                    # create and associate a material parameter
                    ext_mat_param = freeform.get_Parameter(DB.BuiltInParameter.MATERIAL_ID_PARAM)
                    new_mat_param = new_family_doc.FamilyManager.AddParameter("Mass Material",
                                                                              DB.BuiltInParameterGroup.PG_MATERIALS,
                                                                              DB.ParameterType.Material,
                                                                              True)
                    new_family_doc.FamilyManager.AssociateElementParameterToFamilyParameter(ext_mat_param, new_mat_param)

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
                    if not fam_symbol.IsActive:
                        fam_symbol.Activate()
                        revit.doc.Regenerate()

                    new_fam_instance = revit.doc.Create.NewFamilyInstance(room.Level.GetPlaneReference(),
                                                                          mass_placement_point,
                                                                          DB.XYZ(1, 0, 0),
                                                                          fam_symbol
                                                                          )
