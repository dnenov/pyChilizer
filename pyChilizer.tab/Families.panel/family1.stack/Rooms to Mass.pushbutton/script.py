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
        with revit.Transaction(doc=new_family_doc, name="Create Extrusion"):

            try:
                room_height = room.get_Parameter(DB.BuiltInParameter.ROOM_HEIGHT).AsDouble()
                room_ref_array = DB.ReferenceArray()
                for bnd in room_boundaries:
                    endpoints = []
                    for curve in bnd:
                        endpoints.append(new_family_doc.FamilyCreate.NewReferencePoint(curve.GetEndPoint(1)))

                    for i in range(len(endpoints)):
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
                extrusion = new_family_doc.FamilyCreate.NewExtrusionForm(True, room_ref_array,
                                                                          DB.XYZ(0, 0, room_height))
                ext_mat_param = extrusion.get_Parameter(DB.BuiltInParameter.MATERIAL_ID_PARAM)

                # create and associate a material parameter
                new_mat_param = new_family_doc.FamilyManager.AddParameter("Material",
                                                                          DB.BuiltInParameterGroup.PG_MATERIALS,
                                                                          DB.ParameterType.Material,
                                                                          False)
                new_family_doc.FamilyManager.AssociateElementParameterToFamilyParameter(ext_mat_param, new_mat_param)

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

                    new_fam_instance = revit.doc.Create.NewFamilyInstance(room.Level.GetPlaneReference(),
                                                                          room.Location.Point,
                                                                          DB.XYZ(1,0,0),
                                                                          fam_symbol
                                                                          )