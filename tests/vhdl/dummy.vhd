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
    -- the input stream
    i_valid: in std_logic;
    i_dummy: in t_dummy;
    -- the output stream
    o_data: out array_of_data(LENGTH-1 downto 0);
    i_datas: in array_of_data(2 downto 0);
    o_firstdata: out t_data;
    o_firstdatabit: out std_logic
    );
end entity;

architecture arch of dummy is
begin
  o_data <= (others => (others => '0'));
  o_firstdata <= i_datas(0);
  o_firstdatabit <= i_datas(0)(0);
end architecture;

