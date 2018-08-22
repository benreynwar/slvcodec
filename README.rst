
slvcodec
========

slvcodec is a tool that analyzes VHDL and generates:

  * Functions to convert arbitrary VHDL types to and from std_logic_vector.

  * Generate testbenches for entities that read inputs from a file, and
    write outputs to a file.

  * Utilities so that unit tests for VHDL code can easily to be written
    in python.


Generation of functions to convert to and from std_logic_vector
---------------------------------------------------------------

Here's an example VHDL package.

.. code:: vhdl
    
    library ieee;
    use ieee.numeric_std.all;
    
    package complex is
    
      constant FIXED_WIDTH: natural := 8;
      subtype fixed_t is unsigned(FIXED_WIDTH-1 downto 0);
    
      type complex_t is record
        real: fixed_t;
        imag: fixed_t;
      end record;
    
      type array_of_complex is array(natural range <>) of complex_t;
    
    end package;

The following python script is used to generate a helper package that contains
functions to convert the types to and from std_logic_vector.

.. code:: python
          
    import os
    
    from slvcodec import filetestbench_generator
    
    
    thisdir = os.path.dirname(__file__)
    
    
    def make_slvcodec_package():
        complex_pkg_fn = os.path.join(thisdir, 'complex_pkg.vhd')
        directory = os.path.join(thisdir, 'generated')
        os.mkdir(directory)
        filetestbench_generator.add_slvcodec_files(directory, [complex_pkg_fn])
    
    
    if __name__ == '__main__':
        make_slvcodec_package()

Here is what the generated VHDL looks like.

