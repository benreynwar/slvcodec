"""
Top level arrays and records in the ports of a VHDL entity do not work with GHDL and cocotb.

We get around this by flattening all the structures in the top level ports.
Then we modify the cocotb 'dut' object so that the ports do not appear flattened.

This file provides functions to modify the cocotb 'dut' object.
"""

import os
import json

from cocotb_test import run

from slvcodec import typs, filetestbench_generator, flatten_generator


def set_value(dut, base_name, mapping, value, separator):
    """
    Used to apply a value to a compound port in the 'dut' by the __le__ operator.
    e.g.
    myarray <= [1, 2, 3]
    or
    myarray[1] <= 6
    Args:
       `dut`: The cocotb interface to the tested entity.
       `base_name`: A path to the position in the port hierarchy that we are modifying.
                    (e.g. myarray_0_key)
       `mapping`: A representation of the structure of the position in the port hierarchy.
                  (e.g. [{a: None, b: None}, {a: None, b: None}, {a: None, b: None}] for a list
                  of records with length 3.)  None is useful to represent types that are not
                  arrays or records.
       `value`: The value that we which to apply to this port.
       `separator`: The separator that is used when flattening ports.
                    (i.e. '_' so that myarray(0).a becomes myarray_0_a)
    """
    if isinstance(value, dict):
        assert isinstance(mapping, dict)
        for sub_key, sub_value in value.items():
            set_value(dut, base_name + separator + sub_key,
                      mapping[sub_key], sub_value, separator)
    elif isinstance(value, (list, tuple)):
        assert len(mapping) == len(value)
        for sub_index, sub_value in enumerate(value):
            set_value(dut, base_name + separator + str(sub_index),
                      mapping[sub_index], sub_value, separator)
    else:
        getattr(dut, base_name) <= value


def get_value(dut, base_name, mapping, separator):
    """
    Used to retrieve the value from a compound port in the 'dut'.
    Args:
       `dut`: The cocotb interface to the tested entity.
       `base_name`: A path to the position in the port hierarchy that we are modifying.
                    (e.g. myarray_0_key)
       `mapping`: A representation of the structure of the position in the port hierarchy.
                  (e.g. [{a: None, b: None}, {a: None, b: None}, {a: None, b: None}] for a list
                  of records with length 3.)  None is useful to represent types that are not
                  arrays or records.
       `separator`: The separator that is used when flattening ports.
                    (i.e. '_' so that myarray(0).a becomes myarray_0_a)
    """
    if isinstance(mapping, dict):
        value = {sub_key: get_value(dut, base_name + separator + sub_key, sub_mapping, separator)
                 for sub_key, sub_mapping in mapping.items()}
    elif isinstance(mapping, (list, tuple)):
        value = [get_value(dut, base_name + separator + str(sub_index), sub_mapping, separator)
                 for sub_index, sub_mapping in enumerate(mapping)]
    else:
        value = getattr(dut, base_name).value
    return value


def apply_mapping(dut, mapping, separator):
    """
    Adds 'Bundle' objects to the dut that represent compound ports.
    This allows us to treat the dut as if the ports have not been flattened.
    """
    for bundle_name, bundle_mapping in mapping.items():
        if not isinstance(bundle_mapping, (dict, list, tuple)):
            continue
        # Confirm that the bundle_name won't overwrite something.
        failed = False
        try:
            attr = getattr(dut, bundle_name)
        except AttributeError:
            failed = True
        if not failed:
            raise ValueError('The bundle name ({}) cannot be added to the dut because an attribute of the same name already exists.'.format(bundle_name))
        assert failed
        # And add the Bundle.
        dut.__dict__[bundle_name] = Bundle(
            base_name=bundle_name,
            dut=dut,
            mapping=bundle_mapping,
            separator=separator,
            )


class Bundle:
    """
    Added to the cocotb dut to imitate a compound port or an element within a
    compound ports hierarchy.
    """

    def __init__(self, base_name, dut, mapping, separator):
        """
        Args:
            `base_name`: The location of this element within the hierarchy.
            `dut`: The dut that we're modifying.
            `mapping`: The structure of this element.
            `separator`: The separator used when flattening ports.
        """
        self.dut = dut
        self.mapping = mapping
        self.base_name = base_name
        self.separator = separator
        self.elements = []
        if isinstance(mapping, dict):
            for key, sub_mapping in mapping.items():
                assert not hasattr(self, key)
                name = base_name + separator + key
                if isinstance(sub_mapping, (dict, tuple, list)):
                    self.__dict__[key] = Bundle(name, dut, sub_mapping, separator)
                else:
                    if not hasattr(dut, name):
                        import pdb
                        pdb.set_trace()
                    self.__dict__[key] = getattr(dut, name)
        elif isinstance(mapping, (tuple, list)):
            for index, sub_mapping in enumerate(mapping):
                name = base_name + separator + str(index)
                if isinstance(sub_mapping, (dict, tuple, list)):
                    self.elements.append(Bundle(name, dut, sub_mapping, separator))
                else:
                    self.elements.append(getattr(dut, name))

    def __getitem__(self, index):
        return self.elements[index]

    def __le__(self, other):
        set_value(self.dut, self.base_name, self.mapping, other, self.separator)

    @property
    def value(self):
        value = get_value(self.dut, self.base_name, self.mapping, self.separator)
        return value

    @value.setter
    def set_value(self, value):
        set_value(self.dut, self.base_name, self.mapping, value, self.separator)

    def __eq__(self, other):
        return self.value == other


def get_entity_mapping(entity, generics, port_names=None, clock_name='clk'):
    """
    Creates the `mapping` object that other tools in this file use.
    Extracts the information from the `entity` object that is the result
    of parsing the vhdl files.

    Args:
       `entity`: The result of parsing the vhdl files.  Represents a VHDL entity.
       `generics`: The generic parameters we're going to use.
       `port_names`: A list of port names for which we want to get the mapping.
                     The default is to get all of them.
       `clock_name`: The clock is excluded from the mapping.
    """
    mapping = {}
    ports = entity.ports
    for port_name, port in ports.items():
        if port_name == clock_name:
            continue
        if port_names is not None:
            if port_name not in port_names:
                continue
        mapping[port_name] = get_mapping(port.typ, generics)
    return mapping


def get_mapping(typ, generics):
    """
    Creates the `mapping` object for a VHDL type.

    Args:
       `typ`: A typ object produced by parsing VHDL files.
       `generics`: The generic parameters we're going to use.
    """
    mapping = None
    if hasattr(typ, 'names_and_subtypes'):
        mapping = {}
        for name, sub_type in typ.names_and_subtypes:
            mapping[name] = get_mapping(sub_type, generics)
    elif hasattr(typ, 'unconstrained_type'):
        size = typs.apply_generics(generics, typ.size)
        if isinstance(typ.unconstrained_type.subtype, typs.StdLogic):
            mapping = None
        else:
            mapping = [get_mapping(typ.unconstrained_type.subtype, generics)] * size
    return mapping
