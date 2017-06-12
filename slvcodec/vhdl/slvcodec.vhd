library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.math_real.all;

package slvcodec is

  function slvcodec_logceil(constant v: integer) return integer;

  -- std_logic_vector
  function to_slvcodec(constant data: std_logic_vector) return std_logic_vector;
  function from_slvcodec(constant data: std_logic_vector) return std_logic_vector;

  -- std_logic
  function to_slvcodec(constant data: std_logic) return std_logic_vector;
  function from_slvcodec(constant data: std_logic_vector) return std_logic;

  -- unsigned
  function to_slvcodec(constant data: unsigned) return std_logic_vector;
  function from_slvcodec(constant data: std_logic_vector) return unsigned;
  
  -- signed
  function to_slvcodec(constant data: signed) return std_logic_vector;
  function from_slvcodec(constant data: std_logic_vector) return signed;

end package;

package body slvcodec is

  function slvcodec_logceil(constant v: integer) return integer is
  begin
    if (v = 0) then
      return 1;
    elsif (v <= 2) then
      return 1;
    elsif (v <= 4) then
      return 2;
    elsif (v <= 8) then
      return 3;
    elsif (v <= 16) then
      return 4;
    elsif (v <= 32) then
      return 5;
    elsif (v <= 64) then
      return 6;
    elsif (v <= 128) then
      return 7;
    elsif (v <= 256) then
      return 8;
    elsif (v <= 512) then
      return 9;
    elsif (v <= 1024) then
      return 10;
    elsif (v <= 2048) then
      return 11;
    elsif (v <= 4096) then
      return 12;
    else
      return integer(ceil(log2(real(v))));
    end if;
  end function;
  
  -- std_logic_vector
  function to_slvcodec(constant data: std_logic_vector) return std_logic_vector is
    variable mapped: std_logic_vector(data'length-1 downto 0);
  begin
      mapped := data;
      return mapped;
  end function;

  function from_slvcodec(constant data: std_logic_vector) return std_logic_vector is
    variable mapped: std_logic_vector(data'length-1 downto 0);
  begin
    mapped := data;
    return mapped;
  end function;

  -- std_logic
  function to_slvcodec(constant data: std_logic) return std_logic_vector is
    variable output: std_logic_vector(0 downto 0);
  begin
    output(0) := data;
    return output;
  end function;
    
  function from_slvcodec(constant data: std_logic_vector) return std_logic is
    variable mapped: std_logic_vector(0 downto 0);
    variable output: std_logic;
  begin
    mapped := data;
    output := mapped(0);
    return output;
  end function;

  -- unsigned
  function to_slvcodec(constant data: unsigned) return std_logic_vector is
    variable mapped: std_logic_vector(data'length-1 downto 0);
  begin
    mapped := std_logic_vector(data);
    return mapped;
  end function;

  function from_slvcodec(constant data: std_logic_vector) return unsigned is
    variable mapped: unsigned(data'length-1 downto 0);
  begin
      mapped := unsigned(data);
      return mapped;
  end function;

  -- signed
  function to_slvcodec(constant data: signed) return std_logic_vector is
    variable mapped: std_logic_vector(data'length-1 downto 0);
  begin
    mapped := std_logic_vector(data);
    return mapped;
  end function;

  function from_slvcodec(constant data: std_logic_vector) return signed is
    variable mapped: signed(data'length-1 downto 0);
  begin
      mapped := signed(data);
      return mapped;
  end function;

end package body;
