-- -*- vhdl -*- 

library ieee;
use ieee.std_logic_1164.all;

entity ClockGenerator is
  generic (CLOCK_PERIOD: Time;
           CLOCK_OFFSET: Time
           );
  port (clk: out std_logic := '0';
        endsim: in std_logic
        );
end ClockGenerator;

architecture arch of ClockGenerator is
begin
  clock_process: process
  begin
    if endsim /= '1' then
      wait for CLOCK_OFFSET;
      clk <= '0';
      wait for CLOCK_PERIOD/2;
      clk <= '1';
      wait for CLOCK_PERIOD/2-CLOCK_OFFSET;
      clk <= '0';
    else
      wait;
    end if;
  end process;      
end arch;
