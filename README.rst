
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

Example entity.

Example python script.

Example generated test bench.

Python-based testing
--------------------

Example python test
