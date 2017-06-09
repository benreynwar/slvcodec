library ieee;
use ieee.std_logic_1164.all;

package vhdl_type_pkg is
  constant WIDTH: natural := 6;
  constant SIZE: natural := 2;

  subtype t_data is std_logic_vector(WIDTH-1 downto 0);
  subtype t_number is integer range 0 to 8;
  type array_of_data is array(integer range <>) of t_data;
  subtype t_manydata is array_of_data(SIZE-1 downto 0);

  type t_dummy is
    record
      manydata: t_manydata;
      data: t_data;
      anint: integer range 5 downto 0;
      anotherint: t_number;
      logic: std_logic;
      slv: std_logic_vector(3 downto 0);
    end record;
      
end package;
