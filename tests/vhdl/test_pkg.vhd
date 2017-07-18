use work.vhdl_type_pkg.all;

package test_pkg is

  -- t_onetofour should fail in vhdl_type_pkg;
  -- Hopefully this won't die.
  type different_array_of_onetofour is array(integer range <>) of t_onetofour;

  -- This should work.
  type differnt_array_of_data is array(integer range <>) of t_data;
      
end package;
