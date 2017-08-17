import os
import shutil
import itertools
import logging
import random

import fusesoc_generators
from slvcodec import add_slvcodec_files
from slvcodec import filetestbench_generator
from slvcodec import params_helper, config


logger = logging.getLogger(__name__)

dir_path = os.path.dirname(os.path.realpath(__file__))
helper_files = os.path.join(dir_path, 'vhdl', '*.vhd')


def register_rawtest_with_vunit(
        vu, resolved, filenames, top_entity, all_generics, test_class,
        top_params):
    random_lib_name = 'lib' + str(random.randint(0, 1000))
    try:
        lib = vu.library(random_lib_name)
    except KeyError:
        lib = vu.add_library(random_lib_name)
    logger.debug('Adding files to lib {}'.format(filenames))
    lib.add_source_files(filenames)
    tb_generated = lib.entity(top_entity + '_tb')
    entity = resolved['entities'][top_entity]
    for generics in all_generics:
        test = test_class(resolved, generics, top_params)
        name = str(generics)
        if len(name) > 30:
            h = hash(params_helper.make_hashable(generics))
            name = str(h)
        tb_generated.add_config(
            name=name,
            generics=generics,
            pre_config=make_pre_config(test, entity, generics),
            post_check=make_post_check(test, entity, generics),
        )


def register_test_with_vunit(
        vu, directory, filenames, top_entity, all_generics, test_class,
        top_params):
    ftb_directory = os.path.join(directory, 'ftb')
    if os.path.exists(ftb_directory):
        shutil.rmtree(ftb_directory)
    os.makedirs(ftb_directory)
    logger.debug('update_vunit deleting {}'.format(ftb_directory))
    with_slvcodec_files = add_slvcodec_files(directory, filenames)
    generated_fns, resolved = filetestbench_generator.prepare_files(
        directory=ftb_directory, filenames=with_slvcodec_files,
        top_entity=top_entity)
    combined_filenames = with_slvcodec_files + generated_fns
    register_rawtest_with_vunit(
        vu=vu,
        resolved=resolved,
        filenames=combined_filenames,
        top_entity=top_entity,
        all_generics=all_generics,
        test_class=test_class,
        top_params=top_params,
    )


def register_coretest_with_vunit(vu, test, test_output_directory):
    if 'param_sets' in test:
        param_sets = test['param_sets']
    elif 'all_generics' in test:
        param_sets = [{
            'generic_sets': test['all_generics'],
            'top_params': {},
        }]
    else:
        param_sets = [{
            'generic_sets': [{}],
            'top_params': {},
        }]
    for param_set in param_sets:
        generic_sets = param_set['generic_sets']
        top_params = param_set['top_params']
        h = hash(params_helper.make_hashable(top_params))
        generation_directory = os.path.join(
            test_output_directory, test['core_name'], 'generated_{}'.format(h))
        if os.path.exists(generation_directory):
            shutil.rmtree(generation_directory)
        logger.debug('Removing directory {}'.format(generation_directory))
        os.makedirs(generation_directory)
        # Create this side effect object so that we can create a function
        # that has the interface fusesoc_generator expects but we can still
        # get access to the 'resolved' from parsing.
        filenames = fusesoc_generators.get_filenames_from_core(
            generation_directory, test['core_name'], test['entity_name'],
            generic_sets, top_params, add_slvcodec_files)
        ftb_directory = os.path.join(generation_directory, 'ftb')
        if os.path.exists(ftb_directory):
            shutil.rmtree(ftb_directory)
        os.makedirs(ftb_directory)
        generated_fns, resolved = filetestbench_generator.prepare_files(
            directory=ftb_directory, filenames=filenames,
            top_entity=test['entity_name'])
        combined_filenames = filenames + generated_fns
        register_rawtest_with_vunit(
            vu=vu,
            resolved=resolved,
            filenames=combined_filenames,
            top_entity=test['entity_name'],
            all_generics=generic_sets,
            test_class=test['generator'],
            top_params=top_params,
        )


def run_vunit(tests, cores_roots, test_output_directory):
    vu = config.setup_vunit()
    config.setup_logging(vu.log_level)
    config.setup_fusesoc(cores_roots)
    for test in tests:
        register_coretest_with_vunit(vu, test, test_output_directory)
    vu.main()


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
