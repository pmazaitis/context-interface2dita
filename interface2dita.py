#!/usr/local/bin/python3

from lxml import etree
import argparse
from pathlib import Path
import string
from collections import OrderedDict
import datetime
import pprint
import random
from distutils.dir_util import copy_tree


import logging

logging.basicConfig(filename="interface2dita_debug.log",
                    format='%(levelname)s:%(message)s', level=logging.DEBUG)

logger = logging.getLogger(__name__)

# --- Constants and other long-lived data ---

SOURCE_BASE_URL = "https://source.contextgarden.net/tex/context/base/mkiv/"

NSMAP = {'cd': 'http://www.pragma-ade.com/commands'}

donor_set = set()

# --- Utility Functions ---


def ppxml(element, element_doctype='''<!DOCTYPE reference PUBLIC "-//OASIS//DTD DITA Reference//EN" "reference.dtd">'''):
    foobytes = etree.tostring(element,
                              pretty_print=True,
                              xml_declaration=True,
                              encoding='UTF-8',
                              doctype=element_doctype)

    foo = foobytes.decode("utf-8")

    foo = foo.replace('xmlns:ns0="http://www/w3/org/XML/1998/namespace" ', '')
    foo = foo.replace('ns0:lang="en"', 'xml:lang="en"')

    return(foo)


def get_command_url(command_name):
    return f"commands/{command_name[0].lower()}/r_command_{command_name}.dita"


# --- Dealing with Variants ---

def generate_variant_data(
        command_name, command_stanza, variant_type):
    return("Not implemented yet")


# --- Functions to manage the command data ---

def generate_settings_keys(argument):

    keys = []

    # each of the keys can be an option inheritance, a simple value, or a placeholder

    for value in argument:

        this_key = {}

        # print(f"Working with key value: {ppxml(value)}")

        if value.tag == "{http://www.pragma-ade.com/commands}inherit":
            # print(f"Found inheritance from options in {value.get('name')}")
            this_key['type'] = "inherit"
            this_key['donor'] = value.get('name')
            this_key['donor_id'] = "options1"
            donor_set.add(this_key['donor'])

        elif value.tag == "{http://www.pragma-ade.com/commands}constant":
            # (f"Found key name of {value.get('type')}")
            if "cd:" in value.get('type'):
                this_key['type'] = "placeholder"
                this_key['text'] = value.get('type')[3:].upper()
            else:
                this_key['type'] = "simple"
                this_key['text'] = value.get('type')

            if 'default' in value.attrib and value.get('default') == 'yes':
                this_key['default'] = True
            else:
                this_key['default'] = False
        keys.append(this_key)

    return keys


def generate_settings(argument):
    settings = []

    # one set of assignments

    # settings key=value can be inherited as a whole, or have children
    # if articulated, settings keys can be an option inheritance, a simple value, or a placeholder

    for value in argument:

        # Handling the parameter or inherit element as the value, here

        this_setting = {}

        # this should always work
        try:
            value_name = value.get('name')
        except:
            logger.warn(f"Couldn't get name for setting!")

        this_setting['name'] = value_name

        # This is either going to be an inherit, or a parameter

        if value.tag == "{http://www.pragma-ade.com/commands}inherit":
            this_setting['type'] = "inherit"
            this_setting['donor'] = value.get('name')
            this_setting['donor_id'] = "settings1"
            donor_set.add(this_setting['donor'])
        elif value.tag == "{http://www.pragma-ade.com/commands}parameter":
            # get the keys in the parameter
            this_setting['type'] = "keys"
            this_setting['keys'] = generate_settings_keys(value)

        settings.append(this_setting)

    return settings


def generate_options(argument):
    options = []

    # Option values can be of one of three types: an inheritance, a simple value, or a placeholder

    for value in argument:

        this_option = {}

        if value.tag == "{http://www.pragma-ade.com/commands}constant":
            # print(f"Found constant with type {value.get('type')}")
            if "cd:" in value.get('type'):
                this_option['type'] = "placeholder"
                this_option['text'] = value.get('type')[3:].upper()
            else:
                this_option['type'] = "simple"
                this_option['text'] = value.get('type')

            if 'default' in value.attrib and value.get('default') == 'yes':
                this_option['default'] = True
            else:
                this_option['default'] = False

        elif value.tag == "{http://www.pragma-ade.com/commands}inherit":
            # print(f"Found inheritance from command {value.get('name')}")
            this_option['type'] = "inherit"
            this_option['donor'] = value.get('name')
            this_option['donor_id'] = "options1"
            donor_set.add(this_option['donor'])
        options.append(this_option)

    return options


def is_argument_optional(arg):
    if "optional" in arg.attrib and arg.get('optional') == 'yes':
        return True
    else:
        return False


def get_argument_delimiters(arg):

    try:
        delim_type = arg.get('delimiters')
    except:
        pass

    if delim_type is None:
        delim_type = "brackets"

    return delim_type


def get_argument_type(arg):
    if arg.tag == "{http://www.pragma-ade.com/commands}keywords":
        if len(arg) == 1:
            if 'type' in arg[0].attrib and "cd:" in arg[0].get('type'):
                return arg[0].get('type')[3:].upper()
        return "OPTIONS"
    elif arg.tag == "{http://www.pragma-ade.com/commands}assignments":
        return "SETTINGS"
    elif arg.tag == "{http://www.pragma-ade.com/commands}csname":
        return "COMMAND"
    elif arg.tag == "{http://www.pragma-ade.com/commands}content":
        return "SCOPE"
    elif arg.tag == "{http://www.pragma-ade.com/commands}delimiter":
        return "DELIMITER"
    elif arg.tag == "{http://www.pragma-ade.com/commands}dimension":
        return "DIMENSION"
    elif arg.tag == "{http://www.pragma-ade.com/commands}triplet":
        return "TRIPLET"
    elif arg.tag == "{http://www.pragma-ade.com/commands}position":
        return "POSITION"
    elif arg.tag == "{http://www.pragma-ade.com/commands}string":
        return "STRING"
    elif arg.tag == "{http://www.pragma-ade.com/commands}angles":
        return "ANGLES"
    elif arg.tag == "{http://www.pragma-ade.com/commands}template":
        return "TEMPLATE"
    elif arg.tag == "{http://www.pragma-ade.com/commands}apply":
        return "APPLY"
    elif arg.tag == "{http://www.pragma-ade.com/commands}text":
        return "TEXT"
    elif arg.tag == "{http://www.pragma-ade.com/commands}index":
        return "INDEX"
    else:
        logger.warning(
            f"Found unknown argument type of {arg.tag} in:\n{ppxml(arg)}")


