from collections import defaultdict
from pyrevit import HOST_APP
from pyrevit import forms
from pyrevit import revit, DB
from pyrevit import script
import random
from pychilizer import database
import colorsys

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
    hsv_tuples = [(i * 1.0 / n, 0.75, 0.75) for i in range(n)]

    rgb_out = []
    for rgb in hsv_tuples:
        rgb = map(lambda x: int(x * 255), colorsys.hsv_to_rgb(*rgb))
        revit_colour = DB.Color(rgb[0], rgb[1], rgb[2])
        rgb_out.append(revit_colour)
    return rgb_out