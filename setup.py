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
        'vunit-hdl==2.1.1withextraparsing',
    ],
    dependency_links=[
        'git+https://github.com/benreynwar/vunit@20d0ce83a5155ef8b4ebd016702a7d7b715ef65e#egg=vunit-hdl-2.1.1withextraparsing',
    ],
)
