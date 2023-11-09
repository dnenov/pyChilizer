from pyrevit import revit, DB, script, forms, HOST_APP, coreutils
import math
from pyrevit.framework import List
from pychilizer import database
from Autodesk.Revit import Exceptions

output = script.get_output()

def inverted_transform(element, view=revit.active_view):
    # get element location and return its inverted transform
    # can be used to translate geometry to 0,0,0 origin to recreate geometry inside a family
    el_location = element.Location.Point
    bb = element.get_BoundingBox(view)
    orig_cs = bb.Transform
    # Creates a transform that represents a translation via the specified vector.
    translated_cs = orig_cs.CreateTranslation(el_location)
    # Transform from the room location point to origin
    return translated_cs.Inverse


def room_bound_to_origin(room, translation):
    room_boundaries = DB.CurveArrArray()
    # get room boundary segments
    room_segments = room.GetBoundarySegments(DB.SpatialElementBoundaryOptions())
    # iterate through loops of segments and add them to the array
    for seg_loop in room_segments:
        curve_array = DB.CurveArray()
        for s in seg_loop:
            old_curve = s.GetCurve()
            new_curve = old_curve.CreateTransformed(translation)  # move curves to origin
            curve_array.Append(new_curve)
        room_boundaries.Append(curve_array)
    return room_boundaries


def get_ref_lvl_plane(family_doc):
    # from given family doc, return Ref. Level reference plane
    find_planes = DB.FilteredElementCollector(family_doc).OfClass(DB.SketchPlane)
    ref_level = DB.FilteredElementCollector(family_doc).OfClass(DB.Level).WhereElementIsNotElementType().FirstElement()
    return [plane for plane in find_planes if plane.Name == ref_level.Name]


def find_crop_box(view):
    with DB.TransactionGroup(revit.doc, "Temp to find crop") as tg:
        tg.Start()
        with DB.Transaction(revit.doc, "temp") as t2:
            t2.Start()
            view.CropBoxVisible = False
            t2.Commit()
            hidden = DB.FilteredElementCollector(revit.doc, view.Id).ToElementIds()
            t2.Start()
            view.CropBoxVisible = True
            t2.Commit()
            crop_box_el = DB.FilteredElementCollector(revit.doc, view.Id).Excluding(hidden).FirstElement()
            tg.RollBack()
            if crop_box_el:
                return crop_box_el
            else:
                print("CROP NOT FOUND")
                return None

'''Create a new cropbox for a 3D view based on a Section Box
Won't run if no Section Box is active'''
def crop_axo(view3d):
    if view3d.IsSectionBoxActive == False: return

    if view3d.CropBoxActive == False:
        view3d.CropBoxActive = True
    
    crop_box = view3d.CropBox   # get the crop box of the view (bounding box)
    section_box = view3d.GetSectionBox()    # get the section box (bounding box)
    trans = crop_box.Transform  # get the view crop box Transform, will be used to convert from World Coordinates to View Coordinates
    corners = bb_corners(section_box, trans)    # get the actual corners of the section box in View Coordinates

    minX = min(corners, key=lambda x: x.X).X    
    minY = min(corners, key=lambda x: x.Y).Y
    minZ = min(corners, key=lambda x: x.Z).Z
    maxX = max(corners, key=lambda x: x.X).X
    maxY = max(corners, key=lambda x: x.Y).Y
    maxZ = max(corners, key=lambda x: x.Z).Z

    # offset by 1/10 of the crop box outword
    d = 0.05 * (maxX - minX)
    minX = minX - d
    maxX = maxX + d

    d = 0.05 * (maxY - minY)
    minY = minY - d
    maxY = maxY + d

    # finally, create and assign the new crop box
    crop_box.Min = DB.XYZ(minX, minY, minZ)
    crop_box.Max = DB.XYZ(maxX, maxY, maxZ)

    view3d.CropBox = crop_box

'''A helper method to calculate the actual Section Box corners from World to View Coordinates'''
def bb_corners(box, transform):
    b_ll = box.Min    #lower left
    b_lr = DB.XYZ(box.Max.X, box.Min.Y, box.Min.Z) # lower right
    b_ul = DB.XYZ(box.Min.X, box.Max.Y, box.Min.Z) # upper left
    b_ur = DB.XYZ(box.Max.X, box.Max.Y, box.Min.Z) # upper right
    t_ur = box.Max # upper right
    t_ul = DB.XYZ(box.Min.X, box.Max.Y, box.Max.Z) # upper left
    t_lr = DB.XYZ(box.Max.X, box.Min.Y, box.Max.Z) # lower right
    t_ll = DB.XYZ(box.Min.X, box.Min.Y, box.Max.Z) # lower left
    out = [b_ll, b_lr, b_ul, b_ur, t_ur, t_ul, t_lr, t_ll]
    for index, o in enumerate(out):
        out[index] = box.Transform.OfPoint(out[index])
        out[index] = transform.Inverse.OfPoint(out[index])
    return out
    

