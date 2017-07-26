library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

package vhdl_type_pkg is
  -- Use half width to make sure that one constant can depend on another
  -- in same package.
  constant HALF_WIDTH: natural := 3;
  constant WIDTH: natural := 2 *
                             HALF_WIDTH;
  constant SIZE: natural := 2;

  -- Currently slvcodec cannot generate converter functions for integer.
  subtype t_onetofour is integer range 1 to 4;
  -- So hopefully it does not try for an array of them either.
  type array_of_onetofour is array(integer range <>) of t_onetofour;

  -- Make sure unsigned either works, or fails properly.
  subtype t_anunsigned is unsigned(5 downto 0);
  type array_of_unsigned is array(integer range <>) of t_anunsigned;
  type array_of_array_of_unsigned is array(5 downto 0) of array_of_unsigned(3 downto 0);

  -- Make sure signed either works, or fails properly.
  subtype t_asigned is signed(5 downto 0);
  type array_of_signed is array(integer range <>) of t_asigned;
  type array_of_array_of_signed is array(5 downto 0) of array_of_signed(3 downto 0);

  subtype t_data is std_logic_vector(WIDTH-1 downto 0);
  type array_of_data is array(integer range <>) of t_data;
  subtype t_manydata is array_of_data(SIZE-1 downto 0);

  type t_dummy is
    record
      manydata: t_manydata;
      data: t_data;
      logic: std_logic;
      slv: std_logic_vector(3 downto 0);
    end record;
      
end package;
