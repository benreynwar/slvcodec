'''
Functions that make it easier to generate test benchs and run
tests in vunit.
'''

import os
import shutil
import itertools
import logging
import random

import fusesoc_generators
from slvcodec import add_slvcodec_files
from slvcodec import filetestbench_generator
from slvcodec import config


logger = logging.getLogger(__name__)


def register_rawtest_with_vunit(
        vu, resolved, filenames, top_entity, all_generics, test_class,
        top_params):
    '''
    Register a test with vunit.
    Args:
      `vu`: A vunit instance.
      `resolved`: A dictionary of parsed VHDL object.
      `filenames`: The filenames for the test.  Includes testbench.
      `top_entity`: The name of the top level entity.
      `all_generics`: An iterable of dictionaries of the top level generics to
         test.
      `test_class`: A function that takes (resolved, generics, top_params) and
         returns an object with make_input_data and check_output_data methods.
      `top_params`: Top level parameters to pass to the test class.
    '''
    # FIXME: Currently we create a new lib for each test.
    # This is very inefficient.
    random_lib_name = 'lib' + str(random.randint(0, 1000000))
    try:
        lib = vu.library(random_lib_name)
    except KeyError:
        lib = vu.add_library(random_lib_name)
    logger.debug('Adding files to lib %s', str(filenames))
    lib.add_source_files(filenames)
    tb_generated = lib.entity(top_entity + '_tb')
    entity = resolved['entities'][top_entity]
    for generics_index, generics in enumerate(all_generics):
        test = test_class(resolved, generics, top_params)
        tb_generated.add_config(
            name=str(generics_index),
            generics=generics,
            pre_config=make_pre_config(test, entity, generics),
            post_check=make_post_check(test, entity, generics),
        )


def register_test_with_vunit(
        vu, directory, filenames, top_entity, all_generics, test_class,
        top_params):
    '''
    Register a test with vunit.
    Args:
      `vu`: A vunit instance.
      `directory`: A directory in which generated files are placed.
      `filenames`: The filenames for the test.  Does not include testbench.
      `top_entity`: The name of the top level entity.
      `all_generics`: An iterable of dictionaries of the top level generics to
         test.
      `test_class`: A function that takes (resolved, generics, top_params) and
         returns an object with make_input_data and check_output_data methods.
      `top_params`: Top level parameters to pass to the test class.
    '''
    ftb_directory = os.path.join(directory, 'ftb')
    if os.path.exists(ftb_directory):
        shutil.rmtree(ftb_directory)
    os.makedirs(ftb_directory)
    logger.debug('update_vunit deleting %s', ftb_directory)
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
    '''
    Register a test with vunit.
    Args:
      `vu`: A vunit instance.
      `test_output_directory`: A directory in which generated files are placed.
      `test`: A dictionary containing:
        `param_sets`: An iteratable of top_params with lists of generics.
        `core_name`: The name of the fusesoc core to test.
        `top_entity`: The name of the entity to test.
        `generator`: A function that takes (resolved, generics, top_params) and
         returns an object with make_input_data and check_output_data methods.
    '''
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
    for param_set_index, param_set in enumerate(param_sets):
        generic_sets = param_set['generic_sets']
        top_params = param_set['top_params']
        generation_directory = os.path.join(
            test_output_directory, test['core_name'], 'generated_{}'.format(param_set_index))
        if os.path.exists(generation_directory):
            shutil.rmtree(generation_directory)
        logger.debug('Removing directory %s', generation_directory)
        os.makedirs(generation_directory)
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
    '''
    Setup vunit, register the tests, and run them.
    '''
    vu = config.setup_vunit()
    config.setup_logging(vu.log_level)
    config.setup_fusesoc(cores_roots)
    for test in tests:
        register_coretest_with_vunit(vu, test, test_output_directory)
    vu.main()


def make_pre_config(test, entity, generics):
    '''
    Create a function to run before running the simulator.
    '''
    def pre_config(output_path):
        '''
        Generate the input data and write it to a file.
        '''
        i_data = test.make_input_data()
        lines = [entity.inputs_to_slv(line, generics=generics) for line in i_data]
        datainfilename = os.path.join(output_path, 'indata.dat')
        with open(datainfilename, 'w') as f:
            f.write('\n'.join(lines))
        return True
    return pre_config


def make_post_check(test, entity, generics):
    '''
    Create a function to run after running the simulator.
    '''
    def post_check(output_path):
        '''
        Read the input data and output data and run the check_output_data
        function to verify that the test passes.
        '''
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
    '''
    Given all the possible values for each generic parameters, creates
    a list of all the possible generic dictionaries.
    '''
    all_parameter_values = kwargs.values()
    all_parameter_names = kwargs.keys()
    parameter_sets = itertools.product(*all_parameter_values)
    all_generics = [dict(zip(all_parameter_names, ps))
                    for ps in parameter_sets]
    return all_generics


class WrapperTest:
    '''
    Wraps a number of tests providing make_input_data and check_output_data
    methods into a single test with the same interface.
    '''

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


def split_data(is_splits, data, include_initial=False):
    '''
    The list `data` is split into a list of sublists where the
    position of the splits is given by `is_splits`.

    `is_splits` is a list containing boolean values.  If the
    value is true then that position corresponds to the first
    position in a sublist.

    >>> split_data(is_splits=[0, 0, 1, 0, 1, 0, 0, 1],
    ...            data=[1, 2, 3, 4, 5, 6, 7, 8],
    ...            include_initial=False)
    [[3, 4], [5, 6, 7], [8]]
    >>> split_data(is_splits=[0, 0, 1, 0, 1, 0, 0, 1],
    ...            data=[1, 2, 3, 4, 5, 6, 7, 8],
    ...            include_initial=True)
    [[1, 2], [3, 4], [5, 6, 7], [8]]
    '''
    split_datas = []
    if include_initial:
        this_data = []
    else:
        this_data = None
    for is_split, d in zip(is_splits, data):
        if is_split:
            if this_data is not None:
                split_datas.append(this_data)
            this_data = []
        if this_data is not None:
            this_data.append(d)
    if this_data:
        split_datas.append(this_data)
    return split_datas
