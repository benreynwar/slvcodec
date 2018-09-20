import shutil
import os

import fusesoc_generators
from pyvivado import base_project, vivado_project, boards, jtagtestbench_generator

from slvcodec import add_slvcodec_files, filetestbench_generator, test_utils


def from_fusesoc_core(
        directory, corename, entityname, generics, top_params,
        board_name=None, frequency=None, frequency_b=None, overwrite_ok=False,
        testbench_type=None,
):
    board_params = boards.params[board_name]
    filenames = fusesoc_generators.get_filenames_from_core(
        work_root=directory,
        top_core_name=corename,
        top_entity_name=entityname,
        generic_sets=[generics],
        top_params=top_params,
        additional_generator=add_slvcodec_files,
        )
    if testbench_type == 'jtag':
        frequency_b = 0 if frequency_b is None else frequency_b
        files_and_ip = jtagtestbench_generator.get_files_and_ip(
            directory, filenames, entityname, generics, board_params, frequency, frequency_b)
        resolved = {}
        out_of_context = False
    elif testbench_type == 'file':
        output_path = os.path.join(directory, 'simulation_output')
        tb_fns, wrapper_fns, resolved = filetestbench_generator.prepare_files(
            directory, filenames, entityname, add_double_wrapper=True, use_vunit=False,
            dut_directory=None, default_generics=generics, default_output_path=output_path)
        files_and_ip = {
            'design_files': filenames + wrapper_fns,
            'simulation_files': tb_fns,
            'ips': [],
            'top_module': entityname + '_fromslvcodec',
            }
        out_of_context = True
    else:
        files_and_ip = {
            'design_files': filenames,
            'simulation_files': [],
            'ips': [],
            'top_module': entityname,
        }
        out_of_context = True
        resolved = {}
    p = base_project.BaseProject(
        directory=directory,
        files_and_ip=files_and_ip,
        overwrite_ok=overwrite_ok,
        )
    v = vivado_project.VivadoProject(
        project=p,
        board=board_name,
        wait_for_creation=True,
        out_of_context=out_of_context,
        frequency=frequency,
        clock_name='clk',
        )
    return v, resolved


def run_vivado_test(directory, sim_type, test_spec):
    assert sim_type in ('hdl', 'post_synthesis')
    if 'param_sets' not in test_spec:
        param_sets = [{
            'top_params': {},
            'generic_sets': test_spec['all_generics'],
            }]
    else:
        param_sets = test_spec['param_sets']
    for param_set in param_sets:
        params = param_set['top_params']
        all_generics = param_set['generic_sets']
        for generics in all_generics:
            if os.path.exists(directory):
                shutil.rmtree(directory)
            os.makedirs(directory)
            output_path = os.path.join(directory, 'simulation_output')
            proj, resolved = from_fusesoc_core(
                testbench_type='file',
                directory=directory,
                corename=test_spec['core_name'],
                entityname=test_spec['entity_name'],
                board_name='dummy',
                generics=generics,
                top_params=params,
                )
            entity = resolved['entities'][test_spec['entity_name']]
            test = test_spec['generator'](resolved, generics, params)
            first_line_repeats = 20
            if not os.path.exists(output_path):
                os.mkdir(output_path)
            n_lines = test_utils.write_input_file(
                entity, generics, test, output_path, first_line_repeats=first_line_repeats)
            runtime = '{}ns'.format(n_lines*10 + 200)
            proj.run_simulation(test_name='my_test',
                                test_bench_name=test_spec['entity_name'] + '_tb', runtime=runtime,
                                sim_type='post_synthesis')
            test_utils.check_output_file(entity, generics, test, output_path,
                                         first_line_repeats=first_line_repeats)
