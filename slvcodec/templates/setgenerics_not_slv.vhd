library ieee;
use ieee.std_logic_1164.all;
use work.slvcodec.all;
{{use_clauses}}
use work.setgenerics_pkg.all;

entity {{wrapper_name}} is
  port ({% for port in wrapper_ports %}
    {{port.name}}: {{port.direction}} {{port.typ}}{% if not loop.last%};{% endif %}{% endfor %}
  );
end entity;
 
architecture arch of {{wrapper_name}} is
begin

  wrapped: entity work.{{wrapped_name}}{% if wrapped_generics %}
    generic map(
      {{wrapped_generics}}
      ){% endif %}
    port map({% for port in wrapped_ports%}{% if port in wrapper_ports %}
      {{port.name}} => {{port.name}}{% if not loop.last %},{% endif %}{% else %}{% if port.direction == "in" %}{% if port.typ.__str__() == "std_logic"%}
      {{port.name}} => '0'{% else %}
      {{port.name}} => (others => '0'){% endif %}{% if not loop.last %},{% endif %}{% endif %}{% endif %}{% endfor %}
      );
 
end architecture;
