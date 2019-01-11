-- -*- vhdl -*- 

library ieee;
use ieee.std_logic_1164.all;

library std;
use std.textio;
use work.txt_util.all;

entity WriteFile is
  generic (FILENAME: string;
           WIDTH: positive);
  port (clk: in std_logic;
        endsim: in std_logic;
        in_data: in std_logic_vector(0 to WIDTH-1));
end WriteFile;

architecture arch of WriteFile is
  file output_file : textio.text;
begin
  process
    variable output_line : textio.line;
  begin

    while true loop
      if endsim /= '1' then
        wait until rising_edge(clk);
        textio.file_open(output_file, FILENAME, append_mode);
        print(output_file, str(in_data));
        textio.file_close(output_file);
      else
        wait;
      end if;
    end loop;

    wait;
  end process;

end arch;
