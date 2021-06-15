import os
import subprocess
import logging
import filecmp

import yaml

logger = logging.getLogger(__name__)


class Launcher:
    """
    Old Launcher taken from fusesoc.
    """
    def __init__(self, cmd, args=[], shell=False, cwd=None, stderr=None, stdout=None, errormsg=None,
                 env=None):
        self.cmd = cmd
        self.args = args
        self.shell = shell
        self.cwd = cwd
        self.stderr = stderr
        self.stdout = stdout
        self.errormsg = errormsg
        self.env = env

    def run(self):
        logger.debug(self.cwd)
        logger.debug('    ' + str(self))
        try:
            subprocess.check_call([self.cmd] + self.args,
                                  cwd=self.cwd,
                                  env=self.env,
                                  shell=self.shell,
                                  stderr=self.stderr,
                                  stdout=self.stdout,
                                  stdin=subprocess.PIPE),
        except FileNotFoundError:
            raise RuntimeError("Command '" + self.cmd + "' not found. Make sure it is in $PATH")
        except subprocess.CalledProcessError:
            if self.stderr is None:
                output = "stderr"
            else:
                output = self.stderr.name
                with open(self.stderr.name, 'r') as f:
                    logger.error(f.read())

            if self.errormsg is None:
                self.errormsg = ('"' + str(self) + '" exited with an error code.\nERROR: See ' + output + ' for details.')
            raise RuntimeError(self.errormsg)

    def __str__(self):
        return ' '.join([self.cmd] + self.args)


def set_fusesoc_top_params(top_params, top_params_filename=None):
    top_params_filename = os.environ['FUSESOC_TOP_PARAMS']
    with open(top_params_filename, 'w') as f:
        content = yaml.dump(top_params)
        f.write(content)


def get_fusesoc_top_params():
    top_params_filename = os.environ['FUSESOC_TOP_PARAMS']
    with open(top_params_filename, 'r') as f:
        top_params = yaml.load(f)
    return top_params


def generate_core(working_directory, core_name, parameters, config_filename=None, tool='vivado',
                  verbose=False
                  ):
    old_params = os.environ.get('FUSESOC_TOP_PARAMS', None)
    if parameters is not None:
        top_params_filename = os.path.join(working_directory, 'top_params.yaml')
        os.environ['FUSESOC_TOP_PARAMS'] = os.path.abspath(top_params_filename)
        set_fusesoc_top_params(parameters)
    cmd = ['fusesoc']
    if verbose:
        cmd += ['--verbose']
    if config_filename:
        cmd += ['--config', config_filename]
    cmd += ['run', '--target', 'default', '--tool', tool, '--setup', core_name]

    subprocess.call(cmd, cwd=working_directory)

    output_dir = os.path.join(
        working_directory, 'build', '{}_0'.format(core_name), 'default-vivado')
    if not os.path.exists(output_dir):
        output_dir = os.path.join(
            working_directory, 'build', '{}_0'.format(core_name), 'bld-vivado')
    yaml_filename = os.path.join(output_dir, '{}_0.eda.yml'.format(core_name))
    with open(yaml_filename, 'r') as f:
        data = yaml.load(f.read(), Loader=yaml.Loader)
    base_filenames = [f['name'] for f in data['files']]
    filenames = [f if f[0] == '/' else
                 os.path.abspath(os.path.join(output_dir, f)) for f in base_filenames]
    # Sometimes there seem to be repeats
    # This is either a bug in fusesoc or in our core files.
    # Filter them out.
    # FIXME: This is an ugly patch over a nasty problem.
    filtered_filenames = []
    basenames = {}
    for fn in filenames:
        bn = os.path.basename(fn)
        if fn not in filtered_filenames:
            if bn in basenames:
                logger.warning('Two files with the same name: {}, {}'.format(fn, basenames[bn]))
                if not filecmp.cmp(fn, basenames[bn]):
                    logger.warning('Two files with the same name but different contents: {}, {}'.format(fn, basenames[bn]))
                    filtered_filenames.append(fn)
            else:
                basenames[bn] = fn
                filtered_filenames.append(fn)

    if old_params is not None:
        os.environ['FUSESOC_TOP_PARAMS'] = old_params
    return filtered_filenames


