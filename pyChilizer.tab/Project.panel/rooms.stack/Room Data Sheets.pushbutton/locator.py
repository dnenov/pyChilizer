from pyrevit import DB
from itertools import izip

class Locator:
    def __init__(self, sheet, offset, col, row, layout):
        self.pos = self.get_sheet_pos(sheet, offset, col, row)

    '''get positions based on the layout
    pass num columns and rows'''
    def get_sheet_pos(self, sheet, offset, col, row):
        x_min = sheet.Outline.Min.U
        y_min = sheet.Outline.Min.V
        x_max = sheet.Outline.Max.U
        y_max = sheet.Outline.Max.V
        width = x_max - x_min - offset  # offset should be added to 'y' when horizontal titleblock
        height = y_max - y_min
        col_width = width / float(col)
        row_height = height / float(row)

        # adjust for the relative 0,0,0 of the sheet (for some weird reason the sheet is not placed in the 0,0,0)
        delta = DB.XYZ(x_min, y_min, 0) 

        positions = []
        to_feet = 304.8 # for debug only
        print("width: {0} and height: {1} and the offset in internal units was {2}".format(str(width*to_feet), str(height*to_feet), str(to_feet*offset)))
        print("and the initial point of the sheet is {0},{1}".format(str(to_feet*x_min), str(to_feet*y_min)))

        for i in range(int(col)):
            for j in range(int(row)):
                positions.append(DB.XYZ((col_width * 0.5) + i * col_width, (row_height * 0.5) + j * row_height, 0) + delta)

        return positions

    '''due to some unknown mystic forces, 
    the location of the view creation is not correct
    the label is most probably the cause of this problem
    but we could not reverse engineer the algorithm used by the Gods of Revit'''
    def realign_pos(self, doc, views, positions):
        for view, pos in izip(views, positions):
            actual = view.GetBoxCenter()
            delta = pos - actual # substract the desired position from the actual position
            DB.ElementTransformUtils.MoveElement(doc, view.Id, delta)