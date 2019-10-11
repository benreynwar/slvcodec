'''
This module contains functions for converting to and from different
representations of signed and unsigned numbers.
'''


def list_of_uints_to_uint(list_of_uints, width):
    '''
    Convert a list of unsigned integers into a single unsigned integer.

    Args:
        `list_of_uints`: The list of integers.
        `width`: The width of each individual integer.

    >>> # Check that first is the least significant.
    >>> list_of_uints_to_uint(list_of_uints=[1, 0, 0], width=1)
    1
    >>> list_of_uints_to_uint(list_of_uints=[0, 0, 1], width=1)
    4
    >>> # Check for width of 2.
    >>> list_of_uints_to_uint(list_of_uints=[3, 2, 1], width=2)
    27
    '''
    if None in list_of_uints:
        output = None
    else:
        output = 0
        f = pow(2, width)
        for v in reversed(list_of_uints):
            assert v < f
            output += v
            output *= f
        output //= f
    return output


def uint_to_list_of_uints(uint, size, width):
    '''
    Convert an unsigned integer into a list of unsigned integers.

    Args:
        `uint`: the input unsigned integer
        `width`: The width of each individual unsigned integer.
        `size`: The number of items in the produced list.

    >>> uint_to_list_of_uints(5, size=4, width=1)
    [1, 0, 1, 0]
    >>> uint_to_list_of_uints(27, size=3, width=2)
    [3, 2, 1]
    '''
    if uint is None:
        output = [None] * size
    else:
        assert uint >= 0
        residual = uint
        f = pow(2, width)
        output = []
        for i in range(size):
            output.append(residual % f)
            residual = residual >> width
        assert residual == 0
    return output


def sint_to_uint(sint, width):
    '''
    Convert a signed integer to an unsigned integer.

    >>> sint_to_uint(-1, width=2)
    3
    >>> sint_to_uint(-2, width=3)
    6
    '''
    if sint is None:
        uint = None
    elif sint < 0:
        uint = sint + pow(2, width)
    else:
        uint = sint
    if uint < 0:
        print(sint, width, uint)
    assert uint >= 0
    return uint


def uint_to_sint(uint, width):
    '''
    Convert an unsigned integer to a signed integer.

    >>> uint_to_sint(3,  width=2)
    -1
    >>> uint_to_sint(3, width=3)
    3
    '''
    if uint is None:
        sint = None
    elif uint > pow(2, width-1)-1:
        sint = uint - pow(2, width)
    else:
        sint = uint
    return sint


def list_of_sints_to_uint(list_of_sints, width):
    '''
    Convert a list of signed integers to an unsigned integer.

    >>> list_of_sints_to_uint(list_of_sints=[-1, 0, 0], width=2)
    3
    >>> list_of_sints_to_uint(list_of_sints=[0, 0, -1], width=2)
    48
    '''
    if None in list_of_sints:
        uint = None
    else:
        list_of_uints = [sint_to_uint(sint, width) for sint in list_of_sints]
        uint = list_of_uints_to_uint(list_of_uints, width)
    return uint


def uint_to_list_of_sints(uint, size, width):
    '''
    Convert an unsigned integer to a list of signed integers.

    >>> uint_to_list_of_sints(48, size=3, width=2)
    [0, 0, -1]
    '''
    if uint is None:
        list_of_sints = None
    else:
        list_of_uints = uint_to_list_of_uints(uint, size, width)
        list_of_sints = [uint_to_sint(uint, width) for uint in list_of_uints]
    return list_of_sints


def sint_to_list_of_uints(sint, size, width):
    '''
    Convert a signed integer to a list of unsigned integers.

    >>> sint_to_list_of_uints(-1, size=3, width=1)
    [1, 1, 1]
    '''
    if sint is None:
        list_of_uints = None
    else:
        uint = sint_to_uint(sint, size*width)
        list_of_uints = uint_to_list_of_uints(uint=uint, size=size, width=width)
    return list_of_uints


def slv_to_uint(slv):
    '''
    Convert a string of '0' and '1' to an unsigned integer.

    >>> slv_to_uint('001')
    1
    >>> slv_to_uint('1010')
    10
    '''
    total = 0
    f = 1
    for ch in reversed(slv):
        if ch not in ('0', '1'):
            total = None
        if total is not None:
            if ch == '1':
                total += f
            f *= 2
    return total


def uint_to_slv(uint, width, allow_undefined=True):
    '''
    Convert an unsigned integer to a string of '0' and '1'.

    >>> uint_to_slv(10, width=6)
    '001010'
    >>> uint_to_slv(3, width=3)
    '011'
    '''
    if uint is None:
        slv = 'U' * width
        assert allow_undefined
    else:
        bits = []
        for w in range(width):
            bits.append('1' if uint % 2 else '0')
            uint //= 2
        slv = ''.join(reversed(bits))
    return slv
