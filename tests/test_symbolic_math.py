from slvcodec import symbolic_math as sm


def test_substitute():
    string = 'fish + 3 * bear * shark / house'
    simplified = sm.parse_and_simplify(string)
    substituted = sm.make_substitute_function({
        'fish': 2,
        'bear': 4,
        'shark': 3,
        'house': 2,
        })(simplified)
    final = sm.simplify(substituted)
    assert final == 2 + 3 * 4 * 3 / 2


def test_constant_list():
    string = '3 * (fish + 6) - 2 * bear - fish'
    simplified = sm.parse_and_simplify(string)
    constants = sm.get_constant_list(simplified)
    assert constants == set(['fish', 'bear'])


def test_empty_constant_list():
    string = '3 * 12'
    simplified = sm.parse_and_simplify(string)
    constants = sm.get_constant_list(simplified)
    assert constants == set()


def test_simplifications():
    ins_and_outs = (
        ('fish + 8*bear + 2 * (fish - bear)',
         ('(3*fish+6*bear)', '(6*bear+3*fish)')),
        ('4 + (4 - 4) * 2 - 3', ('1',)),
        ('7 * 7', ('49',)),
        ('2 * (3 + 5)', ('16',)),
        ('logceil(5+3)-2', ('1',)),
        ('1 + 1', ('2',)),
        ('(logceil(5*4)-1)+1-0', ('5',)),
        ('3 * 2 / fish / (3 / 4)', ('8/fish', '8*1/fish')),
        ('fish + 1 - 1', ('fish',)),
        ('(fish + 1) - 1', ('fish',)),
        ('fish + 2 * fish', ('3*fish',)),
        )
    for in_string, expected_strings in ins_and_outs:
        simplified = sm.parse_and_simplify(in_string)
        out_string = sm.str_expression(simplified)
        assert out_string in expected_strings
