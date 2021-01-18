__title__ = "Room Calculation\nPoint"
__doc__ = "Add Room Calculation Point to multiple Families \nv1.0"

from pyrevit import revit, DB, HOST_APP, UI
from pyrevit.framework import List
from pyrevit.forms import ProgressBar


# http://www.revitapidocs.com/2018.1/5da8e3c5-9b49-f942-02fc-7e7783fe8f00.htm
class FamilyLoaderOptionsHandler(DB.IFamilyLoadOptions):
    def OnFamilyFound(self, familyInUse, overwriteParameterValues): #pylint: disable=W0613
        """A method called when the family was found in the target document."""
        return True

    def OnSharedFamilyFound(self,
                            sharedFamily, #pylint: disable=W0613
                            familyInUse, #pylint: disable=W0613
                            source, #pylint: disable=W0613
                            overwriteParameterValues): #pylint: disable=W0613
        source = DB.FamilySource.Family
        overwriteParameterValues = True
        return True


def AddRoomCalcPoint(_doc):
    family = _doc.OwnerFamily
    param = family.get_Parameter(DB.BuiltInParameter.ROOM_CALCULATION_POINT)
    if not param:
        return
    with DB.Transaction(_doc, "AddRoomCalcPoint") as t:
        t.Start()
        param.Set(1)
        t.Commit()


def GetSharedParameterFile():
    if HOST_APP.app.SharedParametersFilename:
            sparamf = HOST_APP.app.OpenSharedParameterFile()
            if sparamf:
                return sparamf


def GetElements(_selection):
    elements = []
    for ref in _selection:
        elements.append(revit.doc.GetElement(ref))
    return elements


spfile = GetSharedParameterFile()
selection = revit.get_selection()

if len(selection) == 0:
    selection = GetElements(revit.uidoc.Selection.PickObjects(UI.Selection.ObjectType.Element))

counter = 0
max_value = len(selection)

with ProgressBar(cancellable=True, step=1) as pb:
    for sel in selection:
        fam_ins = sel
        fam = fam_ins.Symbol.Family
        fam_doc = revit.doc.EditFamily(fam)

        AddRoomCalcPoint(fam_doc)

        # print("Is document modifiable? " + str(revit.doc.IsModifiable))
        fam = fam_doc.LoadFamily(revit.doc, FamilyLoaderOptionsHandler())
        counter += 1
        pb.update_progress(counter, max_value)