def generate_args_data(args_tree):
    args_list = []

    option_i = 0
    setting_i = 0

    for args in args_tree:

        for argument in args:
            this_argument = {}
            this_argument['delimiters'] = get_argument_delimiters(argument)
            this_argument['type'] = get_argument_type(argument)
            if this_argument['type'] == "SCOPE":
                this_argument['delimiters'] = "braces"
            if this_argument['type'] == "DELIMITER":
                this_argument['delimiters'] = "none"
                this_argument[f'name'] = argument.get('name')
            this_argument['optional'] = is_argument_optional(argument)
            if this_argument['type'] == "OPTIONS":
                option_i += 1
                this_argument[f'name'] = f"options{option_i}"
                this_argument[f'count'] = len(argument)
                this_argument[f'children'] = generate_options(
                    argument)
            if this_argument['type'] == "SETTINGS":
                setting_i += 1
                this_argument[f'name'] = f"settings{setting_i}"
                this_argument[f'count'] = len(argument)
                this_argument[f'children'] = generate_settings(
                    argument)

            args_list.append(this_argument)

    return args_list


def generate_command_data(
        command_name, command_stanza, instance_donor, instances=[], instance_of=""):

    keywords = []

    try:
        command_level = command_stanza.get('level')
    except:
        command_level = "UNKNOWN"

    if command_level == "system":
        command_is_system = True
    else:
        command_is_system = False

    try:
        reported_category = command_stanza.get('category')
    except:
        reported_category = False

    if reported_category:
        keywords.append(reported_category)

    try:
        source_filename = command_stanza.get('file')
    except:
        source_filename = "UNKNOWN"

    try:
        args_tree = command_stanza.xpath('cd:arguments', namespaces=NSMAP)
    except:
        args_tree = []

    args = generate_args_data(args_tree)

    command_topic_data = {
        'name': command_name,
        'is_system': command_is_system,
        'category': command_level,
        'instances': instances,
        'instance_of': instance_of,
        'instance_donor': instance_donor,
        'keywords': keywords,
        'filename': source_filename,
        'args_tree': args_tree,
        'arguments': args,
        'tree': command_stanza,
    }

    for arg in args:
        if 'name' in arg and arg['name'] == 'options1':
            command_topic_data['options1_count'] = arg['count']
        if 'name' in arg and arg['name'] == 'settings1':
            command_topic_data['settings1_count'] = arg['count']

    return command_topic_data


def list_of_commands(tr, nsp):
    root = tr.getroot()

    pred = f'cd:interface/cd:command'

    all_commands = root.xpath(pred, namespaces=nsp)

    result = []

    for c in all_commands:
        result.append(c)

    return result


def add_command_to_dict(this_dict, command_name, command_stanza, instances=[], instance_of="", is_begin=False, begin_string="", is_end=False, end_string="", instance_donor=""):

    if is_begin:
        command_name = begin_string + command_name
    elif is_end:
        command_name = end_string + command_name

    if command_name in this_dict:
        logger.debug(
            f"Warning! Attempting to clobber entry for {command_name}!")
    else:
        this_dict[command_name] = generate_command_data(
            command_name, command_stanza, instance_donor, instances, instance_of, )

    if is_end:
        this_dict[command_name]['arguments'] = []


def generate_env_related_dict(env_related_dict, commands_dict):

    prefixes = ['start', 'stop', 'setup', 'define']

    for stem in env_related_dict:
        for pre in prefixes:
            if pre + stem in commands_dict:
                env_related_dict[stem].append(pre + stem)

    return env_related_dict


def process_generated_environment(commands_dict, command_name, command_stanza, ignored_stems_for_related, env_related_dict):
    if command_name != "section":
        return

    sequence = []
    instance_stems = []
    instances = []

    print(ppxml(command_stanza))
    print(command_stanza.attrib)

    sequence_xml = command_stanza.xpath(
        'cd:sequence', namespaces=NSMAP)[0]

    for part in sequence_xml:
        sequence.append(part.get('value'))

    if len(sequence) == 3:
        command_prefix = sequence[0]
        command_stem = sequence[1]
        command_postfix = sequence[2]
    elif len(sequence) == 1:
        command_prefix = ""
        command_stem = sequence[0]
        command_postfix = ""

    instances_xml = command_stanza.xpath(
        'cd:instances/cd:constant', namespaces=NSMAP)

    for instance_stem in instances_xml:
        instance_stems.append(instance_stem.get('value'))

    instance_stems.remove(command_stem)

    for this_stem in instance_stems:
        instance_name = command_prefix + this_stem + command_postfix
        instances.append(instance_name)
    print(
        f"## Variant for {command_name} is of type instance, and is a generated environment")
    print(f"### Sequence: {sequence}, {len(sequence)}")
    print(f"### Instances: {instances}, {len(instances)}")

    add_command_to_dict(commands_dict, command_name,
                        command_stanza, instances=instances)
    add_command_to_dict(commands_dict, command_name,
                        command_stanza, instance_donor=command_name, instance_of=command_name, is_begin=True, begin_string="start")
    add_command_to_dict(commands_dict, command_name,
                        command_stanza, instance_donor=command_name, instance_of=command_name, is_end=True, end_string="stop")

    # add instance commands
    for instance in instances:
        add_command_to_dict(commands_dict, instance,
                            command_stanza, instance_donor=command_name, instance_of=command_name)
        add_command_to_dict(commands_dict, instance,
                            command_stanza, instance_donor=command_name, instance_of="start" + command_name, is_begin=True, begin_string="start")
        add_command_to_dict(commands_dict, instance,
                            command_stanza, instance_donor=command_name, instance_of="stop" + command_name, is_end=True, end_string="stop")

    add_command_to_dict(commands_dict, command_name,
                        command_stanza, instances=instances)

    # We keep track of appropriate commands to add to the generated reltable here
    if command_name not in ignored_stems_for_related:
        env_related_dict[command_name] = []


