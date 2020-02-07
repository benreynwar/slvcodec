library ieee;
use ieee.std_logic_1164.all;
use work.slvcodec.all;
{{use_clauses}}

package formal_pkg is
  {% for generic in generics %}constant {{generic.name}}: {{generic.type}} := {{generic.value}};
  {% endfor %}
end package;
