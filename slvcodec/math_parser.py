'''
Functions to deal with doing math on algebraic strings.
Useful for parsing VHDL.
'''

import tokenize
import collections
import logging
import math
from io import StringIO


logger = logging.getLogger(__name__)


def logceil(argument):
    '''
    Returns the number of bits necessary to represent an integer that has
    values in the range from 0 to (`argument`-1).
    The logceil(0) is defined to be 1.
    The logceil(1) is defined to be 1.

    >>> logceil(0)
    1
    >>> logceil(1)
    1
    >>> logceil(4)
    2
    >>> logceil(7)
    3
    '''
    if argument <= 2:
        value = 1
    else:
        value = int(math.ceil(math.log(argument)/math.log(2)))
    return value


def logceil_1to0(argument):
    '''
    Returns the number of bits necessary to represent an integer that has
    values in the range from 0 to (`argument`-1).
    The logceil(0) is defined to be 0.
    The logceil(1) is defined to be 0.

    >>> logceil_1to0(0)
    0
    >>> logceil_1to0(1)
    0
    >>> logceil_1to0(2)
    1
    >>> logceil_1to0(4)
    2
    >>> logceil_1to0(7)
    3
    '''
    if argument < 2:
        value = 0
    else:
        value = int(math.ceil(math.log(argument)/math.log(2)))
    return value


# These are the default functions that can be parsed from the VHDL.
REGISTERED_FUNCTIONS = {
    'logceil': logceil,
    'logceil_1to0': logceil_1to0,
    'clog2': logceil,
    'slvcodec_logceil': logceil,
    'real': lambda x: x,
    'integer': lambda x: x,
    'ceil': math.ceil,
    'pow2': lambda x: pow(2, x),
    'maximum': max,
    'minimum': min,
    }


def register_function(name, function):
    '''
    Register a python function to be used in place of a
    parsed VHDL function.
    '''
    assert name not in REGISTERED_FUNCTIONS
    REGISTERED_FUNCTIONS[name] = function


class MathParsingError(Exception):
    '''
    An exception parsing math.
    '''
    pass


def as_number(v):
    '''
    Converts a value to a number if possible otherwise returns None.
    >>> as_number('fish')
    >>> as_number('3.2')
    3.2
    >>> as_number('3.0')
    3
    >>> as_number(100)
    100
    >>> as_number('3.0.0')
    '''
    try:
        if isinstance(v, int):
            o = v
        elif isinstance(v, float):
            if v == int(v):
                o = int(v)
            else:
                o = v
        elif isinstance(v, str):
            f = float(v)
            if f == int(f):
                o = int(f)
            else:
                o = f
        else:
            o = None
    except ValueError:
        o = None
    return o


def is_number(v):
    '''
    Whether the value is or can be converted to a number.

    >>> is_number('fish')
    False
    >>> is_number('20.2')
    True
    >>> is_number(70)
    True
    '''
    o = as_number(v)
    return o is not None


def transform(item, f):
    '''
    Transform an object with a function.  The object will only be transformed
    if it has a transform method.
    '''
    if hasattr(item, 'transform'):
        transformed = item.transform(f)
    else:
        transformed = item
    return transformed


def collect(item, f):
    '''
    Retrieve items from an object with a function.  Items will only be returned
    if the object has a collect method.
    '''
    if hasattr(item, 'collect'):
        collected = item.collect(f)
    else:
        collected = []
    return collected


def str_expression(item):
    '''
    Returns a string representation of the mathematical equation.

    >>> str_expression(Addition([Term(number=3, expression='fish'), Term(number=1, expression='bear')]))
    '(3*fish+bear)'
    '''
    if isinstance(item, str):
        o = item
    elif isinstance(item, int):
        o = str(item)
    elif isinstance(item, float):
        if int(item) == item:
            o = str(int(item))
        else:
            o = str(item)
    elif hasattr(item, 'str_expression'):
        o = item.str_expression()
    else:
        raise MathParsingError('Cannot use str_expression on {}'.format(item))
    return o


def get_constant_list(item):
    '''
    Returns all the variables in the item.
    >>> item = parse_and_simplify('bear - 3 * fish + bear')
    >>> get_constant_list(item) == {'bear', 'fish'}
    True
    '''
    if isinstance(item, str):
        if '"' in item:
            # Probably something like "001"
            collected = []
        elif item == '\n':
            # Parsing issue that should be fixed properly
            collected = []
        else:
            collected = [item]
    else:
        collected = collect(item, get_constant_list)
    return set(collected)