def process_instance(commands_dict, command_name, command_stanza, ignored_stems_for_related, env_related_dict):

    # TODO remove after debugging
    # if command_name == "section":
    #     print(ppxml(command_stanza))
    #     print(command_stanza.attrib)

    if command_stanza.get('generated') == 'yes' and command_stanza.get('type') == "environment":
        process_generated_environment(
            commands_dict, command_name, command_stanza, ignored_stems_for_related, env_related_dict)
    elif command_stanza.get('generated') == 'yes':
        # TODO handle this case
        pass
        # print(
        #     f"## Variant for {command_name} is of type instance")


def process_interface_tree(ft):
    """Use the complete interface XML file to prepare dictionaries of commands:
    one of commands (style, document, and system) and one of variants.
    """

    logger.debug("### Processing interface tree.")

    ignored_stems_for_related = ['startstop']

    commands_dict = {}
    variants_dict = {}
    env_related_dict = {}

    interface_commands = list_of_commands(ft, NSMAP)

    for command_stanza in interface_commands:
        # First, check if we have a valid name attribute; if that fails, log the offending stanza
        try:
            command_name = command_stanza.attrib['name']
        except:
            logger.debug(
                f"ENONAME: No name found in the folllowing stanza:\n\n{ppxml(command_stanza)}\n\n")
            continue

        if command_name.encode(
                "ascii", errors="ignore").decode() == "":
            # we have no name to work with, bail out
            logger.debug(
                f"EEMPTYNAME: Empty name found in the folllowing stanza:\n\n{ppxml(command_stanza)}\n\n")
            continue

        try:
            variant_type = command_stanza.get('variant')
        except:
            variant_type = False

        try:
            command_type = command_stanza.attrib['type']
        except:
            command_type = False

        if 'begin' in command_stanza.attrib:
            found_begin = True
            begin_string = command_stanza.attrib['begin']
        else:
            found_begin = False
            begin_string = ""

        if 'end' in command_stanza.attrib:
            found_end = True
            # This terrible nonsense is to handle NBSP in attribute value
            end_string = command_stanza.attrib['end'].encode(
                "ascii", errors="ignore").decode()
        else:
            found_end = False
            end_string = ""

        if variant_type:
            # Handle variants, and instances of variants
            #print(f"Variant found for {command_name}")
            # what the heck is happening with setuppapersize
            if command_name == "setuppapersize":
                add_command_to_dict(commands_dict, command_name,
                                    command_stanza)
            elif variant_type == "instance":
                #print(f"Variant for {command_name} is of type instance")
                process_instance(commands_dict, command_name,
                                 command_stanza, ignored_stems_for_related, env_related_dict)
            else:
                add_command_to_dict(variants_dict, command_name,
                                    command_stanza)
        else:
            # Handle all other commands
            if found_begin or found_end:
                # We want to handle all the cases here; we may have begin, end, or both
                # (but we need to generate both commands in any case)
                add_command_to_dict(commands_dict, command_name,
                                    command_stanza, is_begin=True, begin_string=begin_string)
                add_command_to_dict(commands_dict, command_name,
                                    command_stanza, is_end=True, end_string=end_string)
            else:
                # Simple case of single command
                add_command_to_dict(
                    commands_dict, command_name, command_stanza)

        if command_type == "environment":
            # Generate start and stop commands
            add_command_to_dict(commands_dict, command_name,
                                command_stanza, is_begin=True, begin_string="start")
            add_command_to_dict(commands_dict, command_name,
                                command_stanza, is_end=True, end_string="stop")
            # We keep track of appropriate commands to add to the generated reltable here
            if command_name not in ignored_stems_for_related:
                env_related_dict[command_name] = []

    # Run back through the dict of commands stems, and add to the child list any
    # command that has the environment as a stem of common forms

    env_related_dict = generate_env_related_dict(
        env_related_dict, commands_dict)

    return commands_dict, variants_dict, env_related_dict

# --- Topic Building Functions ---


def add_topic_rellinks(topic_data):
    related_links_string = f"""
    <related-links>
      <link href="{SOURCE_BASE_URL}{topic_data['filename']}" scope="external" format="html">
        <linktext>Command definition in the <ph conkeyref="definitions/product_name"/> source file  <filepath>{topic_data['filename']}</filepath></linktext>
      </link>
    </related-links>"""

    related_links_element = etree.fromstring(related_links_string)

    return related_links_element


def add_topic_second_ex():
    second_example_string = """<example id="example_02" rev="0" otherprops="no_output">
      <title>Descriptive Example Title</title>
      <codeblock outputclass="normalize-space">
\\starttext



\\stoptext
      </codeblock>
    </example>"""
    second_example_comment = etree.Comment(second_example_string)
    return second_example_comment


def add_topic_mwe():
    mwe_string = """
    <example id="mwe" rev="0" otherprops="no_output">
      <title>Minimal Working Example</title>
      <codeblock outputclass="normalize-space">
\\starttext



\\stoptext
      </codeblock>
    </example>"""
    mwe_element = etree.fromstring(mwe_string)
    return mwe_element


def add_topic_notes():
    notes_comment_string = """<section id="notes">
      <title>Notes</title>
      <p></p>
    </section>"""
    notes_comment = etree.Comment(notes_comment_string)
    return notes_comment


def add_topic_instances(instances):
    instances_section_element = etree.Element('section')

    title_element = etree.Element('title')
    title_element.text = "Instances"
    instances_section_element.append(title_element)

    intro_p_element = etree.Element('p')
    intro_p_element.text = "This command has the following instances:"
    instances_section_element.append(intro_p_element)

    instance_list_element = etree.Element('ul')

    for i in instances:
        li_element = etree.Element('li')
        xref_element = etree.Element(
            'xref', href=f"../../{get_command_url(i)}")
        xref_element.text = i
        li_element.append(xref_element)
        instance_list_element.append(li_element)

    instances_section_element.append(instance_list_element)

    return instances_section_element


