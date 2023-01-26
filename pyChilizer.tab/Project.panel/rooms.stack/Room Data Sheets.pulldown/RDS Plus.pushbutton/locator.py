from pyrevit import DB
from itertools import izip


class Locator:
    plan = DB.XYZ()  # class variable - plan location
    rcp = DB.XYZ()  # class variable - rcp location
    elevations = []  # class variable - elevation location

    '''Constructor'''

    def __init__(self, sheet, offset, tb_orientation, elevation_widths):
        col = 4
        row = 2
        self.pos = self.get_sheet_pos(sheet, offset, col, row, tb_orientation)
        self.set_pos_plans(self.pos)
        self.set_pos_elevs(self.pos, elevation_widths)

    '''Set positions based on the type of layout
    Allows us to introduce future layouts or layout management ui'''

    def set_pos_plans(self, pos):

        self.plan = (pos[0] + pos[2]) / 2
        self.rcp = (pos[4] + pos[6]) / 2

    # TODO: spread elevations
    def set_pos_elevs(self, pos, elevation_widths):
        previous_elevation = (pos[1]+pos[3])/2
        # print ("First {}".format(previous_elevation))
        offset_positions = [previous_elevation]
        # iterate in widths except last
        #todo: this is not great
        for width in elevation_widths[:-1]:
            # print ("Width: {}".format(width))
            previous_elevation = previous_elevation.Add(DB.XYZ(width, 0,0))
            # print ("Next {}".format(previous_elevation))
            offset_positions.append(previous_elevation)
        # print (offset_positions)
        self.elevations = offset_positions

    '''get positions based on the layout
    pass num columns and rows'''

    def get_sheet_pos(self, sheet, offset, col, row, tb_orientation):
        x_min = sheet.Outline.Min.U
        y_min = sheet.Outline.Min.V
        x_max = sheet.Outline.Max.U
        y_max = sheet.Outline.Max.V
        width = x_max - x_min
        height = y_max - y_min
        if str(tb_orientation) == 'Vertical':
            width -= offset
        else:
            height += offset
        col_width = width / float(col)
        row_height = height / float(row)

        # adjust for the relative 0,0,0 of the sheet (for some weird reason the sheet is not placed in the 0,0,0)
        delta = DB.XYZ(x_min, y_min, 0)

        # all points on screen. the middle of column x row
        positions = []

        for i in range(int(col)):
            for j in range(int(row)):
                positions.append(
                    DB.XYZ((col_width * 0.5) + i * col_width, (row_height * 0.5) + j * row_height, 0) + delta)

        return positions

    '''due to some unknown mystic forces, 
    the location of the view creation is not correct
    the label is most probably the cause of this problem
    but we could not reverse engineer the algorithm used by the Gods of Revit'''

    def realign_pos(self, doc, views, positions):
        for view, pos in izip(views, positions):
            actual = view.GetBoxCenter()
            delta = pos - actual  # substract the desired position from the actual position
            DB.ElementTransformUtils.MoveElement(doc, view.Id, delta)
