library ieee;
use ieee.std_logic_1164.all;
use work.slvcodec.all;
{{use_clauses}}

entity formal_wrapper is
  port ({% for port in ports %}
    {{port.name}}: {{port.direction}} {{port.typ}}{% if not loop.last%};{% endif %}{% endfor %}
  );
end entity;
 
architecture arch of formal_wrapper is
  signal has_reset: std_logic;
begin

  dut: entity work.{{dut_name}}{% if wrapped_generics %}
    generic map(
      {{wrapped_generics}}
      ){% endif %}
    port map({% for port in ports%}
      {{port.name}} => {{port.name}}{% if not loop.last %},{% endif %}{% endfor %}
      );
          
  process(clk)
  begin
    if rising_edge(clk) then
      if reset = '1' then
        has_reset <= '1';
      end if;
      if has_reset = '1' then
        assert input_assertions = (others => (others => '0'));
        assert output_assertions = (others => (others => '0'));
      end if;
    end if;
  end process;
 
end architecture;