def parse_integers(item):
    '''
    Convert all the strings that can be into numbers.

    >>> parse_integers(5)
    5
    >>> parse_integers('6.2')
    6.2
    >>> parse_integers('6.0')
    6
    >>> parse_integers(Expression(['fish', '6.2', 5, '7']))
    Expression(items=('fish', 6.2, 5, 7))
    '''
    if is_number(item):
        parsed = as_number(item)
    else:
        parsed = transform(item, parse_integers)
    return parsed


def parse_parentheses(item):
    '''
    Group items into expressions based on location of parentheses.

    Only 'Expression` has a `parse_parentheses' method so see that
    function for examples.
    '''
    if hasattr(item, 'parse_parentheses'):
        parsed = item.parse_parentheses()
    else:
        parsed = transform(item, parse_parentheses)
    return parsed


def parse_functions(item):
    '''
    Identify functions in the expression.
    Parentheses must have been first parsed.

    Only `Expression` has a `parse_functions` method so see that function
    for examples.
    '''
    if hasattr(item, 'parse_functions'):
        parsed = item.parse_functions()
    else:
        parsed = transform(item, parse_functions)
    return parsed


def parse_multiplication(item):
    '''
    Groups multipled and divided items together.

    Only `Expression` has a `parse_multiplication` method so see that function
    for examples.
    '''
    if hasattr(item, 'parse_multiplication'):
        parsed = item.parse_multiplication()
    else:
        parsed = transform(item, parse_multiplication)
    return parsed


def parse_addition(item):
    '''
    Convert an expression into a list of added terms.

    Only `Expression` has a `parse_multiplication` method so see that function
    for examples.
    '''
    if hasattr(item, 'parse_addition'):
        parsed = item.parse_addition()
    else:
        parsed = transform(item, parse_addition)
    return parsed


def simplify(item):
    '''
    Simplify the math a few times.

    Logs a warning if it does not converge.
    '''
    old_value = item
    max_simplifications = 5
    hit_limit = True
    for dummy_index in range(max_simplifications):
        if hasattr(old_value, 'simplify'):
            new_value = old_value.simplify()
        else:
            new_value = transform(old_value, simplify)
        if old_value == new_value:
            hit_limit = False
            break
        else:
            old_value = new_value
    if hit_limit:
        logger.warning('Hit maximum simplifications when simplifying {}'.format(
            str_expression(new_value)))
    return new_value


def make_substitute_function(d):
    '''
    Returns a function that replaces strings with elements
    from the dictionary `d`.
    Useful for resolving constants and generics.
    '''
    def substitute(item):
        if isinstance(item, str):
            o = d.get(item, item)
        else:
            o = transform(item, substitute)
        return o
    return substitute


def get_value(item):
    if is_number(item):
        result = as_number(item)
    else:
        result = as_number(item.value())
    return result


