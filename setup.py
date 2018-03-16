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
        'pyvivado',
        'vunit-hdl',
        'axilent==0.0.0',
    ],
    dependency_links=[
        'git+https://github.com/benreynwar/fusesoc_generators@9a374ae8fdfdbe0f1448d7973783464614990d9c#egg=fusesoc_generators-0.0.0',
        'git+https://github.com/benreynwar/pyvivado@680364d2fbd04679ef06ea229702e0e6e5394af3#egg=pyvivado-0.0.0',
        'git+https://github.com/benreynwar/axilent@963c6824f2fdbd2a3beaef2682fb7461ddcb5a86#egg=axilent-0.0.0',
    ],
)
