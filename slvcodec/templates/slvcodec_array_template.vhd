  function to_slvcodec (constant data: {{type}}) return std_logic_vector is
    constant W: natural := {{subtype_width}};
    constant N: natural := data'length;
    variable slv: std_logic_vector(N*W-1 downto 0);
  begin
    for ii in 0 to N-1 loop
      slv((ii+1)*W-1 downto ii*W) := to_slvcodec(data(ii));
    end loop;
    return slv; 
  end function;

  function from_slvcodec (constant slv: std_logic_vector) return {{type}} is
    constant W: natural := {{subtype_width}};
    constant N: natural := slv'length/W;
    variable mapped: std_logic_vector(slv'length-1 downto 0);
    variable output: {{type}}{% if unconstrained %}(N-1 downto 0){% endif %};
  begin
    mapped := slv;
    for ii in 0 to N-1 loop
      output(ii) := from_slvcodec(mapped((ii+1)*W-1 downto ii*W));
    end loop;
    return output; 
  end function;