ExpressionBase = collections.namedtuple('ExpressionBase', ['items'])
class Expression(ExpressionBase):
    '''
    An expression is just a list of tokens and parsed elements.
    It's an intemediate form used during parsing.
    '''

    def __new__(cls, items):
        obj = ExpressionBase.__new__(cls, tuple(items))
        return obj

    def transform(self, f):
        new_items = [f(item) for item in self.items]
        if len(new_items) == 1:
            o = new_items[0]
        else:
            o = Expression(new_items)
        return o

    def collect(self, f):
        collected = []
        for item in self.items:
            collected += f(item)
        return collected

    def value(self):
        raise MathParsingError('Cannot get value of a unparsed expression.')

    def str_expression(self):
        return ' '.join([str_expression(item) for item in self.items])

    def parse_functions(self):
        '''
        Find strings followed immediately by an expression.
        Assume that is a function.

        >>> s = 'logceil(5) - 2'
        >>> e = Expression(tokenize_string(s))
        >>> parsed_parentheses = e.parse_parentheses()
        >>> parsed_parentheses.parse_functions()
        Expression(items=(Function(name='logceil', arguments=('5',)), '-', '2'))
        >>> e = Expression(tokenize_string('logceil(logceil(5)) - 2'))
        >>> parsed_parentheses = e.parse_parentheses()
        >>> parsed_parentheses.parse_functions()
        Expression(items=(Function(name='logceil', arguments=(Function(name='logceil', arguments=('5',)),)), '-', '2'))
        >>> s = 'minimum(5+6, 20-2)'
        >>> e = Expression(tokenize_string(s))
        >>> parsed_parentheses = e.parse_parentheses()
        >>> parsed_parentheses.parse_functions()
        Expression(items=(Function(name='minimum', arguments=(Expression(items=('5', '+', '6')), Expression(items=('20', '-', '2')))),))
        '''
        items = [parse_functions(item) for item in self.items]
        last_item = None
        new_items = []
        for item in items:
            if (isinstance(last_item, str) and last_item[0].isalpha() and
                    isinstance(item, Expression)):
                # Split arguments by commas
                arguments = []
                argument = []

                def add_argument(argument):
                    assert len(argument) > 0
                    if len(argument) == 1:
                        arguments.append(argument[0])
                    else:
                        arguments.append(Expression(argument))

                for subitem in item.items:
                    if subitem == ',':
                        add_argument(argument)
                        argument = []
                    else:
                        argument.append(subitem)
                add_argument(argument)
                function_item = Function(name=last_item, arguments=tuple(arguments))
                new_items.append(function_item)
                last_item = None
            else:
                if last_item is not None:
                    new_items.append(last_item)
                last_item = item
        if last_item is not None:
            new_items.append(last_item)
        return Expression(new_items)

    def parse_parentheses(self):
        '''
        Create new sub Expressions for items contained within parentheses.

        >>> s = '(fish + (bear * 3)) - 9'
        >>> e = Expression(tokenize_string(s))
        >>> e.parse_parentheses()
        Expression(items=(Expression(items=('fish', '+', Expression(items=('bear', '*', '3')))), '-', '9'))
        '''
        open_braces = 0
        new_expression = []
        for item in self.items:
            if item == '(':
                if open_braces == 0:
                    stack = []
                else:
                    stack.append(item)
                open_braces += 1
            elif item == ')':
                if open_braces == 1:
                    sub_expression = Expression(stack).parse_parentheses()
                    new_expression.append(sub_expression)
                    stack = []
                elif open_braces == 0:
                    raise MathParsingError('More closing than opening braces')
                else:
                    stack.append(item)
                open_braces -= 1
            elif open_braces > 0:
                stack.append(item)
            else:
                new_expression.append(parse_parentheses(item))
        if open_braces > 0:
            raise MathParsingError('All braces not closed.')
        return Expression(new_expression)

    @staticmethod
    def finish_multiplication_term(items):
        parsed = []
        if ('*' in items) or ('/' in items):
            multiplication = Multiplication.from_items(items)
            parsed.append(multiplication)
        else:
            parsed += items
        return parsed

    def parse_multiplication(self):
        '''
        Goes through the expression items and groups terms that are multiplied
        together into a Multiplication object.

        >>> Expression(tokenize_string('3 * 4')).parse_multiplication()
        Multiplication(powers=(Power(number=1, expression='3'), Power(number=1, expression='4')))
        >>> Expression(tokenize_string('bear + 2 / fish')).parse_multiplication()
        Expression(items=('bear', '+', Multiplication(powers=(Power(number=1, expression='2'), Power(number=-1, expression='fish')))))
        '''
        parsed = []
        possible_multiplication = []
        for item in self.items:
            if item in ('-', '+'):
                parsed += Expression.finish_multiplication_term(
                    possible_multiplication)
                possible_multiplication = []
                parsed.append(item)
            else:
                possible_multiplication.append(parse_multiplication(item))
        parsed += Expression.finish_multiplication_term(possible_multiplication)
        if len(parsed) == 1:
            wrapped = parsed[0]
        else:
            wrapped = Expression(parsed)
        return wrapped

    def parse_addition(self):
        '''
        Goes through the items in the expression and groups together items
        that are added together into an Addition object.

        >>> Expression(tokenize_string('3 - 4')).parse_addition()
        Addition(terms=(Term(number=1, expression='3'), Term(number=-1, expression='4')))
        '''
        if not self.items:
            o = Addition([])
            return o
        items = [parse_addition(x) for x in self.items]
        numbers = []
        expressions = []
        sign = 1
        is_unknown = False
        for item in items:
            if item == '+':
                if sign is None:
                    sign = 1
            elif item == '-':
                if sign is None:
                    sign = -1
                else:
                    sign = -1 * sign
            else:
                if sign is None:
                    logger.debug('Failed to parse {}.  Setting to Unknown'.format(items))
                    is_unknown = True
                    break
                numbers.append(sign)
                expressions.append(item)
                sign = None
        if is_unknown:
            o = Unknown(item)
        else:
            assert sign is None
            terms = [Term(number=number, expression=expression)
                     for number, expression in zip(numbers, expressions)]
            o = Addition(terms)
        return o


