library ieee;
use ieee.std_logic_1164.all;

package slvcodec is

  -- std_logic_vector
  function to_slv(constant data: std_logic_vector) return std_logic_vector;
  function from_slv(constant data: std_logic_vector) return std_logic_vector;

  -- std_logic
  function to_slv(constant data: std_logic) return std_logic_vector;
  function from_slv(constant data: std_logic_vector) return std_logic;

end package;

package body slvcodec is

  -- std_logic_vector
  function to_slv(constant data: std_logic_vector) return std_logic_vector is
  begin
    return data;
  end function;

  function from_slv(constant data: std_logic_vector) return std_logic_vector is
  begin
    return data;
  end function;

  -- std_logic
  function to_slv(constant data: std_logic) return std_logic_vector is
    variable output: std_logic_vector(0 downto 0);
  begin
    output(0) := data;
    return output;
  end function;
    
  function from_slv(constant data: std_logic_vector) return std_logic is
    variable output: std_logic;
  begin
    output := data(0);
    return output;
  end function;

end package body;
