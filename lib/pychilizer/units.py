from pyrevit import revit, DB, script, forms, HOST_APP, coreutils


def convert_length_to_internal(value, doc=revit.doc):
    # convert length units from display units to internal
    display_units = get_length_units(doc)
    converted = DB.UnitUtils.ConvertToInternalUnits(value, display_units)
    return converted


def convert_length_to_display(value, doc=revit.doc):
    # convert lenght units to display from internal
    display_units = get_length_units(doc)
    converted = DB.UnitUtils.ConvertFromInternalUnits(value, display_units)
    return converted


def get_length_units(doc):
    # fetch Revit's internal units depending on the Revit version
    units = doc.GetUnits()
    if HOST_APP.is_newer_than(2021):
        int_length_units = units.GetFormatOptions(DB.SpecTypeId.Length).GetUnitTypeId()
    else:
        int_length_units = units.GetFormatOptions(DB.UnitType.UT_Length).DisplayUnits
    return int_length_units


def degree_conv(x):
    import math
    return (x * 180) / math.pi


def is_metric(doc):
    # check if doc is metric
    if doc.DisplayUnitSystem == DB.DisplayUnit.METRIC:
        # print ("IS METRIC")
        return True
    else:
        # print ("IMPERIAL")
        return False


def correct_input_units(val, doc):
    import re
    try:
        digits = float(val)
    except ValueError:
        # format the string using regex
        digits = re.findall("[0-9.]+", val)[0]
    # get internal units for
    # display_units = get_length_units(doc)
    res = convert_length_to_internal(float(digits), doc)
    # print ("convert from display units: {} \n from float {}\n result {}".format(display_units, digits, res))

    return res


def round_metric_or_imperial(value, doc):
    # if metric, will round to closest to 10mm
    # if imperial, will round to 2 decimals
    if is_metric(doc):
        return round(value, -2)
    else:
        return round(value, 2)


def convert_length_to_display_string(value, doc=revit.doc):
    # convert length units from internal to display
    format_options = DB.FormatValueOptions()
    spec_type_id = DB.SpecTypeId.Length
    format_options.AppendUnitSymbol = True
    display_string = DB.UnitFormatUtils.Format(doc.GetUnits(), spec_type_id, value, False, format_options)
    return display_string


def convert_display_string_to_internal(value_string, doc=revit.doc):
    # convert from display value (string) to internal. can convert fractional values like "0' - 3 5/8"
    spec_type_id = DB.SpecTypeId.Length
    options = DB.ValueParsingOptions()

    parse = DB.UnitFormatUtils.TryParse(doc.GetUnits(), spec_type_id, value_string, options)
    value_in_internal_units = parse[1]
    return value_in_internal_units
