import os
import shutil
import itertools
import logging
from vunit import vhdl_parser

from slvcodec import filetestbench_generator


logger = logging.getLogger(__name__)

dir_path = os.path.dirname(os.path.realpath(__file__))
helper_files = os.path.join(dir_path, 'vhdl', '*.vhd')


def update_vunit(vu, directory, filenames, top_entity, all_generics, test_class,
                 top_params):
    ftb_directory = os.path.join(directory, 'ftb')
    if os.path.exists(ftb_directory):
        shutil.rmtree(ftb_directory)
        logger.debug('update_vunit deleting {}'.format(ftb_directory))
    os.makedirs(ftb_directory)
    generated_fns, entity = filetestbench_generator.prepare_files(
       directory=ftb_directory, filenames=filenames, top_entity=top_entity)
    import random
    random_lib_name = 'lib' + str(random.randint(0, 1000))
    try:
        lib = vu.library(random_lib_name)
    except KeyError:
        lib = vu.add_library(random_lib_name)
    lib.add_source_files(generated_fns)
    lib.add_source_files(helper_files)
    lib.add_source_files(filenames)

    tb_generated = lib.entity(top_entity + '_tb')
    for generics in all_generics:
        test = test_class(entity, generics, top_params)
        tb_generated.add_config(
            name=str(hash(frozenset([(k, v) for k, v in generics.items()]))),
            generics=generics,
            pre_config=make_pre_config(test, entity, generics),
            post_check=make_post_check(test, entity, generics),
            )


def make_pre_config(test, entity, generics):
    def pre_config(output_path):
        i_data = test.make_input_data()
        lines = [entity.inputs_to_slv(line, generics=generics) for line in i_data]
        datainfilename = os.path.join(output_path, 'indata.dat')
        with open(datainfilename, 'w') as f:
            f.write('\n'.join(lines))
        return True
    return pre_config


def make_post_check(test, entity, generics):
    def post_check(output_path):
        # Read input data
        datainfilename = os.path.join(output_path, 'indata.dat')
        with open(datainfilename, 'r') as f:
            lines = f.readlines()
        i_data = [entity.inputs_from_slv(line, generics=generics) for line in lines]
        # Read output dta.
        dataoutfilename = os.path.join(output_path, 'outdata.dat')
        with open(dataoutfilename, 'r') as f:
            lines = f.readlines()
        o_data = [entity.outputs_from_slv(line, generics=generics) for line in lines]
        trimmed_o_data = o_data[:len(i_data)]
        # Check validity.
        test.check_output_data(i_data, trimmed_o_data)
        return True
    return post_check


def make_generics(**kwargs):
    all_parameter_values = kwargs.values()
    all_parameter_names = kwargs.keys()
    parameter_sets = itertools.product(*all_parameter_values)
    all_generics = [dict(zip(all_parameter_names, ps))
                    for ps in parameter_sets]
    return all_generics


class WrapperTest:

    def __init__(self, subtests):
        self.subtests = subtests

    def make_input_data(self):
        input_data = []
        old_length = 0
        self.lengths = []
        for test in self.subtests:
            input_data += test.make_input_data()
            new_length = len(input_data)
            self.lengths.append((old_length, new_length))
            old_length = new_length
        return input_data

    def check_output_data(self, input_data, output_data):
        n_subtests = len(self.subtests)
        for index, indices, test in zip(range(n_subtests), self.lengths, self.subtests):
            logger.info('Checking output in subtest {}/{}'.format(index+1, n_subtests))
            start_index, end_index = indices
            sub_input_data = input_data[start_index: end_index]
            sub_output_data = output_data[start_index: end_index]
            test.check_output_data(sub_input_data, sub_output_data)
