__title__ = "Count Annotation"
__doc__ = "Shows breakdown of annotation elements by category"

from pyrevit import revit, DB, script, forms
from pyrevit.framework import List

anno_cat_list = [DB.BuiltInCategory.OST_DuctTerminalTags,
                 DB.BuiltInCategory.OST_BeamAnalyticalTags,
                 DB.BuiltInCategory.OST_BraceAnalyticalTags,
                 DB.BuiltInCategory.OST_ColumnAnalyticalTags,
                 DB.BuiltInCategory.OST_FloorAnalyticalTags,
                 DB.BuiltInCategory.OST_FloorAnalyticalTags,
                 DB.BuiltInCategory.OST_IsolatedFoundationAnalyticalTags,
                 DB.BuiltInCategory.OST_LinkAnalyticalTags,
                 DB.BuiltInCategory.OST_NodeAnalyticalTags,
                 DB.BuiltInCategory.OST_AnalyticalPipeConnectionLineSymbol,
                 DB.BuiltInCategory.OST_FoundationSlabAnalyticalTags,
                 DB.BuiltInCategory.OST_WallFoundationAnalyticalTags,
                 DB.BuiltInCategory.OST_WallAnalyticalTags,
                 DB.BuiltInCategory.OST_StructConnectionAnchorTags,
                 DB.BuiltInCategory.OST_AreaLoadTags,
                 DB.BuiltInCategory.OST_AreaTags,
                 DB.BuiltInCategory.OST_AssemblyTags,
                 DB.BuiltInCategory.OST_StructConnectionBoltTags,
                 DB.BuiltInCategory.OST_CableTrayFittingTags,
                 DB.BuiltInCategory.OST_CableTrayTags,
                 DB.BuiltInCategory.OST_CaseworkTags,
                 DB.BuiltInCategory.OST_CeilingTags,
                 DB.BuiltInCategory.OST_CommunicationDeviceTags,
                 DB.BuiltInCategory.OST_ConduitFittingTags,
                 DB.BuiltInCategory.OST_StructConnectionSymbols,
                 DB.BuiltInCategory.OST_ContourLabels,
                 DB.BuiltInCategory.OST_CurtainWallPanelTags,
                 DB.BuiltInCategory.OST_DataDeviceTags,
                 DB.BuiltInCategory.OST_IOSDetailGroups,
                 DB.BuiltInCategory.OST_DetailComponentTags,
                 DB.BuiltInCategory.OST_Dimensions,
                 DB.BuiltInCategory.OST_Constraints,
                 DB.BuiltInCategory.OST_DisplacementPath,
                 DB.BuiltInCategory.OST_DoorTags,
                 DB.BuiltInCategory.OST_DuctAccessoryTags,
                 DB.BuiltInCategory.OST_DuctFittingTags,
                 DB.BuiltInCategory.OST_DuctInsulationsTags,
                 DB.BuiltInCategory.OST_DuctLiningsTags,
                 DB.BuiltInCategory.OST_PlaceHolderDucts,
                 DB.BuiltInCategory.OST_DuctTags,
                 DB.BuiltInCategory.OST_ElectricalEquipmentTags,
                 DB.BuiltInCategory.OST_ElectricalFixtureTags,
                 DB.BuiltInCategory.OST_FilledRegion,
                 DB.BuiltInCategory.OST_FireAlarmDeviceTags,
                 DB.BuiltInCategory.OST_FlexDuctTags,
                 DB.BuiltInCategory.OST_FlexPipeTags,
                 DB.BuiltInCategory.OST_FloorTags,
                 DB.BuiltInCategory.OST_FurnitureSystemTags,
                 DB.BuiltInCategory.OST_FurnitureTags,
                 DB.BuiltInCategory.OST_GenericAnnotation,
                 DB.BuiltInCategory.OST_GenericModelTags,
                 DB.BuiltInCategory.OST_StructConnectionHoleTags,
                 DB.BuiltInCategory.OST_InternalAreaLoadTags,
                 DB.BuiltInCategory.OST_InternalLineLoadTags,
                 DB.BuiltInCategory.OST_InternalPointLoadTags,
                 DB.BuiltInCategory.OST_KeynoteTags,
                 DB.BuiltInCategory.OST_LightingDeviceTags,
                 DB.BuiltInCategory.OST_LightingFixtureTags,
                 DB.BuiltInCategory.OST_LineLoadTags,
                 DB.BuiltInCategory.OST_Lines,
                 DB.BuiltInCategory.OST_InsulationLines,
                 DB.BuiltInCategory.OST_MassAreaFaceTags,
                 DB.BuiltInCategory.OST_MassTags,
                 DB.BuiltInCategory.OST_Matchline,
                 DB.BuiltInCategory.OST_MaterialTags,
                 DB.BuiltInCategory.OST_MechanicalEquipmentSetTags,
                 DB.BuiltInCategory.OST_MechanicalEquipmentTags,
                 DB.BuiltInCategory.OST_FabricationContainmentTags,
                 DB.BuiltInCategory.OST_FabricationDuctworkTags,
                 DB.BuiltInCategory.OST_FabricationHangerTags,
                 DB.BuiltInCategory.OST_FabricationPipeworkTags,
                 DB.BuiltInCategory.OST_MultiCategoryTags,
                 DB.BuiltInCategory.OST_NurseCallDeviceTags,
                 DB.BuiltInCategory.OST_ParkingTags,
                 DB.BuiltInCategory.OST_PartTags,
                 DB.BuiltInCategory.OST_PipeAccessoryTags,
                 DB.BuiltInCategory.OST_PipeFittingTags,
                 DB.BuiltInCategory.OST_PipeInsulationsTags,
                 DB.BuiltInCategory.OST_PipeTags,
                 DB.BuiltInCategory.OST_PlantingTags,
                 DB.BuiltInCategory.OST_StructConnectionPlateTags,
                 DB.BuiltInCategory.OST_PlumbingFixtureTags,
                 DB.BuiltInCategory.OST_PointLoadTags,
                 DB.BuiltInCategory.OST_StructConnectionProfilesTags,
                 DB.BuiltInCategory.OST_SitePropertyLineSegmentTags,
                 DB.BuiltInCategory.OST_SitePropertyTags,
                 DB.BuiltInCategory.OST_StairsRailingTags,
                 DB.BuiltInCategory.OST_RampsDownArrow,
                 DB.BuiltInCategory.OST_RampsDownText,
                 DB.BuiltInCategory.OST_ReferenceLines,
                 DB.BuiltInCategory.OST_ReferencePoints,
                 DB.BuiltInCategory.OST_RevisionCloudTags,
                 DB.BuiltInCategory.OST_RevisionClouds,
                 DB.BuiltInCategory.OST_RoofTags,
                 DB.BuiltInCategory.OST_RoomTags,
                 DB.BuiltInCategory.OST_BrokenSectionLine,
                 DB.BuiltInCategory.OST_SecurityDeviceTags,
                 DB.BuiltInCategory.OST_StructConnectionShearStudTags,
                 DB.BuiltInCategory.OST_SiteTags,
                 DB.BuiltInCategory.OST_MEPSpaceTags,
                 DB.BuiltInCategory.OST_SpecialityEquipmentTags,
                 DB.BuiltInCategory.OST_SpotCoordinates,
                 DB.BuiltInCategory.OST_SpotElevSymbols,
                 DB.BuiltInCategory.OST_SpotElevations,
                 DB.BuiltInCategory.OST_SpotSlopes,
                 DB.BuiltInCategory.OST_SprinklerTags,
                 DB.BuiltInCategory.OST_StairsLandingTags,
                 DB.BuiltInCategory.OST_StairsDownArrows,
                 DB.BuiltInCategory.OST_StairsDownText,
                 DB.BuiltInCategory.OST_StairsUpArrows,
                 DB.BuiltInCategory.OST_StairsUpText,
                 DB.BuiltInCategory.OST_StairsRunTags,
                 DB.BuiltInCategory.OST_StairsSupportTags,
                 DB.BuiltInCategory.OST_StairsTags,
                 DB.BuiltInCategory.OST_StairsTriserNumbers,
                 DB.BuiltInCategory.OST_StructuralAnnotations,
                 DB.BuiltInCategory.OST_AreaReinTags,
                 DB.BuiltInCategory.OST_BraceEndSegment,
                 DB.BuiltInCategory.OST_StructuralColumnTags,
                 DB.BuiltInCategory.OST_StructConnectionTags,
                 DB.BuiltInCategory.OST_StructConnectionHiddenLines,
                 DB.BuiltInCategory.OST_StructConnectionSymbol,
                 DB.BuiltInCategory.OST_FabricReinforcementTags,
                 DB.BuiltInCategory.OST_StructuralFoundationTags,
                 DB.BuiltInCategory.OST_StructuralFramingTags,
                 DB.BuiltInCategory.OST_PathReinTags,
                 DB.BuiltInCategory.OST_CouplerTags,
                 DB.BuiltInCategory.OST_RebarTags,
                 DB.BuiltInCategory.OST_StructuralStiffenerTags,
                 DB.BuiltInCategory.OST_TrussTags,
                 DB.BuiltInCategory.OST_TelephoneDeviceTags,
                 DB.BuiltInCategory.OST_TextNotes,
                 DB.BuiltInCategory.OST_WallTags,
                 DB.BuiltInCategory.OST_StructConnectionWeldTags,
                 DB.BuiltInCategory.OST_WindowTags,
                 DB.BuiltInCategory.OST_WireTags,
                 DB.BuiltInCategory.OST_WireTickMarks,
                 DB.BuiltInCategory.OST_ZoneTags]

cat_list = List[DB.BuiltInCategory](anno_cat_list)
# gather all elements belonging to annotation categories
multi_cat_filter = DB.ElementMulticategoryFilter(cat_list)
all_anno_els = DB.FilteredElementCollector(revit.doc).WherePasses(
    multi_cat_filter).WhereElementIsNotElementType().ToElements()


el_count = 0
anno_categories = []
anno_dict = {}
anno_total = 0

# iterate through gathered elements, sort and count them by category
for el in all_anno_els:
    el_cat = el.get_Parameter(DB.BuiltInParameter.ELEM_CATEGORY_PARAM).AsValueString()
    if el_cat in anno_dict:
        count = anno_dict.get(el_cat)
        count += 1
        anno_total += 1
        anno_dict.update({el_cat: count})

    else:
        anno_dict[el_cat] = 1
        anno_total += 1

# print result
for key, value in anno_dict.items():
    print("\t{}: {}".format(key, value) )

print("\n \nTotal annotation elements:{} ".format(anno_total))