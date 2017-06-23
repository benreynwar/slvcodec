  function to_slvcodec (constant data: {{type}}) return std_logic_vector is
    constant W0: natural := 0;
    {% for index, name, width in indices_names_and_widths %}constant W{{index+1}}: natural := W{{index}} + {{width}};
    {% endfor %}variable slv: std_logic_vector({{type}}_slvcodecwidth-1 downto 0);
  begin
    {% for index, name, width in indices_names_and_widths %}slv(W{{index+1}}-1 downto W{{index}}) := to_slvcodec(data.{{name}});
    {% endfor %}return slv; 
  end function;

  function from_slvcodec (constant slv: std_logic_vector) return {{type}} is
    constant W0: natural := 0;
    {% for index, name, width in indices_names_and_widths %}constant W{{index+1}}: natural := W{{index}} + {{width}};
    {% endfor %}variable data: {{type}};
    variable mapped: std_logic_vector({{type}}_slvcodecwidth-1 downto 0);
  begin
    mapped := slv;
    {% for index, name, width in indices_names_and_widths %}data.{{name}} := from_slvcodec(mapped(W{{index+1}}-1 downto W{{index}})); 
    {% endfor %}return data; 
  end function;
