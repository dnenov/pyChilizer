__title__ = "Populate COBie\nInformation"
__doc__ = "Populate COBie related information inside Families."

from pyrevit import HOST_APP
from pyrevit import revit, DB, UI, script, forms

from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, Transaction, TransactionGroup, BuiltInParameter


class FamilyLoaderOptionsHandler(DB.IFamilyLoadOptions):
    def OnFamilyFound(self, familyInUse, overwriteParameterValues): #pylint: disable=W0613
        """A method called when the family was found in the target document."""
        return True
    def OnSharedFamilyFound(self, sharedFamily, familyInUse, overwriteParameterValues):
        source = DB.FamilySource.Family
        overwriteParameterValues = True
        return True


def PopulateParameters(_fam_doc, _s_params, _params):
    # print('populate')
    try:
        t = Transaction(_fam_doc, 'Populate Parameters')
        t.Start()
        for key in _params:
            s_param = _s_params[key]
            if _fam_doc.FamilyManager.get_Parameter(s_param):
                continue
            _fam_doc.FamilyManager.AddParameter(s_param, DB.BuiltInParameterGroup.PG_DATA, False)                
        _fam_doc.Regenerate()   # Not sure if it is necessary
        t.Commit()
    except Exception as e:
        t.RollBack()
        print(str(e))


def SetParameter(_fam_doc, _s_param, _v_param, _fam_type):
    # print('set parameters')
    ts = Transaction(_fam_doc, 'Set Parameters')
    ts.Start()

    param = _fam_doc.FamilyManager.get_Parameter(_s_param)
    if not param:
        return
    
    if _s_param == "ART_TypeMark" or _s_param == "IfcName" or _s_param == "COBie.Type.Name":
        _fam_doc.FamilyManager.Set(param, _fam_type.Name)
    elif _s_param == "IfcDescription":
        d_param = _fam_doc.FamilyManager.get_Parameter("Description")
        description = _fam_type.AsString(d_param)
        _fam_doc.FamilyManager.Set(param, description)
    elif _s_param == "COBie.Type":
        _fam_doc.FamilyManager.Set(param, 1)
    else:
        _fam_doc.FamilyManager.Set(param, _v_param)

    ts.Commit()


uidoc = revit.uidoc
doc = revit.doc

df = HOST_APP.app.OpenSharedParameterFile()
dgs = df.Groups

s_params = {}
debug = ''

for dg in dgs:
    for d in dg.Definitions:
        if d:
            s_params[d.Name] = d
            debug += 'Parameter {}\n'.format(d.Name)

parameters = {}
w_parameters = {}

parameters["ART_TypeMark"] = " "  #Family Type
parameters["Classification.Uniclass.EF.Description"] = "Doors and windows"
parameters["Classification.Uniclass.EF.Number"] = "EF_25_30"
parameters["Classification.Uniclass.Pr.Description"] = "Doorsets"
parameters["Classification.Uniclass.Pr.Number"] = "Pr_30_59_24"
parameters["Classification.Uniclass.Ss.Description"] = "Door systems"			
parameters["Classification.Uniclass.Ss.Number"] = "Ss_25_30_20"
parameters["ClassificationCode"] = "[Uniclass_Pr Classification]Pr_30_59_24:Doorsets"
parameters["COBie.Type"] = "yes"
parameters["COBie.Type.AssetType"] = "Fixed"
parameters["COBie.Type.Category"] = "Pr_30_59_24 : Doorsets"
parameters["COBie.Type.CreatedBy"] = "emily.partridge@architype.co.uk"
parameters["IfcDescription"] = " ";	#Description
parameters["IfcExportAs"] = "IfcWindowType.DOOR"
parameters["IfcName"] = " ";	#Family Type		

w_parameters["ART_TypeMark"] = " "  #Family Type
w_parameters["Classification.Uniclass.EF.Description"] = "Doors and windows"
w_parameters["Classification.Uniclass.EF.Number"] = "EF_25_30"
w_parameters["Classification.Uniclass.Pr.Description"] = "Window units"
w_parameters["Classification.Uniclass.Pr.Number"] = "Pr_30_59_98"
w_parameters["Classification.Uniclass.Ss.Description"] = "Window systems"			
w_parameters["Classification.Uniclass.Ss.Number"] = "Ss_25_30_95"
w_parameters["ClassificationCode"] = "[Uniclass_Pr Classification]Pr_30_59_98:Window units"
w_parameters["COBie.Type"] = "yes"
w_parameters["COBie.Type.AssetType"] = "Fixed"
w_parameters["COBie.Type.Category"] = "Pr_30_59_95 : Windows units"
w_parameters["COBie.Type.CreatedBy"] = "emily.partridge@architype.co.uk"
w_parameters["IfcDescription"] = " ";	#Description
w_parameters["IfcExportAs"] = "IfcWindowType.WINDOW"
w_parameters["IfcName"] = " ";	#Family Type		


# 1. Get selection
# 2. Get unique families
# 3. for foreach Family
# 4. Get into the family and 
# 5. For each parameter in our list, create a new parameter and populate it
# 6. Save, close

# 1
selection = uidoc.Selection.PickObjects(UI.Selection.ObjectType.Element, "Pick elements")

# 2
families = set()

for f_ref in selection:
    fam = doc.GetElement(f_ref)
    if not fam:
        continue
    families.add(fam.Symbol.Family.Id)			

log = ""

# 3

count = 0

with forms.ProgressBar(title='Families') as pb:
    for id in families:
        pb.update_progress(count, len(families))
        count += 1

        n_count = 0
        fam = doc.GetElement(id)
        if not fam:
            continue
        
        # 4
        fam_doc = doc.EditFamily(fam)

        # 5
        tg = TransactionGroup(fam_doc, 'Families')
        tg.Start()

        PopulateParameters(fam_doc, s_params, w_parameters)

        fam_types = fam_doc.FamilyManager.Types
        fam_iter = fam_types.ForwardIterator()
        fam_iter.Reset()
        
        with forms.ProgressBar(title='Nested') as pn:
            while fam_iter.MoveNext():
                pn.update_progress(n_count, fam_types.Size)
                n_count += 1

                fam_type = fam_iter.Current

                t = Transaction(fam_doc, 'Set FamilyType')
                t.Start()
                fam_doc.FamilyManager.CurrentType = fam_type
                t.Commit()

                try:
                    for key in w_parameters:
                        s_param = key
                        v_param = w_parameters[key]

                        SetParameter(fam_doc, s_param, v_param, fam_type)

                    log += fam_type.Name + "\n"
                except Exception as e:
                    t.RollBack()
                    print(str(e))



        tg.Assimilate()

        tf = Transaction(fam_doc, 'Push back')
        tf.Start()
        fam = fam_doc.LoadFamily(doc, FamilyLoaderOptionsHandler())
        tf.Commit()

# print(families)