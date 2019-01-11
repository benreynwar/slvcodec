-- -*- vhdl -*- 

library ieee;
use ieee.std_logic_1164.all;

library std;
use std.textio;
use work.txt_util.all;

entity ReadFile is
  generic (FILENAME: string;
           WIDTH: positive);
  port (clk: in std_logic;
        endsim: out std_logic := '0';
        out_data: out std_logic_vector(0 to WIDTH-1));
end ReadFile;

architecture arch of ReadFile is
  file input_file : textio.text;
  signal the_out_data: std_logic_vector(0 to WIDTH-1) := (others => '0');
begin
  out_data <= the_out_data;
  process
    variable input_line : textio.line;
    variable input_string : string(1 to WIDTH); 
    variable counter: natural := 0;
  begin

    endsim <= '0';
    
    textio.file_open(input_file, FILENAME, read_mode);

    while not textio.endfile(input_file) loop
      wait until rising_edge(clk);
      textio.readline(input_file, input_line);
      textio.read(input_line, input_string);
      the_out_data <= to_std_logic_vector(input_string);
    end loop;

    textio.file_close(input_file);

    while counter < 40 loop
      counter := counter + 1;
      wait until rising_edge(clk);
    end loop;  

    endsim <= '1';
    wait;

  end process;

end arch;