def add_topic_refbody_settings(argument_data):

    settings_donors = set()
    options_donors = set()

    settings_section_element = etree.Element(
        'section', id=argument_data['name'])

    title_element = etree.Element('title')
    title_element.text = "Settings"
    settings_section_element.append(title_element)

    settings_table_element = etree.Element(
        'table', frame="all", rowsep="1", colsep="1")

    # We need a tgroup for each child

    for c in argument_data['children']:
        if c['type'] == 'keys':
            # We have a set of keys to process
            table_group_element = etree.Element('tgroup', cols="2")
            table_group_element.append(etree.Element(
                'colspec', colname="value_name", colnum="1", colwidth="1*"))
            table_group_element.append(etree.Element(
                'colspec', colname="value_desc", colnum="2", colwidth="1*"))

            table_head_element = etree.Element('thead')

            table_head_first_row_element = etree.Element('row')

            for k in c['keys']:
                if k['type'] == "inherit":
                    table_head_title_entry = etree.Element(
                        'entry', namest="value_name", nameend="value_desc")
                    table_head_title_entry.text = f"{c['name']}"
                    ph_element = etree.Element('ph')
                    ph_element.text = " (Inherits from "
                    xref_element = etree.Element(
                        'xref', href=f"../{k['donor'][0]}/r_command_{k['donor']}.dita")
                    xref_element.tail = ")"
                    ph_element.append(xref_element)
                    table_head_title_entry.append(ph_element)
                    break
            else:
                table_head_title_entry = etree.Element(
                    'entry', namest="value_name", nameend="value_desc")
                table_head_title_entry.text = c['name']

            table_head_first_row_element.append(table_head_title_entry)

            table_head_element.append(table_head_first_row_element)

            table_head_second_row_string = """<row>
              <entry>Value</entry>
              <entry>Description</entry>
            </row>"""

            table_head_second_row_element = etree.fromstring(
                table_head_second_row_string)

            table_head_element.append(table_head_second_row_element)

            table_group_element.append(table_head_element)

            table_body_element = etree.Element('tbody')

            for k in c['keys']:

                if k['type'] == "inherit":
                    options_donors.add(k['donor'])
                    donor_set.add(k['donor'])

                    # print("## Donor Data:")
                    # pp = pprint.PrettyPrinter(indent=2)
                    # pp.pprint(commands_dict[c['donor']])

                    if commands_dict[k['donor']]['options1_count'] == 1:
                        inheritance_element_string = f'''<row conkeyref="command_{k['donor']}/options1_entry">
                      <entry></entry>
                    </row>
                    '''
                    elif commands_dict[k['donor']]['options1_count'] > 1:
                        inheritance_element_string = f'''<row conkeyref="command_{k['donor']}/options1_start" conrefend="default.dita#default/options1_stop">
                      <entry></entry>
                    </row>
                    '''
                    else:
                        logger.warn(
                            f"Trying to inherit options from {k['donor']}, but donor has no count.")

                    table_row_element = etree.fromstring(
                        inheritance_element_string)

                elif k['type'] == "placeholder":
                    table_row_element = etree.Element('row')
                    keyword_entry_element = etree.Element('entry')
                    placeholder_name_element = etree.Element(
                        'xref', keyref=k['text'], type="reference")
                    keyword_entry_element.append(placeholder_name_element)
                    table_row_element.append(keyword_entry_element)

                    keyword_desc_element = etree.Element('entry')
                    placeholder_desc_element = etree.Element(
                        'ph', conkeyref=f"{k['text']}/placeholder_desc")
                    keyword_desc_element.append(placeholder_desc_element)
                    table_row_element.append(keyword_desc_element)

                elif k['type'] == "simple":
                    table_row_element = etree.Element('row')
                    keyword_entry_element = etree.Element('entry')
                    keyword_entry_element.text = k['text']
                    table_row_element.append(keyword_entry_element)
                    keyword_desc_element = etree.Element('entry', rev="0")
                    keyword_desc_element.text = ""
                    table_row_element.append(keyword_desc_element)

                else:
                    logger.debug(f"Unknown keytype of key type: {k['type']}")

                if 'default' in k and k['default'] == True:
                    table_row_element.attrib['importance'] = "default"

                table_body_element.append(table_row_element)

            table_group_element.append(table_body_element)

        elif c['type'] == 'inherit':
            # We are pulling in a settings set
            settings_donors.add(c['donor'])
            donor_set.add(c['donor'])

            # print("## Donor Data:")
            # pp = pprint.PrettyPrinter(indent=2)
            # pp.pprint(commands_dict[c['donor']])

            if commands_dict[c['donor']]['settings1_count'] > 1:
                multigroup_inherit_string = f"""<tgroup conkeyref="command_{c['donor']}/settings1_start" conrefend="default.dita#default/settings1_stop" cols="2">
                        <colspec/>
                        <colspec/>
                        <thead>
                            <row>
                                <entry></entry>
                            </row>
                        </thead>
                        <tbody>
                            <row>
                                <entry></entry>
                            </row>
                        </tbody>
                    </tgroup>"""
                table_group_element = etree.fromstring(
                    multigroup_inherit_string)
            elif commands_dict[c['donor']]['settings1_count'] == 1:
                singlegroup_inherit_string = f"""<tgroup conkeyref="command_{c['donor']}/settings1_entry" cols="2">
                        <colspec/>
                        <colspec/>
                        <thead>
                            <row>
                                <entry></entry>
                            </row>
                        </thead>
                        <tbody>
                            <row>
                                <entry></entry>
                            </row>
                        </tbody>
                    </tgroup>"""
                table_group_element = etree.fromstring(
                    singlegroup_inherit_string)

        settings_table_element.append(table_group_element)

    settings_section_element.append(settings_table_element)

    if len(settings_table_element) > 1:
        settings_table_element[0].attrib['id'] = f"{argument_data['name']}_start"
        settings_table_element[-1].attrib['id'] = f"{argument_data['name']}_stop"
    elif len(settings_table_element) == 1:
        settings_table_element[0].attrib['id'] = f"{argument_data['name']}_entry"

    for donor in settings_donors:
        donor_xref_element = etree.Element(
            'xref', href=f"../../{get_command_url(donor)}")
        donor_xref_element.tail = "."
        note_element = etree.Element('note')
        note_element.text = "Inherits settings from "
        note_element.append(donor_xref_element)
        settings_section_element.append(note_element)

    for donor in options_donors:
        donor_xref_element = etree.Element(
            'xref', href=f"../../{get_command_url(donor)}")
        donor_xref_element.tail = "."
        note_element = etree.Element('note')
        note_element.text = "Inherits options from "
        note_element.append(donor_xref_element)
        settings_section_element.append(note_element)

    return settings_section_element


