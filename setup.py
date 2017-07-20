from setuptools import setup

setup(
    name = "slvcodec",
    packages=['slvcodec',
              ],
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
        'vunit-hdl==2.0.2withextraparsing',
    ],
    dependency_links=[
        'git+https://github.com/benreynwar/vunit.git@0f309a5a0b7ff87a9dd88e94b54961d461b56053#egg=vunit-hdl-2.0.2withextraparsing',
    ],
)