def compile_src_files(work_root, src_files):
    '''
    Compiles src files using ghdl.
    '''
    logger.debug('compiling src files {}'.format([src_files]))
    for file_name in src_files:
        if file_name.split('.')[-1] in ('vhd', 'vhdl'):
            args = ['-a', '--std=08']
            args += [file_name]
            logger.debug('Compiling {}'.format(file_name))
            Launcher('ghdl', args,
                     cwd=work_root,
                     errormsg="Failed to analyze {}".format(file_name)).run()


def elaborate(work_root, top_name):
    '''
    Elaborate the design using ghdl.
    '''
    Launcher('ghdl', ['-e', '--std=08']+[top_name],
             cwd=work_root,
             errormsg="Failed to elaborate {}".format(top_name)).run()


def run_single(work_root, top_name, top_generics):
    '''
    Run a single ghdl simulation and return a list of errors.
    Used to determine which generics are required by generated entities.
    '''
    stderr_fn = os.path.join(work_root, 'stderr_0')
    stdout_fn = os.path.join(work_root, 'stdout_0')
    args = ['-r', '--std=08']
    args += [top_name]
    for generic_name, generic_value in top_generics.items():
        args.append('-g{}={}'.format(generic_name, generic_value))
    try:
        with open(stderr_fn, 'w') as stderr_f:
            with open(stdout_fn, 'w') as stdout_f:
                Launcher('ghdl', args,
                         cwd=work_root,
                         stdout=stdout_f,
                         stderr=stderr_f,
                         errormsg="Simulation failed").run()
    except RuntimeError as error:
        with open(stdout_fn, 'r') as stdout_f:
            lines = list(stdout_f)
            for line_index, line in enumerate(lines):
                if ('ghdl:error' in line) or ('assertion failure' in line):
                    logger.error(line)
                else:
                    logger.debug(line)
        raise error
    with open(stderr_fn, 'r') as stderr_f:
        error_lines = stderr_f.readlines()
    with open(stdout_fn, 'r') as stdout_f:
        error_lines += stdout_f.readlines()
    return error_lines


def extract_generics(error_lines):
    '''
    Parse the errors output from ghdl to determine what generics
    are required by the generators.
    '''
    ds = []
    for line in error_lines:
        d = {}
        pieces = line.split('Generator')
        if len(pieces) == 2:
            params = pieces[1].split()
            for param in params:
                key, value = param.split('=')
                assert key not in d
                d[key] = value
                ds.append(d)
    return ds


def run(work_root, top_name, all_top_generics, generator_d):
    '''
    Run the design using ghdl.
    The purpose is to see which modules are used with which generic parameters
    so that we can call the generic parameters appropriately.
    '''
    updated_generators = False
    for top_generics in all_top_generics:
        error_lines = run_single(work_root, top_name, top_generics)
        ds = extract_generics(error_lines)
        for d in ds:
            fd = frozenset((k, v) for k, v in d.items())
            if d['name'] not in generator_d:
                generator_d[d['name']] = []
            g = generator_d[d['name']]
            g.append(d)
            updated_generators = True
    return updated_generators


def compile_elab_and_run(core_name, work_root, all_top_generics, top_params, top_name,
                         generator_d, additional_generator=None, config_filename=None,
                         other_files=None, verbose=False):
    '''
    Run the generators, compile and elaborate the files, and run ghdl
    to see if any of the generators were missing generics.
    '''
    if other_files is None:
        other_files = []
    file_names = generate_core(work_root, core_name, top_params, config_filename=config_filename,
                               tool='vivado', verbose=verbose)
    if additional_generator is not None:
        file_names = additional_generator(work_root, file_names)
    compile_src_files(work_root, other_files + file_names)
    if top_name is not None:
        elaborate(work_root, top_name)
        found_new_parameters = run(
            work_root, top_name, all_top_generics, generator_d)
    else:
        found_new_parameters = False
    return file_names, found_new_parameters


def generate_core_iteratively(core_name, work_root, all_top_generics, top_params, top_name,
                              additional_generator=None, config_filename=None, other_files=None,
                              verbose=False):
    found_new_parameters = True
    elaboration_params = {}
    top_params['elaboration_params'] = elaboration_params
    iteration_count = 0
    while found_new_parameters:
        if iteration_count > 5:
            raise RuntimeError('Too many iterations to generator core.')
        filenames, found_new_parameters = compile_elab_and_run(
            core_name, work_root, all_top_generics, top_params, top_name,
            elaboration_params, additional_generator, config_filename,
            other_files=other_files, verbose=verbose,
        )
        iteration_count += 1
    return filenames