def add_topic_refbody_options(argument_data):

    options_donors = set()

    options_section_element = etree.Element(
        'section', id=argument_data['name'])

    title_element = etree.Element('title')
    title_element.text = "Options"
    options_section_element.append(title_element)

    options_table_element = etree.Element(
        'table', frame="all", rowsep="1", colsep="1", id=f"{argument_data['name']}_table")

    table_group_element = etree.Element('tgroup', cols="2")

    table_group_element.append(etree.Element(
        'colspec', colname="value_name", colnum="1", colwidth="1*"))
    table_group_element.append(etree.Element(
        'colspec', colname="value_desc", colnum="2", colwidth="1*"))

    table_head_string = """<thead>
            <row>
              <entry>Keyword</entry>
              <entry>Description</entry>
            </row>
          </thead>"""

    table_group_element.append(etree.fromstring(table_head_string))

    table_body_element = etree.Element('tbody')

    for c in argument_data['children']:
        if c['type'] == "inherit":
            options_donors.add(c['donor'])
            donor_set.add(c['donor'])

            # print("## Donor Data:")
            # pp = pprint.PrettyPrinter(indent=2)
            # pp.pprint(commands_dict[c['donor']])

            if commands_dict[c['donor']]['options1_count'] == 1:
                inheritance_element_string = f'''<row conkeyref="command_{c['donor']}/options1_entry">
              <entry></entry>
            </row>
            '''
            elif commands_dict[c['donor']]['options1_count'] > 1:
                inheritance_element_string = f'''<row conkeyref="command_{c['donor']}/options1_start" conrefend="default.dita#default/options1_stop">
              <entry></entry>
            </row>
            '''
            else:
                logger.warn(
                    f"Trying to inherit options from {c['donor']}, but donor has no count.")

            table_row_element = etree.fromstring(inheritance_element_string)

        elif c['type'] == "placeholder":
            table_row_element = etree.Element('row')
            keyword_entry_element = etree.Element('entry')
            placeholder_name_element = etree.Element(
                'xref', keyref=c['text'], type="reference")
            keyword_entry_element.append(placeholder_name_element)
            table_row_element.append(keyword_entry_element)

            keyword_desc_element = etree.Element('entry')
            placeholder_desc_element = etree.Element(
                'ph', conkeyref=f"{c['text']}/placeholder_desc")
            keyword_desc_element.append(placeholder_desc_element)
            table_row_element.append(keyword_desc_element)

        elif c['type'] == "simple":
            table_row_element = etree.Element('row')
            keyword_entry_element = etree.Element('entry')
            keyword_entry_element.text = c['text']
            table_row_element.append(keyword_entry_element)
            keyword_desc_element = etree.Element('entry', rev="0")
            keyword_desc_element.text = ""
            table_row_element.append(keyword_desc_element)

        if 'default' in c and c['default'] == True:
            table_row_element.attrib['importance'] = "default"

        table_body_element.append(table_row_element)

    if len(table_body_element.getchildren()) > 1:
        table_body_element[0].attrib['id'] = f"{argument_data['name']}_start"
        table_body_element[-1].attrib['id'] = f"{argument_data['name']}_stop"
    elif len(table_body_element.getchildren()) == 1:
        table_body_element[0].attrib['id'] = f"{argument_data['name']}_entry"

    table_group_element.append(table_body_element)

    options_table_element.append(table_group_element)

    options_section_element.append(options_table_element)

    for donor in options_donors:
        donor_xref_element = etree.Element(
            'xref', href=f"../../{get_command_url(donor)}")
        donor_xref_element.tail = "."
        note_element = etree.Element('note')
        note_element.text = "Inherits options from "
        note_element.append(donor_xref_element)
        options_section_element.append(note_element)

    return options_section_element


def add_topic_refbody_refsyn_simpletable_row(this_argument):
    row_element = etree.Element('strow')

    name_entry_element = etree.Element('stentry')
    desc_entry_element = etree.Element('stentry')
    vals_entry_element = etree.Element('stentry')

    placeholder_name_element = etree.Element(
        'xref', keyref=this_argument['type'], type="reference")
    name_entry_element.append(placeholder_name_element)

    placeholder_desc_element = etree.Element(
        'ph', conkeyref=f"{this_argument['type']}/placeholder_desc")
    desc_entry_element.append(placeholder_desc_element)

    if this_argument['type'] == "OPTIONS":
        # This is the complicated one; we want to actually include a short list of options here

        vals_entry_element = etree.Element('stentry')
        current_element = vals_entry_element
        current_element.text = ""
        in_tail = False

        for c in this_argument['children']:
            if 'type' in c and c['type'] == "inherit":
                # Set upthe translcusion, then return the whole row element
                row_element = etree.Element(
                    'strow', conkeyref=f"command_{c['donor']}/short_options1", id=f"short_{this_argument['name']}")
                row_element.append(etree.Element('stentry'))
                row_element.append(etree.Element('stentry'))
                row_element.append(etree.Element('stentry'))
                return row_element
            elif c['default'] == True and c['type'] == "placeholder":
                placeholder_name_element = etree.Element(
                    'xref', keyref=c['text'], type="reference")
                default_phrase = etree.Element('ph', importance="default")
                default_phrase.append(placeholder_name_element)
                vals_entry_element.append(default_phrase)
                current_element = default_phrase
                current_element.tail = ", "
                in_tail = True
            elif c['type'] == "placeholder":
                placeholder_name_element = etree.Element(
                    'xref', keyref=c['text'], type="reference")
                vals_entry_element.append(placeholder_name_element)
                current_element = placeholder_name_element
                current_element.tail = ", "
                in_tail = True
            elif c['default'] == True:
                default_phrase = etree.Element('ph', importance="default")
                default_phrase.text = c['text']
                current_element = default_phrase
                current_element.tail = ", "
                in_tail = True
            else:
                if in_tail:
                    current_element.tail += f"{c['text']}, "
                else:
                    current_element.text += f"{c['text']}, "

        # Get rid of trailing comma
        if in_tail:
            current_element.tail = current_element.tail[:-2]
        else:
            current_element.text = current_element.text[:-2]

        row_element.set('id', f'short_{this_argument["name"]}')

        if vals_entry_element != current_element:
            vals_entry_element.append(current_element)

        # Add link to section
        xref_element = etree.Element(
            'xref', href=f"#./{this_argument['name']}")
        xref_element.text = " (See options table for details.)"
        vals_entry_element.append(xref_element)

    elif this_argument['type'] == "SETTINGS":
        xref_element = etree.Element(
            'xref', href=f"#./{this_argument['name']}")
        xref_element.text = " (See settings table for details.)"
        vals_entry_element.append(xref_element)

    elif this_argument['type'] == "DELIMITER":
        vals_entry_element.text = "\\" + this_argument['name']

    else:
        placeholder_vals_element = etree.Element(
            'ph', conkeyref=f"{this_argument['type']}/placeholder_value")
        vals_entry_element.append(placeholder_vals_element)

    row_element.append(name_entry_element)
    row_element.append(desc_entry_element)
    row_element.append(vals_entry_element)

    return row_element