UnknownBase = collections.namedtuple('UnknownBase', ['items'])
class Unknown(UnknownBase):
    '''
    A dummy object into which we can throw things we fail to parse without
    everything crashing and burning.
    '''

    def transform(self, f):
        return self

    def collect(self, f):
        return []

    def value(self):
        raise MathParsingError('Cannot get value of Unknown.')


FunctionBase = collections.namedtuple('FunctionBase', ['name', 'arguments'])
class Function(FunctionBase):
    '''
    Represents a function in the expression.  Currently it
    only supports the log ceiling.
    '''

    def transform(self, f):
        new_arguments = [f(arg) for arg in self.arguments]
        f = Function(name=self.name, arguments=tuple(new_arguments))
        return f

    def collect(self, f):
        collected = []
        for arg in self.arguments:
            collected += f(arg)
        return collected

    def value(self):
        arguments = [get_value(arg) for arg in self.arguments]
        if self.name in REGISTERED_FUNCTIONS:
            v = REGISTERED_FUNCTIONS[self.name](*arguments)
        else:
            raise MathParsingError('Unknown function {}'.format(self.name))
        return v

    def simplify(self):
        arguments = [simplify(arg) for arg in self.arguments]
        if all(is_number(arg) for arg in arguments) and (self.name in REGISTERED_FUNCTIONS):
            o = REGISTERED_FUNCTIONS[self.name](*arguments)
        else:
            o = Function(name=self.name, arguments=tuple(arguments))
        return o

    def str_expression(self):
        arguments = ', '.join(str_expression(arg) for arg in self.arguments)
        s = '{}({})'.format(self.name, arguments)
        return s


PowerBase = collections.namedtuple('TermBase', ['number', 'expression'])
class Power(PowerBase):
    '''
    A multiplication object contains many Power objects.  This is to make
    it easy to combine x * y * x into (x ** 2) * y where (x**2) is a power
    object with number=2, and (y) is a power object with number=1.
    '''

    def __new__(cls, number, expression):
        '''
        Represents pow(expression, number)
        '''
        assert is_number(number)
        obj = PowerBase.__new__(
            cls, number, expression)
        return obj

    def transform(self, f):
        expression = f(self.expression)
        t = Power(number=self.number, expression=expression)
        return t

    def collect(self, f):
        collected = f(self.expression)
        return collected

    def value(self):
        result = pow(get_value(self.expression), self.number)
        return result

    def str_expression(self):
        '''
        Return a string representing a number to a power.

        >>> Power(-2, 'fish').str_expression()
        '1/fish/fish'
        >>> Power(1, 'bear').str_expression()
        'bear'
        >>> Power(0, 5).str_expression()
        '1'
        '''
        if self.number == 1:
            s = str_expression(self.expression)
        elif (self.number == 0) or (self.expression == 1):
            s = '1'
        else:
            absnumber = abs(self.number)
            if self.number > 0:
                s = '*'.join([str_expression(self.expression)]*absnumber)
            else:
                s = '/'.join(['1']+[str_expression(self.expression)]*absnumber)
        return s