def point_equal_list(pt, lst):
    for el in list(lst):
        if pt.IsAlmostEqualTo(el, 0.003):
            return el
    else:
        return None


def get_open_ends(curves_list):
    #check if any open ends in a curves list
    endpoints = []
    for curve in curves_list:
        for i in range(2):
            duplicate = point_equal_list(curve.GetEndPoint(i), endpoints)
            if duplicate:
                endpoints.remove(duplicate)
            else:
                endpoints.append(curve.GetEndPoint(i))
    if endpoints:
        return endpoints
    else:
        return None



def get_room_bound(r):
    room_boundaries = DB.CurveLoop()
    # get room boundary segments
    room_segments = r.GetBoundarySegments(DB.SpatialElementBoundaryOptions())
    # iterate through loops of segments and add them to the array
    outer_loop = room_segments[0]
    # for curve in outer_loop:
    curve_loop = [s.GetCurve() for s in outer_loop]
    open_ends = get_open_ends(curve_loop)
    if open_ends:
        return None
    for curve in curve_loop:
        try:
            room_boundaries.Append(curve)
        except Exceptions.ArgumentException:
            print("Boundary curve makes the loop not contiguous in room {}.".format(output.linkify(r.Id)))
    return room_boundaries


def get_longest_boundary(r):
    # get the rooms's longest boundary that is not an arc
    bound = r.GetBoundarySegments(DB.SpatialElementBoundaryOptions())
    longest = None
    for loop in bound:
        for b in loop:
            curve = b.GetCurve()
            if curve.Length > longest and isinstance(curve, DB.Line):
                longest = curve
    return longest


def line_as_vector(line):
    start = line.GetEndPoint(0)
    end = line.GetEndPoint(1)
    vector = end - start
    return vector


def rotation_angle(line, base):
    # calculate the rotation of the line from a given reference

    vector = line_as_vector(line)
    up = DB.XYZ(base.X, base.Y+1, base.Z)
    y_direction = up-base

    angle = vector.AngleTo(y_direction)
    return angle


def room_rotation_angle(room):
    # get the angle of the room's longest boundary to Y axis
    # choose one longest curve to use as reference for rotation

    longest_boundary = get_longest_boundary(room)
    v = line_as_vector(longest_boundary)

    y1 = room.Location.Point
    y2 = DB.XYZ(y1.X, y1.Y+1, y1.Z)
    y_dir = y2-y1

    # get angle and correct value
    angle = v.AngleTo(y_dir)
    # print ("initial angle: {}\n".format(math.degrees(angle)))

    rotation = DB.Transform.CreateRotation(DB.XYZ.BasisZ, -angle)
    rotated_vector = rotation.OfVector(v)
    must_be_zero = math.degrees(rotated_vector.AngleTo(y_dir))
    # print ("angle between rotated and Y vector : {}\n".format(math.degrees(must_be_zero)))
    if round(must_be_zero, 0) != math.radians(0):
        angle = -angle
        rotation2 = DB.Transform.CreateRotation(DB.XYZ.BasisZ, -angle)
        rotated_vector2 = rotation2.OfVector(v)
        must_be_zero2 = math.degrees(rotated_vector2.AngleTo(y_dir))
        # print("corrected angle {}, second check{}".format(math.degrees(angle), math.degrees(must_be_zero2)))
        if round(must_be_zero2,0) != math.radians(0):
            angle = math.radians(90)-angle


    while abs(angle) > math.radians(90):
        if angle > math.radians(0):
            angle = angle - math.radians(90)
        elif angle < math.radians(0):
            angle = angle + math.radians(90)
    # print ("final angle", angle)
    return angle


def get_bb_outline(bb):

    r1 = DB.XYZ(bb.Min.X, bb.Min.Y, bb.Min.Z)
    r2 = DB.XYZ(bb.Max.X, bb.Min.Y, bb.Min.Z)
    r3 = DB.XYZ(bb.Max.X, bb.Max.Y, bb.Min.Z)
    r4 = DB.XYZ(bb.Min.X, bb.Max.Y, bb.Min.Z)

    l1 = DB.Line.CreateBound(r1, r2)
    l2 = DB.Line.CreateBound(r2, r3)
    l3 = DB.Line.CreateBound(r3, r4)
    l4 = DB.Line.CreateBound(r4, r1)

    curves_set = [l1, l2, l3, l4]
    return curves_set


