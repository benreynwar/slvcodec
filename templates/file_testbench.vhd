library ieee;
use ieee.std_logic_1164.all;
{{use_clauses}}

entity FileTestBench is
  generic (
    {{generic_params}}
    DATAINFILENAME: string;
    DATAOUTFILENAME: string
  );
end FileTestBench;
 
architecture arch of FileTestBench is
  {{definitions}}
  signal input_data: t_input;
  signal output_data: t_output;
  signal input_slv: std_logic_vector(t_input_width-1 downto 0);
  signal output_slv: std_logic_vector(t_output_width-1 downto 0);
  signal clk: std_logic;
  signal offset_clk: std_logic;
begin

  input_data <= from_slv(input_slv);
  output_data <= to_slv(output_slv);

  file_reader: entity work.ReadFile
    generic map(FILENAME => DATAINFILENAME,
                WIDTH => t_input_width)
    port map(clk => offset_clk,
             out_data => input_slv);

  file_writer: entity work.WriteFile
    generic map(FILENAME => DATAOUTFILENAME,
                WIDTH => t_output_width)
    port map(clk => clk,
             in_data => output_slv);

  clock_generator: entity work.ClockGenerator
    generic map(CLOCK_PERIOD => CLOCK_PERIOD,
                CLOCK_OFFSET => 0 ns
                )
    port map(clk => clk);

  offset_clock_generator: entity work.ClockGenerator
    generic map(CLOCK_PERIOD => CLOCK_PERIOD,
                CLOCK_OFFSET => CLOCK_PERIOD/10
                )
    port map(clk => offset_clk);

  dut: entity work.{{dut_name}}
    generic map(
      {{dut_generics}}
      );
    port map(clk => clk,
             {{connections}}
             );
 
end arch;
