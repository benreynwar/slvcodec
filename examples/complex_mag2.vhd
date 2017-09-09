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
