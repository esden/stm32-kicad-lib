#!/usr/bin/env python3
"""Kicad library file generator for the stm32cube database files."""

## This script is generating the old version of the KiCad symbol library format
## It is kept here for documentation purposes, and will likely be deleted in the future

__author__ = 'esdentem'

import xml.etree.ElementTree
import re
import sys
import glob

glyph_widths = {
    ' ': 38, '!': 24, '"': 38, '#': 50, '$': 48, '%': 57, '&': 62, '\'': 24, '(': 33, ')': 33, '*': 38, '+': 62,
    ',': 24, '-': 62, '.': 24, '/': 52, '0': 48, '1': 48, '2': 48, '3': 48, '4': 48, '5': 48, '6': 48, '7': 48,
    '8': 48, '9': 48, ':': 24, ';': 24, '<': 62, '=': 62, '>': 62, '?': 43, '@': 64, 'A': 43, 'B': 50, 'C': 50,
    'D': 50, 'E': 45, 'F': 43, 'G': 50, 'H': 52, 'I': 24, 'J': 38, 'K': 50, 'L': 40, 'M': 57, 'N': 52, 'O': 52,
    'P': 50, 'Q': 52, 'R': 50, 'S': 48, 'T': 38, 'U': 52, 'V': 43, 'W': 57, 'X': 48, 'Y': 43, 'Z': 48, '[': 33,
    '\\': 33, ']': 33, '^': 29, '_': 38, '`': 19, 'a': 45, 'b': 45, 'c': 43, 'd': 45, 'e': 43, 'f': 29, 'g': 45,
    'h': 45, 'i': 24, 'j': 24, 'k': 40, 'l': 26, 'm': 67, 'n': 45, 'o': 45, 'p': 45, 'q': 45, 'r': 31, 's': 40,
    't': 29, 'u': 45, 'v': 38, 'w': 52, 'x': 40, 'y': 38, 'z': 40, '{': 33, '|': 48, '}': 33, '~': 36
}

def pretty_print_banks(banks):
    bank_names = sorted(banks.keys())
    for bank in bank_names:
        print("Bank: %s" % bank)
        print("\tPin\tName\tType\tStruct\tFunc")
        for pin in banks[bank]:
            print("\t%s\t%s\t%s\t%s\t%s" % (pin['Pin'],
                                            pin['Pin_name'],
                                            pin['Pin_type'],
                                            pin['Pin_structure'],
                                            pin['Pin_functions']))


def lib_head(f):
    f.write('EESchema-Library Version 2.3\n\n')
    f.write('#encoding utf-8\n')


def lib_foot(f):
    f.write('#\n')
    f.write('#End Library\n')


def symbol_head(f, names, footprint, parts=1):
    f.write("#\n")
    f.write("# " + names[0] + "\n")
    f.write("#\n")
    f.write("DEF " + names[0] + " U 0 50 Y Y " + str(parts) + " F N\n")
    f.write("F0 \"U\" 0 100 50 H V C CNN\n")
    f.write("F1 \"" + names[0] + "\" 0 -100 50 H V C CNN\n")
    f.write("F2 \"" + footprint + "\" 0 -200 50 H V C CIN\n")
    f.write("F3 \"\" 0 0 50 H V C CNN\n")
    if len(names) > 1:
        f.write("ALIAS")
        for name in names[1:]:
            f.write(" " + name)
        f.write("\n")
    f.write("DRAW\n")


def symbol_frame(f, startx, starty, endx, endy, part=1):
    f.write("S {:g} {:g} {:g} {:g} {:g} 1 10 N\n".format(startx, starty, endx, endy, part))


