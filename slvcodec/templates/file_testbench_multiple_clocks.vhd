library ieee;
use ieee.std_logic_1164.all;
use work.slvcodec.all;
{{use_clauses}}

entity {{test_name}} is
  generic (
    {{generic_params}}{% if generic_params %};{% endif %}{% for clock_name, clock_period, clock_offset, any_signals in clock_infos %}
    {{clock_name}}_PERIOD: time := {{clock_period}};
    {{clock_name}}_OFFSET: time := {{clock_offset}};{% endfor %}
    RUNNER_CFG: string;
    OUTPUT_PATH: string
  );
end entity;
 
architecture arch of {{test_name}} is
  {{definitions}}{% for clock_name, clock_period, clock_offset, any_signals in clock_infos %}
  signal {{clock_name}}_clk: std_logic;{% if any_signals %}
  signal {{clock_name}}_input_data: t_{{clock_name}}_inputs;
  signal {{clock_name}}_output_data: t_{{clock_name}}_outputs;
  signal {{clock_name}}_input_slv: std_logic_vector(t_{{clock_name}}_inputs_slvcodecwidth-1 downto 0);
  signal {{clock_name}}_output_slv: std_logic_vector(t_{{clock_name}}_outputs_slvcodecwidth-1 downto 0);
  signal {{clock_name}}_read_clk: std_logic;
  signal {{clock_name}}_write_clk: std_logic;{% endif %}
  {% endfor %}
  signal endsim: std_logic;
begin
  {% for clock_name, clock_period, clock_offset, any_signals in clock_infos %}
  {% if any_signals %}
  {{clock_name}}_input_data <= from_slvcodec({{clock_name}}_input_slv);
  {{clock_name}}_output_slv <= to_slvcodec({{clock_name}}_output_data);

  file_reader_{{clock_name}}: entity work.ReadFile
    generic map(FILENAME => OUTPUT_PATH & "/indata_{{clock_name}}.dat",
                PASSED_RUNNER_CFG => {% if loop.index == 1 %}RUNNER_CFG{% else %}""{% endif %},
                WIDTH => t_{{clock_name}}_inputs_slvcodecwidth)
    port map(clk => {{clock_name}}_read_clk,
             endsim => endsim,
             out_data => {{clock_name}}_input_slv);

  file_writer_{{clock_name}}: entity work.WriteFile
    generic map(FILENAME => OUTPUT_PATH & "/outdata_{{clock_name}}.dat",
                WIDTH => t_{{clock_name}}_outputs_slvcodecwidth)
    port map(clk => {{clock_name}}_write_clk,
             endsim => endsim,
             in_data => {{clock_name}}_output_slv);

  read_clock_generator_{{clock_name}}: entity work.ClockGenerator
    generic map(CLOCK_PERIOD => {{clock_name}}_PERIOD,
                CLOCK_OFFSET => {{clock_name}}_OFFSET+{{clock_name}}_PERIOD/10
                )
    port map(clk => {{clock_name}}_read_clk, endsim => endsim);

  write_clock_generator_{{clock_name}}: entity work.ClockGenerator
    generic map(CLOCK_PERIOD => {{clock_name}}_PERIOD,
                CLOCK_OFFSET => {{clock_name}}_OFFSET+4*{{clock_name}}_PERIOD/10
                )
    port map(clk => {{clock_name}}_write_clk, endsim => endsim);
  {% endif %}

  clock_generator_{{clock_name}}: entity work.ClockGenerator
    generic map(CLOCK_PERIOD => {{clock_name}}_PERIOD,
                CLOCK_OFFSET => {{clock_name}}_OFFSET
                )
    port map(clk => {{clock_name}}_clk, endsim => endsim);
  {% endfor %}

  dut: entity work.{{dut_name}}{% if dut_generics %}
    generic map(
      {{dut_generics}}
      ){% endif %}
    port map({{clk_connections}}
             {{connections}}
             );
 
end architecture;