MultiplicationBase = collections.namedtuple('MultiplicationBase', ['powers'])
class Multiplication(MultiplicationBase):
    '''
    A group of items which are multiplied/divided together.
    '''

    def __new__(cls, powers):
        obj = MultiplicationBase.__new__(
            cls, tuple(powers))
        return obj

    def transform(self, f):
        powers = [f(item) for item in self.powers]
        t = Multiplication(powers)
        return t

    def collect(self, f):
        collected = []
        for item in self.powers:
            collected += f(item)
        return collected

    def value(self):
        power_values = [get_value(item) for item in self.powers]
        result = 1
        for n in power_values:
            result *= n
        return result

    def str_expression(self):
        s = '*'.join([str_expression(item) for item in self.powers])
        return s

    def simplify(self):
        '''
        >>> Multiplication((Power(1, 'fish'), Power(-1, 'fish'), Power(1, 'bear'))).simplify()
        'bear'
        >>> Multiplication((Power(3, 2), Power(-1, 10))).simplify()
        0.8
        '''
        new_powers = collections.OrderedDict()
        powers = [transform(item, simplify) for item in self.powers]
        pure = 1
        for power in powers:
            if is_number(power.expression):
                pure *= power.value()
            else:
                if power.expression not in new_powers:
                    new_powers[power.expression] = Power(
                        expression=power.expression, number=0)
                old_number = new_powers[power.expression].number
                new_number = old_number + power.number
                new_power = Power(expression=power.expression, number=new_number)
                new_powers[power.expression] = new_power
        relevant_powers = [p for p in new_powers.values() if p.number != 0]
        if len(relevant_powers) == 0:
            m = 1
        elif len(relevant_powers) == 1:
            if relevant_powers[0].number == 1:
                m = relevant_powers[0].expression
            else:
                m = relevant_powers[0]
        else:
            m = Multiplication(relevant_powers)
        if pure != 1:
            if m == 1:
                o = pure
            else:
                o = Addition(terms=[Term(number=pure, expression=m)])
        else:
            o = m
        return o

    @staticmethod
    def from_items(items):
        '''
        Returns a Multiplication object from a list of objects.
        Every second object must be '*' or '/'.
        '''
        # Expression should be a list of objects separated by
        # '*' or '/'
        assert len(items) % 2 == 1
        assert len(items) >= 3
        powers = [Power(number=1, expression=items.pop(0))]
        while items:
            op = items.pop(0)
            val = items.pop(0)
            if op == '*':
                powers.append(Power(number=1, expression=val))
            elif op == '/':
                powers.append(Power(number=-1, expression=val))
            else:
                raise ValueError('Invalid operator {}'.format(op))
        return Multiplication(powers)


TermBase = collections.namedtuple('TermBase', ['number', 'expression'])
class Term(TermBase):
    '''
    An Addition object contains many Term objects.
    Useful so that we can easily combine multiples instances of the
    same constant.
    '''

    def __new__(cls, number, expression):
        assert is_number(number)
        obj = TermBase.__new__(
            cls, number, expression)
        return obj

    def transform(self, f):
        expression = f(self.expression)
        t = Term(number=self.number, expression=expression)
        return t

    def collect(self, f):
        collected = f(self.expression)
        return collected

    def value(self):
        result = self.number * get_value(self.expression)
        return result

    def str_expression(self):
        '''
        Convert a Term to a string.

        >>> Term(-1, 'fish').str_expression()
        '-fish'
        >>> Term(2, 'bear').str_expression()
        '2*bear'
        '''
        if self.number == 1:
            s = str_expression(self.expression)
        elif self.number == -1:
            s = '-' + str_expression(self.expression)
        elif self.number == 0:
            s = '0'
        elif self.expression == 1:
            s = self.number
        else:
            s = '{}*{}'.format(str_expression(self.number),
                               str_expression(self.expression))
        return s


