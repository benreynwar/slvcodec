import logging
import os

from vunit import VUnitCLI, VUnit

basedir = os.path.abspath(os.path.dirname(__file__))
vhdldir = os.path.join(basedir, 'vhdl')


def setup_logging(level):
    '''
    Utility function for setting up logging.
    Configured for when slvcodec is being tested rather than used.
    '''
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    # Which packages do we want to log from.
    packages = ('__main__', 'slvcodec',)
    for package in packages:
        logger = logging.getLogger(package)
        logger.addHandler(ch)
        logger.setLevel(level)
    # Warning only packages
    packages = []
    for package in packages:
        logger = logging.getLogger(package)
        logger.addHandler(ch)
        logger.setLevel(logging.WARNING)
    logger.info('Setup logging at level {}.'.format(level))


def setup_vunit(argv=None):
    '''
    Sets up vunit logging and returns the VUnit object.
    '''
    args = VUnitCLI().parse_args(argv=argv)
    log_level = args.log_level
    vu = VUnit.from_args(args)
    vu.log_level = getattr(logging, log_level.upper())
    return vu
