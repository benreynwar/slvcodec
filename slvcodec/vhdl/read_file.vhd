-- -*- vhdl -*- 

library ieee;
use ieee.std_logic_1164.all;

library vunit_lib;
context vunit_lib.vunit_context;

library std;
use std.textio;
use work.txt_util.all;

entity ReadFile is
  generic (FILENAME: string;
           PASSED_RUNNER_CFG: string;
           WIDTH: positive);
  port (clk: in std_logic;
        endsim: in std_logic;
        out_data: out std_logic_vector(0 to WIDTH-1));
end ReadFile;

architecture arch of ReadFile is
  file input_file: textio.text;
  signal the_out_data: std_logic_vector(0 to WIDTH-1) := (others => '0');
begin
  out_data <= the_out_data;
  process
    variable input_line : textio.line;
    variable input_string : string(1 to WIDTH); 
    variable counter: natural := 0;
  begin
    if PASSED_RUNNER_CFG /= "" then
      test_runner_setup(runner, PASSED_RUNNER_CFG);
    end if;

    textio.file_open(input_file, FILENAME, read_mode);

    while not textio.endfile(input_file) loop
      wait until rising_edge(clk);
      textio.readline(input_file, input_line);
      textio.read(input_line, input_string);
      the_out_data <= to_std_logic_vector(input_string);
      assert input_line'length = 0 report "Unexpected line length in input file." severity failure;
    end loop;

    textio.file_close(input_file);

    while counter < 40 loop
      counter := counter + 1;
      wait until rising_edge(clk);
    end loop;  

    if PASSED_RUNNER_CFG /= "" then
      test_runner_cleanup(runner);
    end if;
  end process;

end arch;
