class UI:
    def __init__(self, script):
        self.script = script
        self.config = script.get_config()
        self.is_metric = True
        self.titleblock_dict = {}
        self.viewplan_dict = {}
        self.viewsection_dict = {}
        self.titleblock = None
        self.tblock_orientation = ['Vertical', 'Horizontal']
        self.layout_orientation = ['Tiles', 'Cross']
        self.sheet_number = self.config.get_option('sheet_number', '1000')
        self.crop_offset = self.config.get_option('crop_offset', '350'  if self.is_metric else '9.0') 
        self.titleblock_offset = self.config.get_option('titleblock_offset', '165'  if self.is_metric else '4.2') 
        self.titleblock_orientation = self.config.get_option('titleblock_orientation', self.tblock_orientation[0]) 
        self.layout_ori = self.config.get_option('layout_ori', self.layout_orientation[0]) 
        self.rotated_elevations = self.config.get_option('rotated_elevations', False)

    def set_titleblocks(self):        
        self.titleblock = self.config.get_option('titleblock', list(self.titleblock_dict.keys())[0])

    def set_viewtemplates(self):
        self.viewplan = self.config.get_option('viewplan', "<None>")
        self.viewceiling = self.config.get_option('viewceiling', "<None>")
        self.viewsection = self.config.get_option('viewsection', "<None>")

    def set_config(self, var, val):
        if var == "sheet_number":
            self.config.sheet_number = val
        if var == "crop_offset":
            self.config.crop_offset = val
        if var == "titleblock_offset":
            self.config.titleblock_offset = val
        if var == "titleblock_orientation":
            self.config.titleblock_orientation = val
        if var == "layout_orientation":
            self.config.layout_ori = val
        if var == "rotated_elevations":
            self.config.rotated_elevations = val
        if var == "titleblock":
            self.config.titleblock = val
        if var == "viewplan":
            self.config.viewplan = val
        if var == "viewceiling":
            self.config.viewceiling = val
        if var == "viewsection":
            self.config.viewsection = val
            

        self.script.save_config()