from setuptools import setup

setup(
    name = "slvcodec",
    packages=['slvcodec',
              ],
    package_data={'slvcodec': ['templates/*.vhd', 'vhdl/*.vhd']},
    use_scm_version = {
        "relative_to": __file__,
        "write_to": "slvcodec/version.py",
    },
    author = "Ben Reynwar",
    author_email = "ben@reynwar.net",
    description = ("slvcodec is a package of utilities for generating VHDL to convert to and from std_logic_vector, as well as utilties to create testbenches described by python."),
    license = "MIT",
    keywords = ["VHDL", "hdl", "rtl", "FPGA", "ASIC", "Xilinx", "Altera"],
    url = "https://github.com/benreynwar/slvcodec",
    install_requires=[
        'jinja2>=2.8',
        'pytest',
        'fusesoc_generators',
        'vunit-hdl==2.1.1withextraparsingb',
    ],
    dependency_links=[
        'git+https://github.com/benreynwar/fusesoc_generators@4a9787319a33f5ac6e97f4ff3cb37c9c5703bdfc#egg=fusesoc_generators-0.0.0',
        'git+https://github.com/benreynwar/vunit@4d94c37bb9328da89b2bbe8511d714391441d6dc#egg=vunit-hdl-2.1.1withextraparsingb',
    ],
)
