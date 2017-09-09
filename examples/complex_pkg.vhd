library ieee;
use ieee.numeric_std.all;

package complex is

  constant FIXED_WIDTH: natural := 8;
  subtype fixed_t is signed(FIXED_WIDTH-1 downto 0);

  type complex_t is record
    real: fixed_t;
    imag: fixed_t;
  end record;

  type array_of_complex is array(natural range <>) of complex_t;

end package;