def set_crop_to_bb(element, view, crop_offset, doc=revit.doc):
    try:
        # set the crop box of the view to elements's bounding box in that view
        # draw 2 sets of outlines for each orientation (front/back, left/right)
        # deactivate crop first, just to make sure the element appears in view
        view.CropBoxActive = False
        doc.Regenerate()

        bb = element.get_BoundingBox(view)

        pt1 = DB.XYZ(bb.Max.X, bb.Max.Y, bb.Min.Z)
        pt2 = DB.XYZ(bb.Max.X, bb.Max.Y, bb.Max.Z)
        pt3 = DB.XYZ(bb.Min.X, bb.Min.Y, bb.Max.Z)
        pt4 = DB.XYZ(bb.Min.X, bb.Min.Y, bb.Min.Z)

        pt7 = DB.XYZ(bb.Min.X, bb.Max.Y, bb.Min.Z)
        pt8 = DB.XYZ(bb.Min.X, bb.Max.Y, bb.Max.Z)
        pt5 = DB.XYZ(bb.Max.X, bb.Min.Y, bb.Max.Z)
        pt6 = DB.XYZ(bb.Max.X, bb.Min.Y, bb.Min.Z)

        l1 = DB.Line.CreateBound(pt1, pt2)
        l2 = DB.Line.CreateBound(pt2, pt3)
        l3 = DB.Line.CreateBound(pt3, pt4)
        l4 = DB.Line.CreateBound(pt4, pt1)

        l5 = DB.Line.CreateBound(pt6, pt5)
        l6 = DB.Line.CreateBound(pt5, pt8)
        l7 = DB.Line.CreateBound(pt8, pt7)
        l8 = DB.Line.CreateBound(pt7, pt6)

        curves_set1 = [l1, l2, l3, l4]
        curves_set2 = [l5, l6, l7, l8]

        crsm = view.GetCropRegionShapeManager()
        view_direction = view.ViewDirection

        view.CropBoxActive = True
        # offset will fail if crop offset value too small
        try:
            # try with set 1, if doesn't work try with set 2
            crop_loop = DB.CurveLoop.Create(List[DB.Curve](curves_set1))
            # offset the crop with the specified offset
            curve_loop_offset = DB.CurveLoop.CreateViaOffset(crop_loop, crop_offset, view_direction)
            # in case the offset works inwards, correct it to offset outwards
            if curve_loop_offset.GetExactLength() < crop_loop.GetExactLength():
                curve_loop_offset = DB.CurveLoop.CreateViaOffset(crop_loop, crop_offset, -view_direction)
            crsm.SetCropShape(curve_loop_offset)
        except:
            crop_loop = DB.CurveLoop.Create(List[DB.Curve](curves_set2))
            try:
                curve_loop_offset = DB.CurveLoop.CreateViaOffset(crop_loop, crop_offset, view_direction) # fails here
            except Exceptions.InternalException:
                forms.alert("Room crop failed. This might be happening if the room placement point is not in the room -- or -- if the Crop Offset is set to a value too large. Review and try again")
                return False
            if curve_loop_offset.GetExactLength() < crop_loop.GetExactLength():
                curve_loop_offset = DB.CurveLoop.CreateViaOffset(crop_loop, crop_offset, -view_direction)
            crsm.SetCropShape(curve_loop_offset)

        return True
    except Exception as e:
        forms.alert(f"An exception occurred: {e}")


