#!/usr/bin/env python2
"""Kicad library file generator for the stm32cube database files."""

__author__ = 'esdentem'

import xml.etree.ElementTree
import re
import StringIO
# import os
import glob

def pretty_print_banks(banks):
    bank_names = sorted(banks.keys())
    for bank in bank_names:
        print "Bank: %s" % bank
        print "\tPin\tName\tType\tStruct\tFunc"
        for pin in banks[bank]:
            print "\t%s\t%s\t%s\t%s\t%s" % (pin['Pin'],
                                            pin['Pin_name'],
                                            pin['Pin_type'],
                                            pin['Pin_structure'],
                                            pin['Pin_functions'])


def lib_head(f):
    print >>f, 'EESchema-Library Version 2.3\n'
    print >>f, '#encoding utf-8'


def lib_foot(f):
    print >>f, '#'
    print >>f, '#End Library'


def symbol_head(f, names, footprint):
    print >>f, "#"
    print >>f, "# " + names[0]
    print >>f, "#"
    print >>f, "DEF " + names[0] + " U 0 50 Y Y 1 F N"
    print >>f, "F0 \"U\" 0 100 50 H V C CNN"
    print >>f, "F1 \"" + names[0] + "\" 0 -100 50 H V C CNN"
    print >>f, "F2 \"" + footprint + "\" 0 -200 50 H V C CIN"
    print >>f, "F3 \"\" 0 0 50 H V C CNN"
    if len(names) > 1:
        print >>f, "ALIAS",
        for name in names[1:]:
            f.write(" " + name)
        print >>f, "\n",
    print >>f, "DRAW"


def symbol_frame(f, startx, starty, endx, endy):
    print >>f, "S %s %s %s %s 0 1 10 N" % (startx, starty, endx, endy)


def symbol_pin(f, name, num, x, y, direction, io_type):
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
        else:
            print "Pin '%s' does not have a valid type '%s' defaulting to bidirectional 'B'." % (name, io_type)
    else:
        print "Pin '%s' io type is empty, defaulting to bidirectional 'B'." % name

    print >>f, "X %s %s %s %s 300 %s 50 50 1 1 %s" % (name, num, x, y, direction, pin_type)


def symbol_bank(f, pins, x_offset, y_offset, spacing, direction):
    counter = 0

    def pin_sort_key(pin_key):
        m = re.match("(\D*)(\d*)", pin_key['Pin_name'])
        return '{}{:0>3}'.format(m.group(1), m.group(2))

    for pin in sorted(pins, key=pin_sort_key):
        name = pin['Pin_name']
        if pin['Pin_functions']:
            name += "/" + '/'.join(pin['Pin_functions'])
        if direction == 'R' or direction == 'L':
            symbol_pin(f, name, pin['Pin'], x_offset, y_offset - (counter * spacing), direction, pin['Pin_type'])
        elif direction == 'U' or direction == 'D':
            symbol_pin(f, name, pin['Pin'], x_offset, y_offset - (counter * spacing), direction, pin['Pin_type'])
        else:
            print "Unknown direction!!!"
        counter += 1


def symbol_foot(f):
    print >>f, "ENDDRAW"
    print >>f, "ENDDEF"


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


def symbol_body_width(pins):
    max_char_count = 0

    for pin in pins:
        name = pin['Pin_name']
        if pin['Pin_functions']:
            name += "/" + '/'.join(pin['Pin_functions'])
        max_char_count = max(len(name), max_char_count)

    # The Char width is not constant so we can not 100% rely on the char width value. This also means it is as wide as
    # the widest character making the width usually larger than necessary.
    char_width = 52
    real_width = char_width * (max_char_count * 2 + 2)

    # We need tou round to the nearest 100mil bound
    width = real_width + (100 - (real_width % 100))

    #print "Width %d" % width

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
        print "Merge " + "\tpin\t", pin['Pin'], \
            "\tName:", pin['Pin_name'], \
            "\tType:", old_t, "+", new_t, "=", pin['Pin_type'], \
            "\tFunc:", old_functions, "+", new_pin['Pin_functions'],
        if pin['Pin_name'] != new_pin['Pin_name']:
            print "+", new_pin['Pin_name'],
        print "=", pin['Pin_functions']
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
    # pretty_print_banks(banks)
    symbol_head(f, [source_tree.attrib["RefName"]], source_tree.attrib["Package"])

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


def symbols_from_file(source_filename, target_file):
    # Open pin definition file
    print "Loading source file: " + source_filename

    source_data = None
    # Try to load the source file
    try:
        with open(source_filename) as f:
            source_data = f.read()
            f.close()
    except:
        print "failed to open source file"
        print "Exitinig!"
        exit(1)

    # Remove xmlns (xml namespace)
    source_data = re.sub(' xmlns="[^"]+"', '', source_data, count=1)

    source_tree = None
    # Read and parse the data file
    try:
        source_tree = xml.etree.ElementTree.fromstring(source_data)
    except:
        print "source file parsing failed"
        print "Exiting!"
        exit(1)

    print "Generating symbols for: " + source_tree.attrib["RefName"]

    lib_symbol(target_file, source_tree)


# Open library file
lib_filename = "../stm32.lib"

print "Opening '" + lib_filename + "' as our target library file"

try:
    libf = open(lib_filename, 'w')
except:
    print "could not open target library file"
    print "Exiting!"
    exit(1)

source_dir = "../stm32cube/db/mcu"
source_filenames = glob.glob(source_dir + "/STM32*.xml")

lib_head(libf)
sources_count = 0
for source_filename in source_filenames:
    symbols_from_file(source_filename, libf)
    sources_count += 1
lib_foot(libf)

libf.close()

print "Generated %d STM32 symbols." % sources_count

