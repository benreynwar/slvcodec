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
        'vunit',
    ],
    dependency_links=[
        'git+git://github.com/benreynwar/vunit.git@cfebe6340f266d8c263b14bd8531ecbf54180a48#egg=vunit',
    ],
)