def add_topic_refbody_refsyn_simpletable(topic_data):
    simpletable_element = etree.Element('simpletable')

    simpletable_header_string = """
                    <sthead>
          <stentry>Name</stentry>
          <stentry>Description</stentry>
          <stentry>Values</stentry>
        </sthead>"""

    simpletable_element.append(etree.fromstring(simpletable_header_string))

    for this_argument in topic_data['arguments']:
        simpletable_element.append(
            add_topic_refbody_refsyn_simpletable_row(this_argument))

    return simpletable_element


def add_topic_refbody_refsyn_synph_var(this_argument):

    if this_argument['optional']:
        var_element = etree.Element('var', importance="optional")
    else:
        var_element = etree.Element('var')

    if this_argument['type'] == 'DELIMITER':
        var_element.text = "\\" + this_argument['name']
    elif this_argument['type'] == 'OPTIONS':
        var_element.set('id', f"synvar_{this_argument['name']}")
        var_element.text = this_argument['type']
    elif this_argument['type'] == 'SETTINGS':
        var_element.set('id', f"synvar_{this_argument['name']}")
        var_element.text = this_argument['type']
    else:
        var_element.text = this_argument['type']

    return var_element


def add_delimiter(type, chirality="left"):
    delimiter_element = etree.Element('delim')

    if type == 'parenthesis':
        if chirality == 'left':
            delimiter_element.text = "("
        if chirality == 'right':
            delimiter_element.text = ")"
    elif type == 'braces':
        if chirality == 'left':
            delimiter_element.text = "{"
        if chirality == 'right':
            delimiter_element.text = "}"
    elif type == 'brackets':
        if chirality == 'left':
            delimiter_element.text = "["
        if chirality == 'right':
            delimiter_element.text = "]"
    else:
        delimiter_element.text = "?"

    return delimiter_element


def add_topic_refbody_refsyn_synph(topic_data):

    synph_element = etree.Element('synph')

    synph_element.text = f"\\{topic_data['name']} "

    for this_argument in topic_data['arguments']:
        if this_argument['delimiters'] != "none":
            synph_element.append(add_delimiter(
                this_argument['delimiters'], 'left'))

        synph_element.append(
            add_topic_refbody_refsyn_synph_var(this_argument))

        if this_argument['delimiters'] != "none":
            synph_element.append(add_delimiter(
                this_argument['delimiters'], 'right'))

    return synph_element


def add_topic_refbody_refsyn(topic_data):
    refsyn_element = etree.Element('refsyn', id="syntax")

    title_element = etree.Element('title')
    title_element.text = "Syntax"
    refsyn_element.append(title_element)

    # The refsyn_synph show the syntax of the command
    refsyn_element.append(add_topic_refbody_refsyn_synph(topic_data))

    # The refsyn_table lists and describes the elements of the synph
    if len(topic_data['arguments']) > 0:
        refsyn_element.append(add_topic_refbody_refsyn_simpletable(topic_data))

    # if this command is an instance, indicate it
    if topic_data['instance_of'] != "":
        instance_of_xref_element = etree.Element(
            'xref', href=f"../../{get_command_url(topic_data['instance_of'])}")
        instance_of_xref_element.tail = "."
        note_element = etree.Element('note')
        note_element.text = "Instance of "
        note_element.append(instance_of_xref_element)
        refsyn_element.append(note_element)

    return refsyn_element


def add_topic_refbody(topic_data):
    refbody_element = etree.Element('refbody')

    refbody_element.append(add_topic_refbody_refsyn(topic_data))

    for argument_data in topic_data['arguments']:
        if argument_data['type'] == 'OPTIONS':
            refbody_element.append(add_topic_refbody_options(argument_data))
        elif argument_data['type'] == 'SETTINGS':
            refbody_element.append(add_topic_refbody_settings(argument_data))

    if topic_data['instances']:
        refbody_element.append(add_topic_instances(topic_data['instances']))

    refbody_element.append(add_topic_notes())
    refbody_element.append(add_topic_mwe())
    refbody_element.append(add_topic_second_ex())

    return refbody_element


