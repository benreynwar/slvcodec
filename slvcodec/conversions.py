def list_of_uints_to_uint(list_of_uints, width):
    '''
    Convert a list of unsigned integers into a single unsigned integer.

    Args:
        `list_of_uints`: The list of integers.
        `width`: The width of each individual integer.
    '''
    output = 0
    f = pow(2, width)
    for v in reversed(list_of_uints):
        assert(v < f)
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
    residual = uint
    f = pow(2, width)
    output = []
    for i in range(size):
        output.append(residual % f)
        residual = residual >> width
    assert(residual == 0)
    return output