AdditionBase = collections.namedtuple('AdditionBase', ['terms'])
class Addition(AdditionBase):
    '''
    Many items that are added/substracted together.
    '''

    def __new__(cls, terms):
        obj = AdditionBase.__new__(cls, tuple(terms))
        return obj

    def transform(self, f):
        terms = [f(term) for term in self.terms]
        t = Addition(terms=terms)
        return t

    def collect(self, f):
        collected = []
        for item in self.terms:
            collected += f(item)
        return collected

    def value(self):
        values = [get_value(item) for item in self.terms]
        result = sum(values)
        return result

    def str_expression(self):
        '''
        Converts an Addition object into a string.

        >>> Addition((Term(3, 'fish'), Term(2, 4))).str_expression()
        '(3*fish+2*4)'
        >>> Addition((Term(-1, 'fish'),)).str_expression()
        '-fish'
        '''
        s = ''
        first = True
        for t in self.terms:
            st = str_expression(t)
            if (st[0] == '-') or first:
                prefix = ''
            else:
                prefix = '+'
            s += prefix + st
            first = False
        if len(self.terms) > 1:
            s = '(' + s + ')'
        return s

    @staticmethod
    def from_items(items):
        '''
        Create an Addition object from a list of items.
        '''
        numbers = []
        expressions = []
        sign = None
        for e in items:
            if e == '+':
                if sign is None:
                    sign = 1
            elif e == '-':
                if sign is None:
                    sign = -1
                else:
                    sign = -1 * sign
            else:
                if sign is None:
                    raise MathParsingError('Unknown sign')
                numbers.append(sign)
                expressions.append(e)
                sign = None
        assert sign is None
        terms = [Term(number=number, expression=expression) for
                 number, expression in zip(numbers, expressions)]
        return Addition(terms=terms)

    def simplify(self):
        '''
        Simplify an Addition object by combining terms.

        >>> Addition((Term(3, 'fish'), Term(-2, 'fish'))).simplify()
        'fish'
        >>> simplified = Addition((Term(3, 'fish'), Term(2, 'fish'), Term(1, 'bear'))).simplify()
        >>> set(simplified.terms) == set((Term(5, 'fish'), Term(1, 'bear')))
        True
        '''
        terms = [simplify(term) for term in self.terms]
        # Get a list of terms.
        # If any of the expressions in the terms, are Addition or terms bring them in.
        expanded_terms = []
        for term in terms:
            if isinstance(term.expression, Addition):
                new_terms = [Term(number=term.number*t.number, expression=t.expression)
                             for t in term.expression.terms]
                expanded_terms += new_terms
            elif isinstance(term.expression, Term):
                new_term = Term(number=term.number*term.expression.number,
                                expression=term.expression.expression)
                expanded_terms.append(new_term)
            else:
                new_term = term
                expanded_terms.append(new_term)
        numbers_and_expressions = [(t.number, t.expression) for t in expanded_terms]
        d = collections.OrderedDict()
        int_part = 0
        for n, e in numbers_and_expressions:
            if is_number(e):
                int_part += int(e) * n
            else:
                if e not in d:
                    d[e] = n
                else:
                    d[e] += n
        d[int_part] = 1
        cleaned_d = collections.OrderedDict(
            [(k, v) for k, v in d.items() if (v != 0) and (k != 0)])
        new_expressions = list(cleaned_d.keys())
        new_numbers = [cleaned_d[k] for k in new_expressions]
        if len(new_expressions) == 1:
            if new_numbers[0] == 1:
                o = new_expressions[0]
            else:
                o = Addition(terms=[Term(
                    number=new_numbers[0], expression=new_expressions[0])])
        else:
            ts = [Term(number=n, expression=e)
                  for n, e in zip(new_numbers, new_expressions)]
            if not ts:
                o = 0
            else:
                o = Addition(ts)
        return o


def tokenize_string(s):
    '''
    Break a string up into tokens.
    '''
    tokens = [
        t.string for t in tokenize.generate_tokens(StringIO(s).readline)
        if t.string and (not t.string.isspace())]
    return tokens


def parse_string(s):
    '''
    Tokenize a string and then parse it.
    '''
    tokens = tokenize_string(s)
    expression = Expression(tokens)
    item = parse(expression)
    return item


def parse(item):
    '''
    Parsed a tokenized string.
    '''
    if '**' in item.items:
        raise MathParsingError('symbolic math cannot parse power "**" syntax')
    parsed_integers = parse_integers(item)
    parsed_parentheses = parse_parentheses(parsed_integers)
    parsed_functions = parse_functions(parsed_parentheses)
    parsed_multiplication = parse_multiplication(parsed_functions)
    parsed_addition = parse_addition(parsed_multiplication)
    return parsed_addition


def parse_and_simplify(s):
    '''
    Tokenize, parse and simplify a string.
    '''
    if s == '':
        raise ValueError('Cannot parse an empty string')
    parsed = parse_string(s)
    simplified = simplify(parsed)
    return simplified


if __name__ == '__main__':
    #import doctest
    #doctest.testmod()
    s = 'minimum(1, 2) - 2'
    e = Expression(tokenize_string(s))
    parsed_parentheses = e.parse_parentheses()
    parsed_functions = parsed_parentheses.parse_functions()
    print(parsed_functions)