def add_topic_prolog(topic_data):

    prolog_element = etree.Element('prolog')

    # Source file (TODO: is this path reasonable?)

    source_element = etree.Element('source')
    source_element.text = f"tex/texmf-context/tex/context/base/mkiv/{topic_data['filename']}"
    prolog_element.append(source_element)

    # Critical Dates

    critdates_element = etree.Element('critdates')

    random_number_of_days = random.randrange(120, 240)
    check_date = today + datetime.timedelta(days=random_number_of_days)

    created_element = etree.Element(
        'created', date=f"{today.strftime('%Y-%m-%d')}", expiry=f"{check_date.strftime('%Y-%m-%d')}")
    critdates_element.append(created_element)

    revised_comment = etree.Comment(
        '<revised date="YYYY-MM-DD" expiry="YYYY-MM-DD"/>')
    critdates_element.append(revised_comment)

    prolog_element.append(critdates_element)

    # Metadata

    metadata_element = etree.Element('metadata')

    if topic_data['is_system']:
        audience_element = etree.Element('audience', type="internal")
    else:
        audience_element = etree.Element('audience', type="user")
    metadata_element.append(audience_element)

    category_element = etree.Element('category')
    category_element.text = topic_data['category']
    metadata_element.append(category_element)

    keywords_element = etree.Element('keywords')
    for kw in topic_data['keywords']:
        keyword_element = etree.Element('keyword')
        keyword_element.text = kw
        keywords_element.append(keyword_element)
    metadata_element.append(keywords_element)

    prodinfo_string = """
            <prodinfo>
        <prodname>ConTeXt</prodname>
          <vrmlist>
            <vrm version="iv" release="production" modification=""/>
          </vrmlist>
        </prodinfo>"""

    prodinfo_element = etree.fromstring(prodinfo_string)

    metadata_element.append(prodinfo_element)

    prolog_element.append(metadata_element)

    return prolog_element


def add_topic_shortdesc(topic_data):
    cmdname_element = etree.Element('cmdname')
    cmdname_element.text = f"\\{topic_data['name']}"
    cmdname_element.tail = " command..."

    shortdesc_element = etree.Element('shortdesc', rev='0')
    shortdesc_element.text = "The "
    shortdesc_element.append(cmdname_element)

    return shortdesc_element


def add_topic_title(topic_data):
    title_element = etree.Element('title')
    title_element.text = f"\\{topic_data['name']}"
    return title_element


def generate_dita_topic(topic_data):
    topic = etree.Element('reference', id=f"r_command_{topic_data['name']}")

    attr = topic.attrib
    attr['{http://www/w3/org/XML/1998/namespace}lang'] = "en"

    topic.append(add_topic_title(topic_data))
    topic.append(add_topic_shortdesc(topic_data))
    topic.append(add_topic_prolog(topic_data))
    topic.append(add_topic_refbody(topic_data))
    topic.append(add_topic_rellinks(topic_data))

    return topic


# --- Dealing With Output

def make_output_dirs(base_path, lang):

    # Setup areas for common and translation
    common_path = base_path / 'common'
    common_path.mkdir(exist_ok=True)
    supported_languages = ['en']

    for language in supported_languages:
        lp = base_path / language
        lp.mkdir(exist_ok=True)

    focus_path = base_path / lang

    topic_areas = ["commands", "frontmatter", "glossary",
                   "out", "placeholders", "support", "temp", ]

    for directory in topic_areas:
        topic_area = focus_path / directory
        topic_area.mkdir(exist_ok=True)

    for directory in string.ascii_lowercase:
        command_area = focus_path / "commands" / directory
        command_area.mkdir(exist_ok=True)

    return focus_path


def import_manually_edited_topics(met_path, build_path):
    copy_tree(str(met_path), str(build_path), update=1)


def write_command_topic(topic_element, name, path):

    filename = path / "commands" / name[0].lower() / f"r_command_{name}.dita"

    output_bytes = etree.tostring(topic_element,
                                  pretty_print=True,
                                  xml_declaration=True,
                                  encoding='UTF-8',
                                  doctype='''<!DOCTYPE reference PUBLIC "-//OASIS//DTD DITA Reference//EN" "reference.dtd">''')

    output = output_bytes.decode("utf-8")

    output = output.replace(
        'xmlns:ns0="http://www/w3/org/XML/1998/namespace" ', '')
    output = output.replace('ns0:lang="en"', 'xml:lang="en"')

    with open(filename, 'w') as f:
        f.write(output)


def write_inheritance_ditamap(donor_set, path):
    inheritance_map = etree.Element('map')
    attr = inheritance_map.attrib
    attr['{http://www/w3/org/XML/1998/namespace}lang'] = "en"

    title_element = etree.Element('title')
    title_element.text = "Command Inheritance"
    inheritance_map.append(title_element)

    inheritance_map.append(etree.Comment(
        "Conrefs for commands that use settings that other command inheirit. We only ever want to update these in one place, and have all of the dependant commands also update."))

    for donor in donor_set:
        keydef_element = etree.Element(
            'keydef', keys=f"command_{donor}", href=f"commands/{donor[0]}/r_command_{donor}.dita")
        inheritance_map.append(keydef_element)

    filename = path / "inheritance.ditamap"

    output_bytes = etree.tostring(inheritance_map,
                                  pretty_print=True,
                                  xml_declaration=True,
                                  encoding='UTF-8',
                                  doctype='''<!DOCTYPE map PUBLIC "-//OASIS//DTD DITA Map//EN" "map.dtd">''')

    output = output_bytes.decode("utf-8")

    output = output.replace(
        'xmlns:ns0="http://www/w3/org/XML/1998/namespace" ', '')
    output = output.replace('ns0:lang="en"', 'xml:lang="en"')

    with open(filename, 'w') as f:
        f.write(output)


