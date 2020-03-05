library ieee;
use ieee.std_logic_1164.all;
use work.slvcodec.all;
{{use_clauses}}

entity {{test_name}} is
  generic (
    {{generic_params}}{% if generic_params %};{% endif %}
    CLOCK_PERIOD: time := 10 ns;
    RUNNER_CFG: string;
    OUTPUT_PATH: string
  );
end entity;
 
architecture arch of {{test_name}} is
  {{definitions}}
  signal input_data: t_input;
  signal output_data: t_output;
  signal input_slv: std_logic_vector(t_input_slvcodecwidth-1 downto 0);
  signal output_slv: std_logic_vector(t_output_slvcodecwidth-1 downto 0);
  signal clk: std_logic;
  signal read_clk: std_logic;
  signal write_clk: std_logic;
  signal endsim: std_logic;
  {{extra_definitions}}
begin
  {{extra_logic}}

  input_data <= from_slvcodec(input_slv);
  output_slv <= to_slvcodec(output_data);

  file_reader: entity work.ReadFile
    generic map(FILENAME => OUTPUT_PATH & "/indata.dat",
                PASSED_RUNNER_CFG => RUNNER_CFG,
                WIDTH => t_input_slvcodecwidth)
    port map(clk => read_clk,
             endsim => endsim,
             out_data => input_slv);

  file_writer: entity work.WriteFile
    generic map(FILENAME => OUTPUT_PATH & "/outdata.dat",
                WIDTH => t_output_slvcodecwidth)
    port map(clk => write_clk,
             endsim => endsim,
             in_data => output_slv);

  clock_generator: entity work.ClockGenerator
    generic map(CLOCK_PERIOD => CLOCK_PERIOD,
                CLOCK_OFFSET => 0 ns
                )
    port map(clk => clk, endsim => endsim);

  read_clock_generator: entity work.ClockGenerator
    generic map(CLOCK_PERIOD => CLOCK_PERIOD,
                CLOCK_OFFSET => CLOCK_PERIOD/10
                )
    port map(clk => read_clk, endsim => endsim);

  write_clock_generator: entity work.ClockGenerator
    generic map(CLOCK_PERIOD => CLOCK_PERIOD,
                CLOCK_OFFSET => 4*CLOCK_PERIOD/10
                )
    port map(clk => write_clk, endsim => endsim);

  dut: entity work.{{dut_name}}{% if dut_generics %}
    generic map(
      {{dut_generics}}
      ){% endif %}
    port map({{clk_connections}}
             {{connections}}
             );
 
end architecture;
