import os
from setuptools import setup

this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name = "slvcodec",
    packages=['slvcodec', 'slvcodec.cocotb_wrapper',
              ],
    package_data={'slvcodec': ['templates/*.vhd', 'vhdl/*.vhd']},
    use_scm_version = {
        "relative_to": __file__,
        "write_to": "slvcodec/version.py",
    },
    setup_requires=['setuptools_scm'],
    author = "Ben Reynwar",
    author_email = "ben@reynwar.net",
    description = ("Utilities for generating VHDL to convert to and from std_logic_vector, as well as utilties to create testbenches described by python."),
    long_description=long_description,
    long_description_content_type='text/x-rst',
    license = "MIT",
    keywords = ["VHDL", "hdl", "rtl", "FPGA", "ASIC", "Xilinx", "Altera"],
    url = "https://github.com/benreynwar/slvcodec",
    install_requires=[
        'jinja2>=2.8',
        'pytest',
        'vunit-hdl',
        'pyyaml',
        'cocotb>=1.4.0rc1',
        'fusesoc',
    ],
)
