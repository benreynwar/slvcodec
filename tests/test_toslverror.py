import pytest

from slvcodec import typs, vhdl_parser

SIMPLE_PACKAGE = '''
library ieee;
use ieee.std_logic_1164.all;

package SimplePackage is
  constant DATA_SIZE: natural := 6;
  subtype data_t is std_logic_vector(DATA_SIZE-1 downto 4);
  type array_of_data_t is array(natural range <>) of data_t;

  type mixture_t is record
    color: std_logic_vector(3 downto 0);
    is_happy: std_logic;
  end record;
  type array_of_mixture_t is array(natural range <>) of mixture_t;

end package;
'''

SIMPLE_ENTITY = '''
library ieee;
use ieee.std_logic_1164.all;

use work.SimplePackage.all;

entity SimplePorts is
  port (
    i_valid: in std_logic;
    i_data: in array_of_data_t(5 downto 0);
    i_mixtures: in array_of_mixture_t(1 downto 0);
    o_valid: out std_logic;
    o_data: out array_of_data_t(5 downto 0)
  );
end entity;

architecture arch of SimplePorts is
begin
  o_valid <= i_valid;
  o_data <= i_data;
end architecture;
'''


def test_toslverrors():
    parsed_package = vhdl_parser.parse_package_string(SIMPLE_PACKAGE)
    parsed_entity = vhdl_parser.parse_entity_string(SIMPLE_ENTITY)
    resolved_entities, resolved_packages = vhdl_parser.resolve_entities_and_packages(
        [parsed_entity], [parsed_package])
    resolved_entity = resolved_entities['simpleports']
    # Send i_data=0.
    # This is invalid since i_data expects a list of values so we expect an
    # exception to get raised telling us which entity and port is causing the
    # problem.
    with pytest.raises(typs.ToSlvError) as slv_error:
        resolved_entity.inputs_to_slv({
            'i_valid': 0,
            'i_data': 0,
        }, generics={})
    message = slv_error.value.args[0]
    assert all([s in message.lower() for s in ('simpleports', 'i_data')])
    # Given a nonexistent port name we should get an exception.
    with pytest.raises(typs.ToSlvError) as slv_error:
        resolved_entity.inputs_to_slv({
            'i_non_existent_port_name': 0,
            'i_data': [0]*6,
        }, generics={})
    message = slv_error.value.args[0]
    assert all([s in message.lower() for s in ('simpleports', 'i_non_existent_port_name')])
    # Here we have the wrong number of records in the list.
    with pytest.raises(typs.ToSlvError) as slv_error:
        resolved_entity.inputs_to_slv({
            'i_mixtures': [],
        }, generics={})
    message = slv_error.value.args[0]
    assert all([s in message.lower() for s in ('simpleports', 'i_mixtures', 'length')])
    # Here we have an invalid record element.
    with pytest.raises(typs.ToSlvError) as slv_error:
        resolved_entity.inputs_to_slv({
            'i_mixtures': [{}, {'is_happy': 1, 'is_sad': 0}],
        }, generics={})
    message = slv_error.value.args[0]
    assert all([s in message.lower() for s in ('simpleports', 'i_mixtures', 'is_sad', 'mixture_t')])
    # An element of a record is too large.
    with pytest.raises(typs.ToSlvError) as slv_error:
        resolved_entity.inputs_to_slv({
            'i_mixtures': [{}, {'is_happy': 1, 'color': 16}],
        }, generics={})
    message = slv_error.value.args[0]
    assert all([s in message.lower() for s in (
        'simpleports', 'i_mixtures', 'mixture_t', 'color', '16', '15')])


if __name__ == '__main__':
    test_toslverrors()