.. code:: vhdl

    library ieee;
    use ieee.std_logic_1164.all;
    use ieee.numeric_std.all;
    use work.complex.all;
    use work.slvcodec.all;
    
    package complex_slvcodec is
    
    
      function to_slvcodec (constant data: array_of_complex) return std_logic_vector;
      function from_slvcodec (constant slv: std_logic_vector) return array_of_complex;
      constant fixed_t_slvcodecwidth: natural := fixed_width;
      constant complex_t_slvcodecwidth: natural := 2*fixed_width;
      function to_slvcodec (constant data: complex_t) return std_logic_vector;
      function from_slvcodec (constant slv: std_logic_vector) return complex_t;
    
    end package;
    
    package body complex_slvcodec is
    
      function to_slvcodec (constant data: array_of_complex) return std_logic_vector is
        constant W: natural := complex_t_slvcodecwidth;
        constant N: natural := data'length;
        variable slv: std_logic_vector(N*W-1 downto 0);
      begin
        for ii in 0 to N-1 loop
          slv((ii+1)*W-1 downto ii*W) := to_slvcodec(data(ii));
        end loop;
        return slv; 
      end function;
    
      function from_slvcodec (constant slv: std_logic_vector) return array_of_complex is
        constant W: natural := complex_t_slvcodecwidth;
        constant N: natural := slv'length/W;
        variable mapped: std_logic_vector(slv'length-1 downto 0);
        variable output: array_of_complex(N-1 downto 0);
      begin
        mapped := slv;
        for ii in 0 to N-1 loop
          output(ii) := from_slvcodec(mapped((ii+1)*W-1 downto ii*W));
        end loop;
        return output; 
      end function;
    
      function to_slvcodec (constant data: complex_t) return std_logic_vector is
        constant W0: natural := 0;
        constant W1: natural := W0 + fixed_width;
        constant W2: natural := W1 + fixed_width;
        variable slv: std_logic_vector(complex_t_slvcodecwidth-1 downto 0);
      begin
        slv(W1-1 downto W0) := to_slvcodec(data.real);
        slv(W2-1 downto W1) := to_slvcodec(data.imag);
        return slv; 
      end function;
    
      function from_slvcodec (constant slv: std_logic_vector) return complex_t is
        constant W0: natural := 0;
        constant W1: natural := W0 + fixed_width;
        constant W2: natural := W1 + fixed_width;
        variable data: complex_t;
        variable mapped: std_logic_vector(complex_t_slvcodecwidth-1 downto 0);
      begin
        mapped := slv;
        data.real := from_slvcodec(mapped(W1-1 downto W0)); 
        data.imag := from_slvcodec(mapped(W2-1 downto W1)); 
        return data; 
      end function;
    
    end package body;
    

Generation of file-based testbenches
------------------------------------

Here's an example entity that just returns the magnitude squared of a complex data type
that we defined earlier.

.. code:: vhdl
    
    library ieee;
    use ieee.numeric_std.all;
    use work.complex.all;
    
    entity complex_mag2 is
      port (
        i: in complex_t;
        o: out unsigned(FIXED_WIDTH+1-1 downto 0)
        );
    end entity;
    
    architecture arch of complex_mag2 is
    
      signal real2: signed(FIXED_WIDTH*2-1 downto 0);
      signal imag2: signed(FIXED_WIDTH*2-1 downto 0);
      signal mag2: unsigned(FIXED_WIDTH*2-1 downto 0);
      signal scaled_mag2: unsigned(FIXED_WIDTH+1-1 downto 0);
      
    begin
    
      real2 <= i.real * i.real;
      imag2 <= i.imag * i.imag;
      mag2 <= unsigned(real2) + unsigned(imag2);
    
      scaled_mag2 <= mag2(FIXED_WIDTH*2-1-1 downto FIXED_WIDTH-2);
    
      o <= scaled_mag2;
      
    end architecture;

We can use slvcodec to generate a testbench that reads input data from a file,
and writes output data to another file.

.. code:: python

    import os
    
    from slvcodec import filetestbench_generator
    
    
    thisdir = os.path.dirname(__file__)
    
    
    def make_slvcodec_package():
        complex_pkg_fn = os.path.join(thisdir, 'complex_pkg.vhd')
        directory = os.path.join(thisdir, 'generated')
        os.mkdir(directory)
        slvcodec_files = filetestbench_generator.add_slvcodec_files(directory, [complex_pkg_fn])
        return slvcodec_files
    
    
    def make_complex_mag2_testbench():
        base_filenames = [
            os.path.join(thisdir, 'complex_pkg.vhd'),
            os.path.join(thisdir, 'complex_mag2.vhd'),
            ]
        slvcodec_fns = make_slvcodec_package()
        with_slvcodec_fns = base_filenames + slvcodec_fns
        directory = os.path.join(thisdir, 'generated')
        generated_fns, generated_wrapper_fns, resolved = filetestbench_generator.prepare_files(
            directory=directory, filenames=with_slvcodec_fns,
            top_entity='complex_mag2')
        return generated_fns
    

    if __name__ == '__main__':
        make_complex_mag2_testbench()


This will generate the following VHDL testbench.

.. code:: vhdl
    
    library ieee;
    use ieee.std_logic_1164.all;
    use work.slvcodec.all;
    use ieee.numeric_std.all;
    use work.complex.all;
    use work.complex_slvcodec.all;
    
    entity complex_mag2_tb is
      generic (
        
        CLOCK_PERIOD: time := 10 ns;
        RUNNER_CFG: string;
        OUTPUT_PATH: string
      );
    end entity;
     
    architecture arch of complex_mag2_tb is
      type t_input is
    record
        i: complex_t;
    end record;
    type t_output is
    record
        o: unsigned((1+fixed_width)-1 downto 0);
    end record;
      constant t_input_slvcodecwidth: natural := 2*fixed_width;
      function to_slvcodec (constant data: t_input) return std_logic_vector;
      function from_slvcodec (constant slv: std_logic_vector) return t_input;
      function to_slvcodec (constant data: t_input) return std_logic_vector is
        constant W0: natural := 0;
        constant W1: natural := W0 + 2*fixed_width;
        variable slv: std_logic_vector(t_input_slvcodecwidth-1 downto 0);
      begin
        slv(W1-1 downto W0) := to_slvcodec(data.i);
        return slv; 
      end function;
    
      function from_slvcodec (constant slv: std_logic_vector) return t_input is
        constant W0: natural := 0;
        constant W1: natural := W0 + 2*fixed_width;
        variable data: t_input;
        variable mapped: std_logic_vector(t_input_slvcodecwidth-1 downto 0);
      begin
        mapped := slv;
        data.i := from_slvcodec(mapped(W1-1 downto W0)); 
        return data; 
      end function;
      constant t_output_slvcodecwidth: natural := (1+fixed_width);
      function to_slvcodec (constant data: t_output) return std_logic_vector;
      function from_slvcodec (constant slv: std_logic_vector) return t_output;
      function to_slvcodec (constant data: t_output) return std_logic_vector is
        constant W0: natural := 0;
        constant W1: natural := W0 + (1+fixed_width);
        variable slv: std_logic_vector(t_output_slvcodecwidth-1 downto 0);
      begin
        slv(W1-1 downto W0) := to_slvcodec(data.o);
        return slv; 
      end function;
    
      function from_slvcodec (constant slv: std_logic_vector) return t_output is
        constant W0: natural := 0;
        constant W1: natural := W0 + (1+fixed_width);
        variable data: t_output;
        variable mapped: std_logic_vector(t_output_slvcodecwidth-1 downto 0);
      begin
        mapped := slv;
        data.o := from_slvcodec(mapped(W1-1 downto W0)); 
        return data; 
      end function;
      signal input_data: t_input;
      signal output_data: t_output;
      signal input_slv: std_logic_vector(t_input_slvcodecwidth-1 downto 0);
      signal output_slv: std_logic_vector(t_output_slvcodecwidth-1 downto 0);
      signal clk: std_logic;
      signal read_clk: std_logic;
      signal write_clk: std_logic;
    begin
    
      input_data <= from_slvcodec(input_slv);
      output_slv <= to_slvcodec(output_data);
    
      file_reader: entity work.ReadFile
        generic map(FILENAME => OUTPUT_PATH & "/indata.dat",
                    PASSED_RUNNER_CFG => RUNNER_CFG,
                    WIDTH => t_input_slvcodecwidth)
        port map(clk => read_clk,
                 out_data => input_slv);
    
      file_writer: entity work.WriteFile
        generic map(FILENAME => OUTPUT_PATH & "/outdata.dat",
                    WIDTH => t_output_slvcodecwidth)
        port map(clk => write_clk,
                 in_data => output_slv);
    
      clock_generator: entity work.ClockGenerator
        generic map(CLOCK_PERIOD => CLOCK_PERIOD,
                    CLOCK_OFFSET => 0 ns
                    )
        port map(clk => clk);
    
      read_clock_generator: entity work.ClockGenerator
        generic map(CLOCK_PERIOD => CLOCK_PERIOD,
                    CLOCK_OFFSET => CLOCK_PERIOD/10
                    )
        port map(clk => read_clk);
    
      write_clock_generator: entity work.ClockGenerator
        generic map(CLOCK_PERIOD => CLOCK_PERIOD,
                    CLOCK_OFFSET => 4*CLOCK_PERIOD/10
                    )
        port map(clk => write_clk);
    
      dut: entity work.complex_mag2
        port map(
                 i => input_data.i,
    o => output_data.o
                 );
     
    end architecture;


But generating a test bench that just reads and writes the input and output data
to and from files isn't particularly useful unless we have a way of generating the
input data, and checking the output data.  Slvcodec include tools to do this
with python.

Python-based testing
--------------------

We define a python class with a ``make_input_data`` method that returns an iterable of
dictionaries specifying the input data, and a ``check_output_data`` method that receives
a list of input_data dictionaries and a list of output data dictionaries, that raises an
exeception is the output data is incorrect.

.. code:: python

    class ComplexMag2Test:
    
        def __init__(self, resolved, generics, top_params):
            # Here we're taking advantage of the fact that when the test is intialized it
            # has access to the parsed VHDL.  We use that to get the value of the constant
            # FIXED_WIDTH that is defined in complex_pkg.vhd.
            self.fixed_width = resolved['packages']['complex'].constants['fixed_width'].value()
            self.max_fixed = pow(2, self.fixed_width-1)-1
            self.min_fixed = -pow(2, self.fixed_width-1)
            self.n_data = 100
    
        def fixed_to_float(self, f):
            r = f / pow(2, self.fixed_width-2)
            return r
    
        def make_input_data(self, seed=None, n_data=3000):
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
            differences = [abs(expected - actual) for expected, actual in zip(input_float_mag2s, outputs)]
            allowed_error = 1/pow(2, self.fixed_width-2)
            assert all([d < allowed_error for d in differences])


We then use ``slvcodec.test_utils.register_test_with_vunit`` to generate an appropriate testbench and input
data file, and register the produced test with vunit.  VUnit can then be run as normal.


.. code:: python

    from slvcodec import test_utils, config
    import os
    
    if __name__ == '__main__':
        random.seed(0)
        # Initialize vunit with command line parameters.
        vu = config.setup_vunit()
        # Set up logging.
        config.setup_logging(vu.log_level)
        # Get filenames for test
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
