import os
import json

from cocotb_test import run

from slvcodec import typs, filetestbench_generator, flatten_generator


def set_value(dut, base_name, mapping, value, separator):
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
            breakpoint()
        assert failed
        # And add the Bundle.
        dut.__dict__[bundle_name] = Bundle(
            base_name=bundle_name,
            parent=dut,
            mapping=bundle_mapping,
            separator=separator,
            )


class Bundle:

    def __init__(self, base_name, parent, mapping, separator):
        self.parent = parent
        self.mapping = mapping
        self.base_name = base_name
        self.separator = separator
        self.elements = []
        if isinstance(mapping, dict):
            for key, sub_mapping in mapping.items():
                assert not hasattr(self, key)
                name = base_name + separator + key
                if isinstance(sub_mapping, (dict, tuple, list)):
                    self.__dict__[key] = Bundle(name, parent, sub_mapping, separator)
                else:
                    if not hasattr(parent, name):
                        import pdb
                        pdb.set_trace()
                    self.__dict__[key] = getattr(parent, name)
        elif isinstance(mapping, (tuple, list)):
            for index, sub_mapping in enumerate(mapping):
                name = base_name + separator + str(index)
                if isinstance(sub_mapping, (dict, tuple, list)):
                    self.elements.append(Bundle(name, parent, sub_mapping, separator))
                else:
                    self.elements.append(getattr(parent, name))
        
    def __getitem__(self, index):
        return self.elements[index]

    def __le__(self, other):
        set_value(self.parent, self.base_name, self.mapping, other, self.separator)

    @property
    def value(self):
        value = get_value(self.parent, self.base_name, self.mapping, self.separator)
        return value

    @value.setter
    def set_value(self, value):
        set_value(self.parent, self.base_name, self.mapping, value, self.separator)

    def __eq__(self, other):
        return self.value == other


def get_entity_mapping(entity, generics, port_names=None, clock_name='clk'):
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


def run_with_cocotb(generation_directory, filenames, entity_name, generics, test_module_name):
    flat_name = 'flat_' + entity_name
    entities, packages, filename_to_package_name = filetestbench_generator.process_files(
        generation_directory, filenames, entity_names_to_resolve=entity_name)
    combined_filenames = filetestbench_generator.add_slvcodec_files_inner(
        generation_directory, filenames, packages, filename_to_package_name)
    top_entity = entities[entity_name]
    wrapper = flatten_generator.make_flat_wrapper(
        top_entity, flat_name, separator='_', generics=generics)
    wrapper_filename = os.path.join(generation_directory, flat_name + '.vhd')
    with open(wrapper_filename, 'w') as f:
        f.write(wrapper)
    final_filenames = [wrapper_filename] + combined_filenames
    os.environ['SIM'] = 'ghdl'
    mapping = get_entity_mapping(top_entity, generics=generics)
    test_params_filename = os.path.abspath(os.path.join(generation_directory, 'test_params.json'))
    with open(test_params_filename, 'w') as f:
        f.write(json.dumps({'generics': generics, 'mapping': mapping}))
    run.run(
        vhdl_sources=final_filenames,
        toplevel=flat_name,
        module=test_module_name,
        extra_env={'test_params_filename': test_params_filename},
        )