def symbol_pin(f, name, num, x, y, direction, io_type, part=1):
    pin_type = 'B'
    # Pin types are:
    # Input             I
    # Output            O
    # Bidirectional     B
    # Tristate          T
    # Passive           P
    # Unspecified       U
    # Power In          W
    # Power out         w
    # Open Collector    C
    # Open Emitter      E
    # Not Connected     N
    if io_type:
        if re.match("^I/O$", io_type) or \
           re.match("^MonoIO$", io_type):
            pin_type = 'B'
        elif re.match("^I$", io_type) or \
            re.match("^Boot$", io_type) or \
            re.match("^Reset$", io_type):
            pin_type = 'I'
        elif re.match("^O$", io_type):
            pin_type = 'O'
        elif re.match("^S$", io_type) or \
            re.match("^Power$", io_type):
            pin_type = 'W'
        elif re.match("^NC$", io_type):
            pin_type = 'N'
        elif re.match("^Passive$", io_type):
            pin_type = 'P'
        else:
            print("Pin '%s' does not have a valid type '%s' defaulting to bidirectional 'B'." % (name, io_type))
    else:
        print("Pin '%s' io type is empty, defaulting to bidirectional 'B'." % name)

    f.write("X {} {} {:g} {:g} 300 {} 50 50 {:g} 1 {}\n".format(name, num, x, y, direction, part, pin_type))


def symbol_bank(f, pins, x_offset, y_offset, spacing, direction, part=1):
    counter = 0

    def pin_sort_key(pin_key):
        m = re.match("(\D*)(\d*)", pin_key['Pin_name'])
        return '{}{:0>3}'.format(m.group(1), m.group(2))

    for pin in sorted(pins, key=pin_sort_key):
        name = pin['Pin_name']
        if pin['Pin_functions']:
            name += "/" + '/'.join(pin['Pin_functions'])
        if direction == 'R' or direction == 'L':
            symbol_pin(f, name, pin['Pin'], x_offset, y_offset - (counter * spacing), direction, pin['Pin_type'], part)
        elif direction == 'U' or direction == 'D':
            symbol_pin(f, name, pin['Pin'], x_offset, y_offset - (counter * spacing), direction, pin['Pin_type'], part)
        else:
            print("Unknown direction!!!")
        counter += 1


def symbol_foot(f):
    f.write("ENDDRAW\n")
    f.write("ENDDEF\n")


def symbol_pin_height(banks):
    left_banks = []
    right_banks = []

    side = 'L'
    for bank in sorted(banks.keys()):
        if not (bank == 'VSS' or bank == 'VDD'):
            if side == 'L':
                left_banks.append(bank)
                side = 'R'
            elif side == 'R':
                right_banks.append(bank)
                side = 'L'

    left_height = 17 * (len(left_banks) - 1)
    left_height += len(banks[left_banks[-1]])
    right_height = 17 * (len(right_banks) - 1)
    right_height += len(banks[right_banks[-1]])

    full_height = max(left_height, right_height) + 1 + max(len(banks['VSS']), len(banks['VDD']))

    return full_height * 100


def graphical_text_width(text):
    tally = 0
    for char in text:
        tally += glyph_widths[char]
    return tally


def symbol_body_width(pins):
    max_graphical_text_width = 0

    for pin in pins:
        name = pin['Pin_name']
        if pin['Pin_functions']:
            name += "/" + '/'.join(pin['Pin_functions'])
        max_graphical_text_width = max(graphical_text_width(name), max_graphical_text_width)

    # With body width we mean including the pins ...
    pin_with_longest_text_width = max_graphical_text_width + 50 + 300

    real_width = pin_with_longest_text_width * 2 + graphical_text_width("  ")

    # We need tou round to the nearest 100mil bound
    width = real_width + (100 - (real_width % 100))

    # print "Width %d" % width

    return width


def symbol_bank_width(bank):
    max_graphical_text_width = 0

    for pin in bank:
        name = pin['Pin_name']
        if pin["Pin_functions"]:
            name += "/" + '/'.join(pin['Pin_functions'])
        max_graphical_text_width = max(graphical_text_width(name), max_graphical_text_width)

    # With body width we mean including the pins ...
    pin_with_longest_text_width = max_graphical_text_width + 50 + 300

    real_width = pin_with_longest_text_width + graphical_text_width("  ")

    width = real_width + (100 - (real_width % 100))

    return width


