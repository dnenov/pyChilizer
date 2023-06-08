from collections import defaultdict
from pyrevit import HOST_APP
from pyrevit import forms
from pyrevit import revit, DB
from pyrevit import script
import random
from pychilizer import database
import colorsys


# colour gradients solution by https://bsouthga.dev/posts/color-gradients-with-python


def basic_colours():
    # colour presets - short colours list (14 colours)
    basic_colours = [
        "#40DFFF",
        "#803ABA",
        "#E6B637",
        "#A8DA84"
        "#8337E6",
        "#EBE70E",
        "#D037E6",
        "#074FE0",  # blue
        "#03A64A",
        "#662400",
        "#FF6B1A",
        "#FF4858",
        "#747F7F",
        "#919151"
    ]

    return basic_colours


def rainbow():
    dark = "#42371E"
    red = "#F10800"
    orange = "#F27405"
    yellow = "#FFF14E"
    green = "#016B31"
    pink = "#F587FF"
    blue = "#6DDEF0"
    violet = "#550580"
    cyan = "#40DFFF"
    rainbow_colours = [dark, red, orange, yellow, green, blue, cyan, violet, pink]
    return rainbow_colours


def hex_to_rgb(hex):
    return [int(hex[i:i + 2], 16) for i in range(1, 6, 2)]


def rgb_to_hex(rgb):
    rgb = [int(x) for x in rgb]
    return "#" + "".join(["0{0:x}".format(v) if v < 16 else "{0:x}".format(v) for v in rgb])


def color_dict(gradient):
    """Takes in a list of RGB sub-lists and returns dictionary of
        colors in RGB and hex form for use in a graphing function
        defined later on """
    return {
        "hex": [rgb_to_hex(rgb) for rgb in gradient],
        "r": [rgb[0] for rgb in gradient],
        "g": [rgb[1] for rgb in gradient],
        "b": [rgb[2] for rgb in gradient],
    }


def linear_gradient(start_hex, finish_hex, n=10):
    """ returns a gradient list of (n) colors between
        two hex colors. start_hex and finish_hex
        should be the full six-digit color string,
        including the number sign ("#FFFFFF") """
    # Starting and ending colors in RGB form
    s = hex_to_rgb(start_hex)
    f = hex_to_rgb(finish_hex)
    # Initilize a list of the output colors with the starting color
    rgb_list = [s]
    # Calcuate a color at each evenly spaced value of t from 1 to n
    for t in range(1, n):
        # Interpolate RGB vector for color at the current value of t
        curr_vector = [int(s[j] + (float(t) / (n - 1)) * (f[j] - s[j])) for j in range(3)]
        # Add it to our list of output colors
        rgb_list.append(curr_vector)
    return color_dict(rgb_list)


def polylinear_gradient(colors, n):
    ''' returns a list of colors forming linear gradients between
          all sequential pairs of colors. "n" specifies the total
          number of desired output colors '''
    # The number of colors per individual linear gradient
    n_out = int(float(n) / (len(colors) - 1)) + 2
    # returns dictionary defined by color_dict()
    gradient_dict = linear_gradient(colors[0], colors[1], n_out)

    if len(colors) > 1:
        for col in range(1, len(colors) - 1):
            next = linear_gradient(colors[col], colors[col + 1], n_out)
            for k in ("hex", "r", "g", "b"):
                # Exclude first point to avoid duplicates
                gradient_dict[k] += next[k][1:]
    return gradient_dict


def revit_colour(hex):
    rgb = hex_to_rgb(hex)
    revit_clr = DB.Color(rgb[0], rgb[1], rgb[2])
    return revit_clr


def random_colour_hsv(n):
    # return random colour based on
    hsv_tuples = [(i * 1.0 / n, 0.85, 0.85) for i in range(n)]

    rgb_out = []
    for rgb in hsv_tuples:
        rgb = map(lambda x: int(x * 255), colorsys.hsv_to_rgb(*rgb))
        revit_colour = DB.Color(rgb[0], rgb[1], rgb[2])
        rgb_out.append(revit_colour)
    return rgb_out


