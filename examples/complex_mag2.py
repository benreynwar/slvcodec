import random
import logging

from slvcodec import test_utils, config

logger = logging.getLogger(__name__)


class ComplexMag2Test:

    def __init__(self, resolved, generics, top_params):
        self.fixed_width = resolved['packages']['complex'].constants['fixed_width'].value()
        self.max_fixed = pow(2, self.fixed_width-1)-1
        self.min_fixed = -pow(2, self.fixed_width-1)
        self.n_data = 100

    def fixed_to_float(self, f):
        r = f / pow(2, self.fixed_width-2)
        return r

    def make_input_data(self):
        input_data = [{
            'i': {'real': random.randint(self.min_fixed, self.max_fixed),
                  'imag': random.randint(self.min_fixed, self.max_fixed)},
        } for i in range(self.n_data)]
        return input_data

    def check_output_data(self, input_data, output_data):
        inputs = [self.fixed_to_float(d['i']['real']) + self.fixed_to_float(d['i']['imag']) * 1j
                  for d in input_data]
        input_float_mag2s = [abs(v)*abs(v) for v in inputs]
        outputs = [self.fixed_to_float(d['o']) for d in output_data]
        differences = [abs(expected - actual)
                       for expected, actual in zip(input_float_mag2s, outputs)]
        allowed_error = 1/pow(2, self.fixed_width-2)
        assert all([d < allowed_error for d in differences])


def run_test():
    random.seed(0)
    # Initialize vunit with command line parameters.
    vu = config.setup_vunit()
    # Set up logging.
    config.setup_logging(vu.log_level)
    # Get filenames for test
    import os
    this_dir = os.path.dirname(os.path.realpath(__file__))
    filenames = [
        os.path.join(this_dir, 'complex_pkg.vhd'),
        os.path.join(this_dir, 'complex_mag2.vhd'),
        ]
    # Register the test with VUnit.
    test_output_directory = os.path.join(this_dir, 'generated')
    test_utils.register_test_with_vunit(
        vu=vu,
        directory=test_output_directory,
        filenames=filenames,
        top_entity='complex_mag2',
        all_generics=[{}],
        test_class=ComplexMag2Test,
        top_params={},
        )
    # Run the tests with VUnit
    vu.set_sim_option('disable_ieee_warnings', True)
    vu.main()


if __name__ == '__main__':
    run_test()
