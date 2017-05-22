library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.vhdl_type_pkg.all;

entity dummy is
  generic (
    LENGTH: natural := 3
    );
  port (
    clk: in std_logic;
    reset: in std_logic;
    i_valid: in std_logic;
    i_dummy: in t_dummy;
    o_data: out array_of_data(LENGTH-1 downto 0)
    );
end entity;

architecture arch of dummy is
begin
  o_data <= (others => (others => '0'));
end architecture;

