-- -*- vhdl -*- 

library ieee;
use ieee.std_logic_1164.all;

library std;
use std.textio.all;
use work.txt_util.all;

entity read_pipe is
  generic (FILENAME: string; WIDTH: positive);
  port (
    clk: in std_logic;
    out_data: out std_logic_vector(0 to WIDTH-1)
    );
end entity;

architecture arch of read_pipe is
  file input_file: text;
  signal the_out_data: std_logic_vector(0 to WIDTH-1) := (others => '0');
begin

  out_data <= the_out_data;
  process
    variable input_line : line;
    variable input_string : string(1 to WIDTH); 
    variable counter: natural := 0;
    variable start_index: natural := 0;
  begin
    report "reading: opening file" severity note;
    file_open(input_file, FILENAME, read_mode);
    report "reading: opened file" severity note;
    --while not textio.endfile(input_file) loop
    while true loop
      wait until rising_edge(clk);
      report "reading: got edge. trying to read line" severity note;
      readline(input_file, input_line);
      read(input_line, input_string);
      the_out_data <= to_std_logic_vector(input_string);
      report "reading: read data" severity note;
      assert input_line'length = 0 report "Syncing problem in named pipe." severity failure;
    end loop;

    file_close(input_file);

    while counter < 40 loop
      counter := counter + 1;
      wait until rising_edge(clk);
    end loop;  

  end process;

end architecture;