def get_colours(n):
    if n < 14:
        colours = basic_colours()
    else:
        colours = rainbow()
    col_dict = polylinear_gradient(colours, n)
    chop_col_list = col_dict["hex"][0:n]
    # gradient method
    revit_colours = [revit_colour(h) for h in chop_col_list]
    # random method
    # revit_colours = colorize.random_colour_hsv(len(types_dict))

    for x in range(10):
        random.shuffle(revit_colours)
    return revit_colours


override_options = ["Projection Line Colour", "Projection Surface Colour", "Cut Line Colour", "Cut Pattern Colour"]
default_override_options = ["Projection Surface Colour", "Cut Pattern Colour"]
OVERRIDES_CONFIG_OPTION_NAME = "overrides"
CATEGORIES_CONFIG_OPTION_NAME = "colorize_categories"

class ChosenItem(forms.TemplateListItem):
    """Wrapper class for chosen item"""
    @property
    def name(self):
        return str(self.item)


def get_config(config_set, option_name, default_options):
    # get the config values
    prev_choice = config_set.get_option(option_name, [])
    if not prev_choice:
        save_config([x for x in default_options], option_name,config_set)
        prev_choice = config_set.get_option(option_name, [])
    return prev_choice

# categories_config = script.get_config(colorize.CATEGORIES_CONFIG_OPTION_NAME) #get colorize_categories config - to store fav categories

def get_categories_config(doc):
    # get the category language-specific labels from config and return a dictionary {Label:BIC}
    categories_config = script.get_config(CATEGORIES_CONFIG_OPTION_NAME)  # get colorize_categories config
    default_categories_names = database.frequent_category_labels()
    categories_names_list= get_config(categories_config, CATEGORIES_CONFIG_OPTION_NAME, default_categories_names)
    return database.category_labels_to_bic(categories_names_list, doc)



def save_config(chosen, option_name, config):
    """Save given list of overrides"""
    config.set_option(option_name, chosen)
    # script.save_config()


def load_configs(config, option_name,default_option):
    """Load list of frequently selected items from configs or defaults"""
    ovrds = config.get_option(option_name, [])
    ovrd_items = [x for x in (ovrds or default_option)]
    if not ovrds:
        ovrd_items = [x for x in default_option]
    return filter(None, ovrd_items)

def config_overrides(config, option_name):
    """Ask for users choice of overrides"""
    prev_ovrds = load_configs(config, option_name, default_override_options)
    opts = [ChosenItem(x, checked=x in prev_ovrds) for x in override_options]
    overrides = forms.SelectFromList.show(
        sorted(opts),
        title="Choose Overrides Styles",
        button_name="Remember",
        multiselect=True
    )
    if overrides:
        save_config([x for x in overrides if x], option_name,config)


def config_category_overrides(doc):
    """Ask for favourite categories"""
    # categories_config = get_categories_config(doc)
    categories_config = script.get_config(CATEGORIES_CONFIG_OPTION_NAME)
    prev_cat_overrides = load_configs(categories_config, CATEGORIES_CONFIG_OPTION_NAME, database.frequent_category_labels())
    category_options = [ChosenItem(x, checked=x in prev_cat_overrides) for x in database.model_categories_dict(doc)]
    category_selection = forms.SelectFromList.show(
        sorted(category_options, key=lambda x:x.name),
        title="Frequent Categories List",
        button_name="Choose Categories",
        multiselect=True
    )
    if category_selection:
        save_config([x for x in category_selection if x],CATEGORIES_CONFIG_OPTION_NAME, categories_config)


def set_colour_overrides_by_option(overrides_option, colour, doc):
    override = DB.OverrideGraphicSettings()
    solid_fill_pat_id = database.get_solid_fill_pat(doc).Id
    if "Projection Line Colour" in overrides_option:
        override.SetProjectionLineColor(colour)
    if "Cut Line Colour" in overrides_option:
        override.SetCutLineColor(colour)
    if "Projection Surface Colour" in overrides_option:
        override.SetSurfaceForegroundPatternColor(colour)
        override.SetSurfaceForegroundPatternId(solid_fill_pat_id)
    if "Cut Pattern Colour" in overrides_option:
        override.SetCutForegroundPatternColor(colour)
        override.SetCutForegroundPatternId(solid_fill_pat_id)
    return override
