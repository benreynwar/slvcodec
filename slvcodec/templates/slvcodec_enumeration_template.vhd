  function to_slvcodec (constant data: {{type}}) return std_logic_vector is
    variable slv: std_logic_vector({{type}}_slvcodecwidth-1 downto 0);
  begin
    case data is {% for literal in literals %}
      when {{literal}} => slv := std_logic_vector(to_unsigned({{loop.index-1}}, {{type}}_slvcodecwidth));{% endfor %}
      when others => slv := (others => 'U');
    end case;
    return slv; 
  end function;

  function from_slvcodec (constant slv: std_logic_vector) return {{type}} is
    variable pos: integer range 0 to {{n_literals}}-1;
    variable data: {{type}};
  begin
    if is_X(slv) then
      pos := 0;
    else
      pos := to_integer(unsigned(slv));
    end if;
    case pos is {% for literal in literals %}
      when {{loop.index-1}} => data := {{literal}};{% endfor %}
    end case;
    return data; 
  end function;