def set_crop_to_boundary(room, boundary_curve, view, crop_offset, doc=revit.doc):
    # set the crop box of the view to match the boundary in width and room's bounding box in that view in height
    # deactivate crop first, just to make sure the element appears in view
    view.CropBoxActive = False
    doc.Regenerate()

    b_start = boundary_curve.GetEndPoint(0)
    b_end = boundary_curve.GetEndPoint(1)

    bb = room.get_BoundingBox(view)

    pt1 = DB.XYZ(b_start.X, b_start.Y, bb.Min.Z)
    pt2 = DB.XYZ(b_start.X, b_start.Y, bb.Max.Z)
    pt3 = DB.XYZ(b_end.X, b_end.Y, bb.Max.Z)
    pt4 = DB.XYZ(b_end.X, b_end.Y, bb.Min.Z)

    l1 = DB.Line.CreateBound(pt1, pt2)
    l2 = DB.Line.CreateBound(pt2, pt3)
    l3 = DB.Line.CreateBound(pt3, pt4)
    l4 = DB.Line.CreateBound(pt4, pt1)

    curves_set = [l1, l2, l3, l4]

    crsm = view.GetCropRegionShapeManager()
    view_direction = view.ViewDirection

    view.CropBoxActive = True
    # offset will fail if crop offset value too small

    crop_loop = DB.CurveLoop.Create(List[DB.Curve](curves_set))
    # offset the crop with the specified offset
    try:
        curve_loop_offset = DB.CurveLoop.CreateViaOffset(crop_loop, crop_offset, view_direction)
    except Exception:
        curve_loop_offset = DB.CurveLoop.CreateViaOffset(crop_loop, crop_offset, -view_direction)
    # in case the offset works inwards, correct it to offset outwards
    if curve_loop_offset.GetExactLength() < crop_loop.GetExactLength():
        curve_loop_offset = DB.CurveLoop.CreateViaOffset(crop_loop, crop_offset, -view_direction)
    crsm.SetCropShape(curve_loop_offset)

    return


def get_bb_axis_in_view(element, view):
    # return the central axis of element's bounding box in view
    # get viewplan bbox, center
    bbox = element.get_BoundingBox(view)
    center = 0.5 * (bbox.Max + bbox.Min)
    axis = DB.Line.CreateBound(center, center + DB.XYZ.BasisZ)
    return axis


def get_aligned_crop(geo, transform):

    rotated_geo = geo.GetTransformed(transform)
    revit.doc.Regenerate()
    rb = rotated_geo.GetBoundingBox()
    bb_outline = get_bb_outline(rb)
    # rotate the curves back using the opposite direction
    tr_back = transform.Inverse
    rotate_curves_back = [c.CreateTransformed(tr_back) for c in bb_outline]
    crop_loop = DB.CurveLoop.Create(List[DB.Curve](rotate_curves_back))

    return crop_loop


def get_unique_borders(borders, tolerance):
    # sort the borders discarding overlapping ones (lying on same axis)
    axis_set = []
    sorted_lines = []
    for curve in borders:
        deriv = curve.ComputeDerivatives(0.5, True)
        tangent = deriv.BasisX
        pt = curve.Evaluate(0.5, True)
        axis = DB.Line.CreateUnbound(pt, tangent)
        on_axis = False
        if not axis_set:
            axis_set.append(axis)
            sorted_lines.append(curve)
        for line in axis_set:
            distance = line.Distance(pt)
            # print (distance)
            if distance <= tolerance:
                on_axis = True
        if not on_axis:
            axis_set.append(axis)
            sorted_lines.append(curve)
    return sorted_lines


def discard_short(curves, threshold):
    return [curve for curve in curves if curve.Length > threshold]


def room_to_freeform(r, family_doc):
    room_geo = r.ClosedShell
    for geo in room_geo:
        if isinstance(geo, DB.Solid) and geo.Volume > 0.0:
            freeform = DB.FreeFormElement.Create(family_doc, geo)
            family_doc.Regenerate()
            delta = DB.XYZ(0, 0, 0) - freeform.get_BoundingBox(None).Min
            move_ff = DB.ElementTransformUtils.MoveElement(
                family_doc, freeform.Id, delta
            )
            # create and associate a material parameter
            ext_mat_param = freeform.get_Parameter(DB.BuiltInParameter.MATERIAL_ID_PARAM)
            is_instance_parameter = True  # if the material is instance or type parameter
            new_mat_param = database.add_material_parameter(family_doc, "Material", is_instance_parameter)
            family_doc.FamilyManager.AssociateElementParameterToFamilyParameter(ext_mat_param,
                                                                                new_mat_param)
    return freeform