def write_related_ditamap(related_dict, path):
    inheritance_map = etree.Element('map')
    attr = inheritance_map.attrib
    attr['{http://www/w3/org/XML/1998/namespace}lang'] = "en"

    title_element = etree.Element('title')
    title_element.text = "Command Inheritance"

    inheritance_map.append(etree.Comment(
        "Reltable for related commands: each row with as many cells needed for all of the related commands to that particular command."))

    reltable_element = etree.Element('reltable')

    reltable_header_row_string = """<relheader>
      <relcolspec type="reference"><!--Command--></relcolspec>
      <relcolspec type="reference"><!--Related--></relcolspec>
    </relheader>"""

    reltable_element.append(etree.fromstring(reltable_header_row_string))

    for command_list in related_dict.values():
        for command in command_list:
            sibling_list = command_list.copy()
            sibling_list.remove(command)
            # print(command, sibling_list)
            relrow_element = etree.Element('relrow')
            single_relcell_element = etree.Element('relcell')
            topicref_element = etree.Element(
                'topicref', href=f"commands/{command[0].lower()}/r_command_{command}.dita")
            single_relcell_element.append(topicref_element)
            relrow_element.append(single_relcell_element)
            multiple_relcell_element = etree.Element('relcell')
            for command in sibling_list:
                topicref_element = etree.Element(
                    'topicref', href=f"commands/{command[0].lower()}/r_command_{command}.dita")
                multiple_relcell_element.append(topicref_element)
            relrow_element.append(multiple_relcell_element)
            reltable_element.append(relrow_element)

    inheritance_map.append(reltable_element)

    filename = path / "relations.ditamap"

    output_bytes = etree.tostring(inheritance_map,
                                  pretty_print=True,
                                  xml_declaration=True,
                                  encoding='UTF-8',
                                  doctype='''<!DOCTYPE map PUBLIC "-//OASIS//DTD DITA Map//EN" "map.dtd">''')

    output = output_bytes.decode("utf-8")

    output = output.replace(
        'xmlns:ns0="http://www/w3/org/XML/1998/namespace" ', '')
    output = output.replace('ns0:lang="en"', 'xml:lang="en"')

    with open(filename, 'w') as f:
        f.write(output)


def write_command_ditamap(command_list, path, map_filename, map_title):
    command_map = etree.Element('map')
    attr = command_map.attrib
    attr['{http://www/w3/org/XML/1998/namespace}lang'] = "en"

    title_element = etree.Element('title')
    title_element.text = map_title
    command_map.append(title_element)

    for command in sorted(command_list):
        keydef_element = etree.Element(
            'topicref', keys=f"command_{command}", href=f"commands/{command[0]}/r_command_{command}.dita")
        command_map.append(keydef_element)

    filename = path / map_filename

    output_bytes = etree.tostring(command_map,
                                  pretty_print=True,
                                  xml_declaration=True,
                                  encoding='UTF-8',
                                  doctype='''<!DOCTYPE map PUBLIC "-//OASIS//DTD DITA Map//EN" "map.dtd">''')

    output = output_bytes.decode("utf-8")

    output = output.replace(
        'xmlns:ns0="http://www/w3/org/XML/1998/namespace" ', '')
    output = output.replace('ns0:lang="en"', 'xml:lang="en"')

    with open(filename, 'w') as f:
        f.write(output)


# --- Main ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Client settings")
    parser.add_argument("--input", type=str, default="context-en.xml")
    parser.add_argument("--lang", type=str, default="en")
    parser.add_argument("--name", type=str)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--testdata", action="store_true")
    args = vars(parser.parse_args())

    input_file = args['input']

    full_tree = etree.parse(input_file)

    today = datetime.date.today()

    print("Starting up.")

    # Process tree into dict of commands and variants

    print("Processing interface file.")

    commands_dict, variants_dict, related_dict = process_interface_tree(
        full_tree)

    # TODO remove after debugging
    # print("## reltable Data Structure")
    # pp = pprint.PrettyPrinter(indent=2)
    # pp.pprint(related_dict)

    if args['testdata']:

        # TODO remove after debugging
        # print("## reltable Data Structure")
        # pp = pprint.PrettyPrinter(indent=2)
        # pp.pprint(related_dict)

        print("Done!")

    elif args['all']:

        print("Generating command topics.")

        logger.debug("### Starting run of all commands!")

        # Setting up paths

        build_path = Path.cwd() / 'build'
        build_path.mkdir(exist_ok=True, parents=True)
        dita_path = Path.cwd() / 'build' / 'dita'
        dita_path.mkdir(exist_ok=True, parents=True)

        manual_topics_path = Path.cwd() / 'manually_edited_topics'

        focus_path = make_output_dirs(dita_path, args['lang'])

        # Keep track of what commands we see for the maps
        full_topics_list = []
        user_topics_list = []
        system_topics_list = []

        print("Writing topic files.")

        for num, (command_name, command_data) in enumerate(commands_dict.items()):
            logger.info(f"{num:04}: Processing {command_data['name']}...")

            command_data = commands_dict[command_name]

            xml_topic = generate_dita_topic(command_data)

            full_topics_list.append(command_name)
            if command_data['is_system']:
                system_topics_list.append(command_data['name'])
            else:
                user_topics_list.append(command_data['name'])

            write_command_topic(xml_topic, command_name, focus_path)

        print("Writing maps.")

        write_inheritance_ditamap(donor_set, focus_path)

        write_related_ditamap(related_dict, focus_path)

        # Ditamap files for DITA processors
        write_command_ditamap(full_topics_list, focus_path,
                              "full_commands.ditamap", "Full Commands")
        write_command_ditamap(user_topics_list, focus_path,
                              "user_commands.ditamap", "User Commands")
        write_command_ditamap(system_topics_list, focus_path,
                              "system_commands.ditamap", "System Commands")

        # XML files for ConTeXt setups
        write_command_ditamap(full_topics_list, focus_path,
                              "full_commands.xml", "Full Commands")
        write_command_ditamap(user_topics_list, focus_path,
                              "user_commands.xml", "User Commands")
        write_command_ditamap(system_topics_list, focus_path,
                              "system_commands.xml", "System Commands")

        print("Importing manually edited topics.")

        import_manually_edited_topics(manual_topics_path, build_path)

        print("Done.")

    elif args['name']:
        # show individual dita

        req_name = args['name']

        logger.debug(f"### Processing for command {req_name}!")

        if req_name in commands_dict:

            requested_command = commands_dict[req_name]

            print(f"## XML stanza:")
            print(ppxml(requested_command['tree']))

            print("## Resulting Data Structure")
            pp = pprint.PrettyPrinter(indent=2)
            pp.pprint(requested_command)

            print("## DITA Output:")
            print(ppxml(generate_dita_topic(requested_command)))

        else:
            print(f"Command name {commands_dict[req_name]} unknown!")

    else:
        print("No action taken")

    logger.debug("\n*\n*\n*")