def pin_append_combine(pin_list, new_pin):
    # Extract the record with the same Pin number from the pin_list if available
    pin = None
    pin_index = 0
    for p in pin_list:
        if p['Pin'] == new_pin['Pin']:
            pin = p
            break
        pin_index += 1

    if pin:
        old_functions = list(pin['Pin_functions'])
        # If the new pin's name is different than the old we add it's name to the function list
        if pin['Pin_name'] != new_pin['Pin_name']:
            pin['Pin_functions'].append(new_pin['Pin_name'])
        # If the new pin has some additional functions we add that too to the old pins function list.
        for function in new_pin['Pin_functions']:
            if function not in pin['Pin_functions']:
                pin['Pin_functions'].append(function)
        # Merge pin type
        old_t = pin['Pin_type']
        new_t = new_pin['Pin_type']
        # If they are different then we just assume the result will be I/O (Yes I know that might be wrong but ...)
        if old_t != new_t:
            pin["Pin_type"] = "I/O"
        pin_list[pin_index] = pin
        # Report the merging action
        print("Merge " + "\tpin\t", pin['Pin'], \
            "\tName:", pin['Pin_name'], \
            "\tType:", old_t, "+", new_t, "=", pin['Pin_type'], \
            "\tFunc:", old_functions, "+", new_pin['Pin_functions'])
        if pin['Pin_name'] != new_pin['Pin_name']:
            print("+", new_pin['Pin_name'])
        print("=", pin['Pin_functions'])
    else:
        pin_list.append(new_pin)


def lib_symbol(f, source_tree):
    data = []

    # Filter data for the specific footprint
    for pin_data in source_tree.findall("Pin"):
        pin = pin_data.attrib["Position"]
        pin_name = pin_data.attrib["Name"].replace(" ", "")
        pin_type = pin_data.attrib["Type"]
        pin_functions = []
        if not '--short-pins' in sys.argv:
            for pin_function in pin_data.findall("Signal"):
                pf_name = pin_function.attrib["Name"]
                if pf_name != None and pf_name != "GPIO":
                    pin_functions.append(pf_name)
        pin_append_combine(data, {'Pin': pin,
                                  'Pin_name': pin_name,
                                  'Pin_functions': pin_functions,
                                  'Pin_type': pin_type})

    # Group pins into banks
    banks = {'OTHER': [], 'VSS': [], 'VDD': []}
    for row in data:
        pin_name = row["Pin_name"]
        if re.match("VSS.?", pin_name):
            banks['VSS'].append(row)
        elif re.match("VDD.?", pin_name):
            banks['VDD'].append(row)
        else:
            m = re.match("P([A-Z])\d+", pin_name)
            if m:
                if m.group(1) in banks:
                    banks[m.group(1)].append(row)
                else:
                    banks[m.group(1)] = [row]
            else:
                banks['OTHER'].append(row)

    #
    # Plot single symbol
    #
    # pretty_print_banks(banks)
    symbol_head(f, [source_tree.attrib["RefName"]], source_tree.attrib["Package"])

    # Add pad pin to symbol if the package is a QFN type
    m = re.match(".*QFPN(\d*)", source_tree.attrib["Package"])
    if m:
        banks['VSS'].append({'Pin': str((int(m.group(1)) + 1)),
                             'Pin_name': "Pad",
                             'Pin_functions': [],
                             'Pin_type': "Passive" if source_tree.attrib["HasPowerPad"]=="false" else "Power"})

    height = symbol_pin_height(banks)
    v_offset = height / 2
    v_offset -= v_offset % 100

    width = symbol_body_width(data)
    h_offset = width / 2
    h_offset += h_offset % 100

    symbol_frame(f, -h_offset + 300, v_offset + 100, h_offset - 300, v_offset - height - 0)

    # Plot all the banks except VSS and VDD
    direction = 'R'
    counter = 0
    last_left_bank_height = 0
    last_right_bank_height = 0
    for bank in sorted(banks.keys()):
        if not (bank == "VSS" or bank == "VDD"):
            if direction == 'R':
                last_left_bank_height = len(banks[bank])
                last_right_bank_height = 0
                symbol_bank(f, banks[bank], -h_offset, v_offset + (-100 * 17) * counter, 100, direction)
                direction = 'L'
            elif direction == 'L':
                last_right_bank_height = len(banks[bank])
                symbol_bank(f, banks[bank], h_offset, v_offset + (-100 * 17) * counter, 100, direction)
                direction = 'R'
                counter += 1

    # If the last bank was on the left side then the VDD bank would go on the right side in theory,
    # this is not what we want though, we want both VDD and VSS to be on the same height, so we are moving down
    # to the next bank row
    if direction == 'R':
        counter -= 1

    last_bank_offset = -100 * (max(last_left_bank_height, last_right_bank_height) + 1)

    symbol_bank(f, banks['VDD'], -h_offset, v_offset + (-100 * 17) * counter + last_bank_offset, 100, 'R')
    symbol_bank(f, banks['VSS'],  h_offset, v_offset + (-100 * 17) * counter + last_bank_offset, 100, 'L')

    symbol_foot(f)

    #
    # Plot symbol with parts
    #
    sym_names = []
    for ref in [source_tree.attrib["RefName"]]:
        sym_names.append(ref + "_u")

    symbol_head(f, sym_names, source_tree.attrib["Package"], len(banks))

    sorted_banks = []

    for bank in sorted(banks.keys()):
        if bank == "VSS" or bank == "VDD":
            continue
        sorted_banks.append(banks[bank])
    sorted_banks.append(banks["VSS"])
    sorted_banks.append(banks["VDD"])

    part = 1
    for bank in sorted_banks:
        height = len(bank) * 100
        v_offset = height / 2
        v_offset -= v_offset % 100

        width = symbol_bank_width(bank) + 200
        h_offset = width / 2
        h_offset += h_offset % 100

        symbol_frame(f, -h_offset + 300, v_offset + 100, h_offset - 300, v_offset - height - 0, part)

        symbol_bank(f, bank, h_offset, v_offset, 100, 'L', part)

        part += 1

    symbol_foot(f)


