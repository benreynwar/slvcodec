'''
Functions that make it easier to generate test benchs and run
tests in vunit.
'''

import os
import shutil
import itertools
import logging
import random
import inspect
import json
import sys
import subprocess
import tempfile

from xml.etree import cElementTree as ET
import cocotb as true_cocotb

from slvcodec import add_slvcodec_files
from slvcodec import filetestbench_generator, flatten_generator
from slvcodec import config, fusesoc_wrapper, event, cocotb_dut
from slvcodec import cocotb_wrapper as cocotb
from slvcodec.cocotb_wrapper import triggers


logger = logging.getLogger(__name__)


def remove_duplicates(filenames):
    new_filenames = []
    for filename in filenames:
        if filename not in new_filenames:
            new_filenames.append(filename)
    return new_filenames

def register_rawtest_with_vunit(
        vu, filenames, testbench_name, entity=None, resolved=None, all_generics=None,
        test_class=None, top_params=None, pre_config=None, post_check=None):
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
    filenames = remove_duplicates(filenames)
    is_unique = False
    while not is_unique:
        random_lib_name = 'lib' + str(random.randint(0, 1000000))
        try:
            lib = vu.library(random_lib_name)
        except KeyError:
            lib = vu.add_library(random_lib_name)
            is_unique = True
        logger.debug('Adding files to lib %s', str(filenames))
    lib.add_source_files(filenames)
    tb_generated = lib.entity(testbench_name)
    if all_generics is None:
        all_generics = [{}]
    for generics_index, generics in enumerate(all_generics):
        if (pre_config is None) or (post_check is None):
            test = test_class(resolved, generics, top_params)
        if pre_config is None:
            this_pre_config = make_pre_config(test, entity, generics)
        else:
            this_pre_config = pre_config
        if post_check is None:
            this_post_check = make_post_check(test, entity, generics)
        else:
            this_post_check = post_check
        tb_generated.add_config(
            name=str(generics_index),
            generics=generics,
            pre_config=this_pre_config,
            post_check=this_post_check,
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
    generated_fns, generated_wrapper_fns, resolved = filetestbench_generator.prepare_files(
        directory=ftb_directory, filenames=with_slvcodec_files,
        top_entity=top_entity,
    )
    combined_filenames = with_slvcodec_files + generated_fns + generated_wrapper_fns
    register_rawtest_with_vunit(
        vu=vu,
        resolved=resolved,
        filenames=combined_filenames,
        entity=resolved['entities'][top_entity],
        testbench_name=top_entity + '_tb',
        all_generics=all_generics,
        test_class=test_class,
        top_params=top_params,
    )


def get_coretest_files(test, test_output_directory, param_set,
                       add_double_wrapper, default_generics, fusesoc_config_filename,
                       generate_iteratively, verbose=False):
    generated_index = 0
    generic_sets = param_set['generic_sets']
    top_params = param_set['top_params']
    generation_directory = os.path.join(
        test_output_directory, test['core_name'], 'generated_{}'.format(generated_index))
    while os.path.exists(generation_directory):
        generated_index += 1
        generation_directory = os.path.join(
            test_output_directory, test['core_name'], 'generated_{}'.format(generated_index))
    os.makedirs(generation_directory)
    if generate_iteratively:
        filenames = fusesoc_wrapper.generate_core_iteratively(
            core_name=test['core_name'],
            work_root=generation_directory,
            all_top_generics=generic_sets,
            top_params=top_params,
            top_name=test['entity_name'],
            config_filename=fusesoc_config_filename,
            additional_generator=add_slvcodec_files,
            verbose=verbose,
            )
    else:
        filenames = fusesoc_wrapper.generate_core(
            working_directory=generation_directory,
            core_name=test['core_name'],
            parameters=top_params,
            config_filename=fusesoc_config_filename,
            additional_generator=add_slvcodec_files,
            verbose=verbose,
            )
        filenames = add_slvcodec_files(generation_directory, filenames)
    ftb_directory = os.path.join(generation_directory, 'ftb')
    if os.path.exists(ftb_directory):
        shutil.rmtree(ftb_directory)
    os.makedirs(ftb_directory)
    generated_fns, generated_wrapper_fns, resolved = filetestbench_generator.prepare_files(
        directory=ftb_directory, filenames=filenames,
        top_entity=test['entity_name'],
        add_double_wrapper=add_double_wrapper,
        clock_domains=test.get('clock_domains', None),
        clock_periods=test.get('clock_periods', None),
        clock_offsets=test.get('clock_offsets', None),
        default_generics=default_generics,
        )
    combined_filenames = filenames + generated_fns + generated_wrapper_fns
    return filenames, combined_filenames, resolved


def register_coretest_with_vunit(
        vu, test, test_output_directory, add_double_wrapper=False, default_generics={},
        fusesoc_config_filename=None, generate_iteratively=False, verbose=False):
    '''
    Register a test with vunit.
    Args:
      `vu`: A vunit instance.
      `test_output_directory`: A directory in which generated files are placed.
      `test`: A dictionary containing:
        `param_sets`: An iteratable of top_params with lists of generics.
        `core_name`: The name of the fusesoc core to test.
        `wrapper_core_name`: The name of a fusesoc core that wraps the synthesizable part.
        `top_entity`: The name of the entity to test.
        `generator`: A function that takes (resolved, generics, top_params) and
         returns an object with make_input_data and check_output_data methods.
      `add_double_wrapper`: Adds wrappers that convert to and from std_logic_vector.
         Useful if you want the test to also work post-synthesis.
      `default_generics`: Default values for generics.
    '''
    if 'param_sets' in test:
        param_sets = test['param_sets']
    else:
        top_params = test.get('top_params', {})
        if 'all_generics' in test:
            all_generics = test['all_generics']
        else:
            all_generics = [test.get('generics', {})]
        param_sets = [{
            'generic_sets': all_generics,
            'top_params': top_params,
            }]
    for param_set in param_sets:
        filenames, combined_filenames, resolved = get_coretest_files(
            test, test_output_directory, param_set,
            add_double_wrapper, default_generics, fusesoc_config_filename,
            generate_iteratively, verbose=verbose)
        register_rawtest_with_vunit(
            vu=vu,
            filenames=combined_filenames,
            entity=resolved['entities'][test['entity_name']],
            testbench_name=test['entity_name'] + '_tb',
            resolved=resolved,
            all_generics=param_set['generic_sets'],
            test_class=test['generator'],
            top_params=param_set['top_params'],
            )
    return {
        'filenames': filenames,
        'combined_filenames': combined_filenames,
        }


def run_vunit(tests, cores_roots, test_output_directory):
    '''
    Setup vunit, register the tests, and run them.
    '''
    vu = config.setup_vunit()
    config.setup_logging(vu.log_level)
    for test in tests:
        register_coretest_with_vunit(vu, test, test_output_directory)
    vu.main()


def write_input_file(entity, generics, test, output_path, first_line_repeats=0):
    '''
    Generate the input data and write it to a file.
    '''
    if hasattr(test, 'clock_domains') and test.clock_domains:
        # Write an input file for each clock domain.
        i_datas = test.make_input_data()
        grouped_ports = entity.group_ports_by_clock_domain(test.clock_domains)
        assert set(i_datas.keys()) == set(grouped_ports.keys())
        for clock_name, inputs_and_outputs in grouped_ports.items():
            inputs, outputs = inputs_and_outputs
            i_data = i_datas[clock_name]
            for d in i_data:
                for p in inputs:
                    if p.name not in d:
                        d[p.name] = None
                assert set(d.keys()) == set([p.name for p in inputs])
            # Get all the signals matching the domain
            lines = [entity.inputs_to_slv(line, generics=generics, subset_only=True)
                     for line in i_data]
            if first_line_repeats > 0:
                lines = [lines[0]] * first_line_repeats + lines
            datainfilename = os.path.join(output_path, 'indata_{}.dat'.format(clock_name))
            with open(datainfilename, 'w') as f:
                f.write('\n'.join(lines))
    else:
        i_data = test.make_input_data()
        lines = [entity.inputs_to_slv(line, generics=generics) for line in i_data]
        if first_line_repeats > 0:
            lines = [lines[0]] * first_line_repeats + lines
        datainfilename = os.path.join(output_path, 'indata.dat')
        with open(datainfilename, 'w') as f:
            f.write('\n'.join(lines))
    return len(lines)


def check_output_file(entity, generics, test, output_path, first_line_repeats=0):
    '''
    Read the input data and output data and run the check_output_data
    function to verify that the test passes.
    '''
    if hasattr(test, 'clock_domains') and test.clock_domains:
        i_datas = {}
        o_datas = {}
        grouped_ports = entity.group_ports_by_clock_domain(test.clock_domains)
        for clock_name, inputs_and_outputs in grouped_ports.items():
            input_ports, output_ports = inputs_and_outputs
            if input_ports:
                datainfilename = os.path.join(output_path, 'indata_{}.dat'.format(clock_name))
                with open(datainfilename, 'r') as f:
                    lines = f.readlines()
                i_datas[clock_name] = [
                    entity.inputs_from_slv(
                        line, generics=generics, subset=[p.name for p in input_ports])
                    for line in lines][first_line_repeats:]
            if output_ports:
                dataoutfilename = os.path.join(output_path, 'outdata_{}.dat'.format(clock_name))
                with open(dataoutfilename, 'r') as f:
                    lines = f.readlines()
                o_datas[clock_name] = [
                    entity.outputs_from_slv(
                        line, generics=generics, subset=[p.name for p in output_ports])
                    for line in lines][first_line_repeats:][:len(i_datas[clock_name])]
        sig = inspect.signature(test.check_output_data)
        if len(sig.parameters) == 2:
            test.check_output_data(i_datas, o_datas)
        else:
            test.check_output_data(i_datas, o_datas, output_path)
    else:
        # Read input data
        datainfilename = os.path.join(output_path, 'indata.dat')
        with open(datainfilename, 'r') as f:
            lines = f.readlines()
        i_data = [entity.inputs_from_slv(line, generics=generics)
                  for line in lines][first_line_repeats:]
        # Read output dta.
        dataoutfilename = os.path.join(output_path, 'outdata.dat')
        with open(dataoutfilename, 'r') as f:
            lines = f.readlines()
        o_data = [entity.outputs_from_slv(line, generics=generics)
                  for line in lines][first_line_repeats:]
        trimmed_o_data = o_data[:len(i_data)]
        # Check validity.
        sig = inspect.signature(test.check_output_data)
        if len(sig.parameters) == 2:
            test.check_output_data(i_data, trimmed_o_data)
        else:
            test.check_output_data(i_data, trimmed_o_data, output_path)


def make_pre_config(test, entity, generics):
    '''
    Create a function to run before running the simulator.
    '''
    def pre_config(output_path):
        '''
        Generate the input data and write it to a file.
        '''
        write_input_file(entity=entity, generics=generics, test=test, output_path=output_path)
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
        check_output_file(entity=entity, generics=generics, test=test, output_path=output_path)
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

    def check_output_data(self, input_data, output_data, output_path=None):
        n_subtests = len(self.subtests)
        for index, indices, test in zip(range(n_subtests), self.lengths, self.subtests):
            logger.debug('Checking output in subtest {}/{}'.format(index+1, n_subtests))
            start_index, end_index = indices
            sub_input_data = input_data[start_index: end_index]
            sub_output_data = output_data[start_index: end_index]
            sig = inspect.signature(test.check_output_data)
            if len(sig.parameters) == 2:
                test.check_output_data(sub_input_data, sub_output_data)
            else:
                test.check_output_data(sub_input_data, sub_output_data, output_path)


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


def make_old_style_test(test_generator, generics, top_params):
    async def run_old_style_test(dut, loop, resolved):
        test = test_generator(resolved, generics, top_params)
        input_data = test.make_input_data()
        output_data = []
        for ipt in input_data:
            dut.set(ipt)
            await event.NextCycleFuture()
            opt = dut.get_outputs()
            output_data.append(opt)
        test.check_output_data(input_data, output_data)
        raise event.TerminateException()
    return run_old_style_test


def run_pipe_test(directory, filenames, top_entity, generics, coro, needs_resolved=False):
    simulator = event.Simulator(directory, filenames, top_entity, generics)
    os.environ['PIPE_SIM'] = 'True'
    loop = event.EventLoop(simulator)
    if needs_resolved:
        loop.create_task(coro(simulator.dut, simulator.resolved))
    else:
        loop.create_task(coro(simulator.dut))
    loop.run_forever()


def run_coretest_with_pipes(
        test, test_output_directory, add_double_wrapper=False, default_generics={},
        fusesoc_config_filename=None, generate_iteratively=False):
    '''
    Register a test with vunit.
    Args:
      `vu`: A vunit instance.
      `test_output_directory`: A directory in which generated files are placed.
      `test`: A dictionary containing:
        `param_sets`: An iteratable of top_params with lists of generics.
        `core_name`: The name of the fusesoc core to test.
        `wrapper_core_name`: The name of a fusesoc core that wraps the synthesizable part.
        `top_entity`: The name of the entity to test.
        `generator`: A function that takes (resolved, generics, top_params) and
         returns an object with make_input_data and check_output_data methods.
      `add_double_wrapper`: Adds wrappers that convert to and from std_logic_vector.
         Useful if you want the test to also work post-synthesis.
      `default_generics`: Default values for generics.
    '''
    if 'param_sets' in test:
        param_sets = test['param_sets']
    else:
        top_params = test.get('top_params', {})
        if 'all_generics' in test:
            all_generics = test['all_generics']
        else:
            all_generics = [test.get('generics', {})]
        param_sets = [{
            'generic_sets': all_generics,
            'top_params': top_params,
            }]
    dir_index = 0
    for param_set in param_sets:
        top_params = param_set['top_params']

        generated_index = 0
        generation_directory = os.path.join(
            test_output_directory, test['core_name'], 'generated_{}'.format(generated_index))
        while os.path.exists(generation_directory):
            generated_index += 1
            generation_directory = os.path.join(
                test_output_directory, test['core_name'], 'generated_{}'.format(generated_index))
        os.makedirs(generation_directory)

        if generate_iteratively:
            generic_sets = param_set['generic_sets']
            filenames = fusesoc_wrapper.generate_core_iteratively(
                core_name=test['core_name'],
                work_root=generation_directory,
                all_top_generics=generic_sets,
                top_params=top_params,
                top_name=test['entity_name'],
                config_filename=fusesoc_config_filename,
                additional_generator=add_slvcodec_files,
                )
        else:
            filenames = fusesoc_wrapper.generate_core(
                working_directory=generation_directory,
                core_name=test['core_name'],
                parameters=top_params,
                config_filename=fusesoc_config_filename,
                )
            filenames = add_slvcodec_files(generation_directory, filenames)
        for generics in param_set['generic_sets']:
            if 'coro' in test:
                coro = test['coro'](generics, top_params)
            else:
                coro = make_old_style_test(test['generator'], generics, top_params)
            needs_resolved = test.get('needs_resolved', True)
            output_directory = os.path.join(test_output_directory, 'run{}'.format(dir_index))
            while os.path.exists(output_directory):
                dir_index += 1
                output_directory = os.path.join(test_output_directory, 'run{}'.format(dir_index))
            run_pipe_test(output_directory, filenames, test['entity_name'], generics,
                          coro, needs_resolved=needs_resolved)


def run_coretest_with_cocotb(
        test, test_output_directory, fusesoc_config_filename=None, generate_iteratively=False,
        wave=False, write_input_output_files=False, verbose=False,
    ):
    '''
    Run a test with cocotb.
    Args:
      `test_output_directory`: A directory in which generated files are placed.
      `test`: A dictionary containing:
        `param_sets`: An iteratable of top_params with lists of generics.
        `core_name`: The name of the fusesoc core to test.
        `wrapper_core_name`: The name of a fusesoc core that wraps the synthesizable part.
        `top_entity`: The name of the entity to test.
        `test_module_name`: A cocotb test module name.
    '''
    print('start run_coretest_with_cocotb')
    if 'param_sets' in test:
        param_sets = test['param_sets']
    else:
        top_params = test.get('top_params', {})
        if 'all_generics' in test:
            all_generics = test['all_generics']
        else:
            all_generics = [test.get('generics', {})]
        param_sets = [{
            'generic_sets': all_generics,
            'top_params': top_params,
            }]
    for param_set in param_sets:
        top_params = param_set['top_params']

        generated_index = 0
        generation_directory = os.path.join(
            test_output_directory, test['core_name'], 'generated_{}'.format(generated_index))
        while os.path.exists(generation_directory):
            generated_index += 1
            generation_directory = os.path.join(
                test_output_directory, test['core_name'], 'generated_{}'.format(generated_index))
        os.makedirs(generation_directory)

        if generate_iteratively:
            generic_sets = param_set['generic_sets']
            print('generating iteratively')
            filenames = fusesoc_wrapper.generate_core_iteratively(
                core_name=test['core_name'],
                work_root=generation_directory,
                all_top_generics=generic_sets,
                top_params=top_params,
                top_name=test['entity_name'],
                config_filename=fusesoc_config_filename,
                additional_generator=add_slvcodec_files,
                verbose=verbose,
                )
        else:
            filenames = fusesoc_wrapper.generate_core(
                working_directory=generation_directory,
                core_name=test['core_name'],
                parameters=top_params,
                config_filename=fusesoc_config_filename,
                verbose=verbose,
                )
            filenames = add_slvcodec_files(generation_directory, filenames)
        for generics in param_set['generic_sets']:
            run_with_cocotb(
                generation_directory, filenames, test['entity_name'],
                generics, test['test_module_name'], test.get('test_params', None),
                top_params, wave=wave, write_input_output_files=write_input_output_files)


def run_with_cocotb(generation_directory, filenames, entity_name, generics, test_module_name,
                    test_params_producer=None, top_params=None, wave=False,
                    write_input_output_files=False, flatten=True,
                    ):
    entities, packages, filename_to_package_name = filetestbench_generator.process_files(
        generation_directory, filenames, entity_names_to_resolve=entity_name)
    combined_filenames = filetestbench_generator.add_slvcodec_files_inner(
        generation_directory, filenames, packages, filename_to_package_name)
    top_entity = entities[entity_name]
    if flatten:
        top_name = 'flat_' + entity_name
        wrapper = flatten_generator.make_flat_wrapper(
            top_entity, top_name, separator='_', generics=generics)
        wrapper_filename = os.path.join(generation_directory, top_name + '.vhd')
        with open(wrapper_filename, 'w') as f:
            f.write(wrapper)
        final_filenames = [wrapper_filename]
    else:
        top_name  = entity_name
        final_filenames = []
    final_filenames += combined_filenames
    os.environ['SIM'] = 'ghdl'
    mapping = cocotb_dut.get_entity_mapping(top_entity, generics=generics)
    input_port_names = [port.name for port in top_entity.ports.values() if port.direction == 'in']
    output_port_names = [port.name for port in top_entity.ports.values() if port.direction == 'out']
    test_params_filename = os.path.abspath(os.path.join(generation_directory, 'test_params.json'))
    if test_params_producer is not None:
        test_params = test_params_producer({'entitites': entities, 'packages': packages})
    else:
        test_params = {}
    params = {
        'generics': generics,
        # Use a list of tuples rather than dict so we can guarantee order.
        'mapping': mapping,
        'test_params': test_params,
        'filenames': filenames,
        'top_params': top_params,
        'input_port_names': input_port_names,
        'output_port_names': output_port_names,
        }
    if write_input_output_files:
        params.update({
            'directory': generation_directory,
            })
    with open(test_params_filename, 'w') as f:
        f.write(json.dumps(params))
    if wave:
        simulation_args = ['--wave=dump.ghw']
    else:
        simulation_args = []
    pwd = os.getcwd()
    os.chdir(generation_directory)
    run(
        vhdl_sources=final_filenames,
        simulation_args=simulation_args,
        toplevel=top_name,
        module=test_module_name,
        extra_env={'test_params_filename': test_params_filename},
        )
    os.chdir(pwd)


def run(vhdl_sources, simulation_args, toplevel, module, extra_env):
    lib_dir = os.path.join(os.path.dirname(true_cocotb.__file__), 'libs')
    shared_lib = os.path.join(lib_dir, 'libcocotbvpi_ghdl.so')
    run_dir = ''

    for key, value in extra_env.items():
        os.environ[key] = value

    lib_dir_sep = os.pathsep + lib_dir + os.pathsep
    if lib_dir_sep not in os.environ["PATH"]:  # without checking will add forever casing error
        os.environ["PATH"] += lib_dir_sep

    python_path = os.pathsep.join(sys.path)
    os.environ["PYTHONPATH"] = os.pathsep + lib_dir

    if run_dir:
        os.environ["PYTHONPATH"] += os.pathsep + run_dir
    os.environ["PYTHONPATH"] += os.pathsep + python_path

    os.environ["TOPLEVEL"] = toplevel
    os.environ["COCOTB_SIM"] = "1"
    os.environ["MODULE"] = module
    results_xml_file = tempfile.mkstemp('_cocotb_results')[1]
    os.environ["COCOTB_RESULTS_FILE"] = results_xml_file
    cmds = [['ghdl', '-i', filename] for filename in vhdl_sources]
    cmds += [
        ['ghdl', '-m', toplevel],
        ['ghdl', '-r', toplevel, '--vpi='+shared_lib] + simulation_args,
        ]
    for cmd in cmds:
        retval = subprocess.call(cmd)
        assert retval == 0
    # Check that the produced xml file by cocotb.

    tree = ET.parse(results_xml_file)
    for testsuite in tree.iter('testsuite'):
        for testcase in testsuite.iter('testcase'):
            for failure in testcase.iter("failure"):
                msg = '{} class="{}" test="{}" error={}'.format(
                    failure.get('message'), testcase.get('classname'),
                    testcase.get('name'), failure.get('stdout'))
                raise Exception(msg)
    os.remove(results_xml_file)


@cocotb.coroutine
async def clock(clock_signal, period=2, units='ns'):
    assert period % 2 == 0
    while True:
        clock_signal <= 0
        await triggers.Timer(period//2, units=units)
        clock_signal <= 1
        await triggers.Timer(period//2, units=units)
