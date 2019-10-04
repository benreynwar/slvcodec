-- -*- vhdl -*- 

library ieee;
use ieee.std_logic_1164.all;

library std;
use std.textio.all;
use work.txt_util.all;

entity write_pipe is
  generic (FILENAME: string;
           WIDTH: positive);
  port (clk: in std_logic;
        in_data: in std_logic_vector(0 to WIDTH-1));
end entity;

architecture arch of write_pipe is
  file output_file : text;
begin

  process
    variable output_line : line;
  begin

    report "writing: opening output pipe " & FILENAME severity note;
    file_open(output_file, FILENAME, write_mode);
    report "writing: opened output pipe" severity note;
    while true loop
      wait until rising_edge(clk);
      report "writing: edge has risen width = " & integer'image(WIDTH) severity note;
      print(output_file, str(in_data));
      flush(output_file);
    end loop;
    file_close(output_file);

    wait;
  end process;

end architecture;
