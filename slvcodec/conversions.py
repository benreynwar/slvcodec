def list_of_uints_to_uint(list_of_uints, width):
    '''
    Convert a list of unsigned integers into a single unsigned integer.

    Args:
        `list_of_uints`: The list of integers.
        `width`: The width of each individual integer.
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
    '''
    if uint is None:
        output = None
    else:
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
    '''
    if sint is None:
        uint = None
    elif sint < 0:
        uint = sint + pow(2, width)
    else:
        uint = sint
    return uint


def uint_to_sint(uint, width):
    '''
    Convert an unsigned integer to a signed integer.
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
    '''
    if uint is None:
        list_of_sints = None
    else:
        list_of_uints = uint_to_list_of_uints(uint, size, width)
        list_of_sints = [uint_to_sint(uint, width) for uint in list_of_uints]
    return list_of_sints


def slv_to_uint(slv):
    '''
    Convert a string of '0' and '1' to an unsigned integer.
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


def uint_to_slv(uint, width):
    '''
    Convert an unsigned integer to a string of '0' and '1'.
    '''
    if uint is None:
        slv = 'U' * width
    else:
        bits = []
        for w in range(width):
            bits.append('1' if uint % 2 else '0')
            uint //= 2
        slv = ''.join(reversed(bits))
    return slv
