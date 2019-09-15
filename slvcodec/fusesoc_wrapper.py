import os
import yaml
import subprocess


def generate_core(working_directory, core_name, parameters, config_filename=None, tool='vivado'):
    cmd = ['fusesoc', '--verbose',]
    if config_filename:
        cmd += ['--config', config_filename]
    cmd += ['run', '--tool', tool, '--setup', core_name]

    subprocess.call(cmd, cwd=working_directory)

    output_dir = os.path.join(
        working_directory, 'build', '{}_0'.format(core_name), 'default-vivado')
    yaml_filename = os.path.join(output_dir, '{}_0.eda.yml'.format(core_name))
    with open(yaml_filename, 'r') as f:
        data = yaml.load(f.read(), Loader=yaml.Loader)
    base_filenames = [f['name'] for f in data['files']]
    filenames = [f if f[0] == '/' else
                 os.path.abspath(os.path.join(output_dir, f)) for f in base_filenames]
    return filenames
