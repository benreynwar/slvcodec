library ieee;
use ieee.std_logic_1164.all;
use work.slvcodec.all;
{{use_clauses}}

package setgenerics_pkg is{% for name, typ,  value in generics %}
  constant {{name}}: {{typ}} := {{value}};{% endfor %}
end package;