def symbols_from_file(source_filename, target_file):
    # Open pin definition file
    print("Loading source file: " + source_filename)

    source_data = None
    # Try to load the source file
    try:
        with open(source_filename) as f:
            source_data = f.read()
            f.close()
    except:
        print("failed to open source file")
        print("Exitinig!")
        exit(1)

    # Remove xmlns (xml namespace)
    source_data = re.sub(' xmlns="[^"]+"', '', source_data, count=1)

    source_tree = None
    # Read and parse the data file
    try:
        source_tree = xml.etree.ElementTree.fromstring(source_data)
    except:
        print("source file parsing failed")
        print("Exiting!")
        exit(1)

    print("Generating symbols for: " + source_tree.attrib["RefName"])

    lib_symbol(target_file, source_tree)


# width = graphical_text_width("PA7/ADC_IN7/12S1_SD/SPI1_MOSI/TIM14_CH1/TIM17_CH1/TIM1_CH1N/TIM3_CH2")
# print "Test Text Width: " + str(width) + " double: " + str(width * 2) + "\n"


# Open library file
lib_filename = "../stm32.lib"

print("Opening '" + lib_filename + "' as our target library file")

try:
    libf = open(lib_filename, 'w')
except:
    print("could not open target library file")
    print("Exiting!")
    exit(1)

source_dir = "../stm32cube/db/mcu"
source_filenames = sorted(glob.glob(source_dir + "/STM32*.xml"))

lib_head(libf)

sources_count = 0
if True:
    for source_filename in source_filenames:
        symbols_from_file(source_filename, libf)
        sources_count += 1
else:
    symbols_from_file(source_filenames[0], libf)
    sources_count += 1

lib_foot(libf)

libf.close()

print("Generated %d STM32 symbols." % sources_count)