def room_to_extrusion(r, family_doc):
    output = script.get_output()
    room_height = r.get_Parameter(DB.BuiltInParameter.ROOM_HEIGHT).AsDouble()
    # helper: define inverted transform to translate room geometry to origin
    geo_translation = inverted_transform(r)
    # collect room boundaries and translate them to origin
    room_boundaries = room_bound_to_origin(r, geo_translation)
    # skip if the boundaries are not a closed loop (can happen with misaligned boundaries)
    if not room_boundaries:
        print("Extrusion failed for room {}. Try fixing room boundaries".format(output.linkify(r.Id)))
        return

    ref_plane = get_ref_lvl_plane(family_doc)
    # create extrusion, assign material, associate with shared parameter
    try:
        extrusion = family_doc.FamilyCreate.NewExtrusion(True, room_boundaries, ref_plane[0],
                                                         room_height)
        ext_mat_param = extrusion.get_Parameter(DB.BuiltInParameter.MATERIAL_ID_PARAM)
        # create and associate a material parameter
        new_mat_param = family_doc.FamilyManager.AddParameter("Material",
                                                              DB.BuiltInParameterGroup.PG_MATERIALS,
                                                              DB.ParameterType.Material,
                                                              False)
        family_doc.FamilyManager.AssociateElementParameterToFamilyParameter(ext_mat_param,
                                                                            new_mat_param)
        return extrusion
    except Exceptions.InternalException:
        print("Extrusion failed for room {}. Try fixing room boundaries".format(output.linkify(r.Id)))
        return


def create_room_axo_rotate(room, angle=None, view_scale=50, doc=revit.doc):
    if angle == None:
        angle = room_rotation_angle(room)

    # create 3D axo for a room, rotate the Section Box to fit
    threeD_type = database.get_view_family_types(DB.ViewFamily.ThreeDimensional, doc)[0]

    threeD = DB.View3D.CreateIsometric(doc, threeD_type.Id)
    threeD.Scale = view_scale

    # 1. rotate room geometry
    room_shell = room.ClosedShell
    rotation = DB.Transform.CreateRotationAtPoint(DB.XYZ.BasisZ, -angle, room.Location.Point)
    rotated_shell = room_shell.GetTransformed(rotation)

    # 2. get the bbox of the rotated shell
    shell_bb = rotated_shell.GetBoundingBox()
    rotate_back = rotation.Inverse

    # rotate the bbox back
    new_bb = DB.BoundingBoxXYZ()
    new_bb.Transform = rotate_back
    new_bb.Min = shell_bb.Min
    new_bb.Max = shell_bb.Max

    # set bbox as section box
    sb = threeD.SetSectionBox(new_bb)

    # set orientation
    eye = DB.XYZ(0, 0, 0)
    up = DB.XYZ(-1, 1, 2)
    fwd = DB.XYZ(-1, 1, -1)

    view_orientation = DB.ViewOrientation3D(eye, up, fwd)
    threeD.SetOrientation(view_orientation)
    threeD.CropBoxActive = True
    doc.Regenerate()
    crop_axo(threeD)

    return threeD


def room_bb_outlines(room, angle=None):
    if angle==None:
        angle=room_rotation_angle(room)
    # get the outlines of a room's bounding box, rotated
    rotation = DB.Transform.CreateRotationAtPoint(DB.XYZ.BasisZ, angle, room.Location.Point)
    rotated_crop_loop = get_aligned_crop(room.ClosedShell, rotation.Inverse)
    return rotated_crop_loop


def orient_elevation_to_line(doc, elevation_marker, marker_center, line, elevation_id, view):
    # rotate the elevation marker to face a line, with given marker center
    # get the elevation with the elevation id
    elevation_view = doc.GetElement(elevation_marker.GetViewId(elevation_id))
    # get the view direction of the elevation view (facing the viewer)
    view_direction = elevation_view.ViewDirection
    # note: the origin of the elevation view is NOT the center of the marker
    bb = elevation_marker.get_BoundingBox(view)
    center = (bb.Max + bb.Min) / 2

    # project the origin onto the line and get closest point
    project = line.Project(center)
    project_point = project.XYZPoint
    # construct a line from from the projected point to origin and get its vector
    projection_direction = DB.Line.CreateBound(project_point, center).Direction
    vectors_angle = view_direction.AngleOnPlaneTo(projection_direction, DB.XYZ.BasisZ)
    # calculate the rotation angle
    rotation_angle = vectors_angle - math.radians(360)
    marker_axis = DB.Line.CreateBound(marker_center, marker_center + DB.XYZ.BasisZ)
    elevation_marker.Location.Rotate(marker_axis, rotation_angle)
    return elevation_marker


def offset_curve_inwards_into_room(curve, room, offset_distance):
    # offset inwards and check if it's the right side (check if inside room)
    offset_curve = curve.CreateOffset(offset_distance, DB.XYZ(0, 0, 1))
    curve_midpoint = offset_curve.Evaluate(0.5, True)
    if not room.IsPointInRoom(curve_midpoint):
        offset_curve = curve.CreateOffset(-offset_distance, DB.XYZ(0, 0, 1))
    return offset_curve