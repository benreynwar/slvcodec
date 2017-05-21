import tokenize
import logging
from collections import namedtuple
from io import StringIO


def as_int(v):
    try:
        if isinstance(v, int):
            o = v
        elif isinstance(v, str):
            o = int(v)
        else:
            o = None
    except ValueError:
        o = None
    return o


def is_int(v):
    o = as_int(v)
    return (o is not None)


logger = logging.getLogger(__name__)


def items_to_object(items):
    if len(items) == 1:
        o = items[0]
    else:
        o = Expression(items)
    return o


def transform(item, f):
    if hasattr(item, 'transform'):
        transformed = item.transform(f)
    else:
        transformed = item
    return transformed


def collect(item, f):
    if hasattr(item, 'collect'):
        collected = item.collect(f)
    else:
        collected = []
    return collected


def str_expression(item):
    if isinstance(item, str):
        o = item
    elif isinstance(item, int):
        o = str(item)
    elif hasattr(item, 'str_expression'):
        o = item.str_expression()
    else:
        raise Exception('Cannot use str_expression on {}'.format(item))
    return o


def get_constant_list(item):
    if isinstance(item, str):
        collected = [item]
    else:
        collected = collect(item, get_constant_list)
    return collected


def parse_integers(item):
    if is_int(item):
        parsed = as_int(item)
    else:
        parsed = transform(item, parse_integers)
    return parsed


def parse_parentheses(item):
    if hasattr(item, 'parse_parentheses'):
        parsed = item.parse_parentheses()
    else:
        parsed = transform(item, parse_parentheses)
    return parsed


def parse_multiplication(item):
    if hasattr(item, 'parse_multiplication'):
        parsed = item.parse_multiplication()
    else:
        parsed = transform(item, parse_multiplication)
    return parsed


def simplify_multiplication(item):
    if hasattr(item, 'simplify_multiplication'):
        parsed = item.simplify_multiplication()
    else:
        parsed = transform(item, simplify_multiplication)
    return parsed


def parse_addition(item):
    if hasattr(item, 'parse_addition'):
        parsed = item.parse_addition()
    else:
        parsed = transform(item, parse_addition)
    return parsed


def simplify_addition(item):
    if hasattr(item, 'simplify_addition'):
        parsed = item.simplify_addition()
    else:
        parsed = transform(item, simplify_addition)
    return parsed


def make_substitute_function(d):
    def substitute(item):
        if isinstance(item, str):
            o = d.get(item, item)
        else:
            o = transform(item, substitute)
        return o
    return substitute


def get_value(item):
    if is_int(item):
        result = as_int(item)
    else:
        result = item.value()
    return result


ExpressionBase = namedtuple('ExpressionBase', ['items'])
class Expression(ExpressionBase):

    def __new__(cls, items):
        obj = ExpressionBase.__new__(cls, tuple(items))
        return obj

    def transform(self, f):
        new_items = [f(item) for item in self.items]
        return items_to_object(new_items)

    def collect(self, f):
        collected = []
        for item in self.items:
            collected += f(item)
        return collected

    def value(self):
        raise Exception('Cannot get value of a unparsed expression.')

    def str_expression(self):
        return ' '.join([str_expression(item) for item in self.items])

    def parse_parentheses(self):
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
                    raise Exception('More closing than opening braces')
                else:
                    stack.append(item)
                open_braces -= 1
            elif open_braces > 0:
                stack.append(item)
            else:
                new_expression.append(parse_parentheses(item))
        if open_braces > 0:
            raise Exception('All braces not closed.')
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
        wrapped = items_to_object(parsed)
        return wrapped

    def parse_addition(self):
        items = [parse_addition(x) for x in self.items]
        numbers = []
        expressions = []
        sign = 1
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
                    raise Exception('Unknown sign')
                numbers.append(sign)
                expressions.append(item)
                sign = None
        assert(sign is None)
        terms = [Term(number=number, expression=expression)
                 for number, expression in zip(numbers, expressions)]
        o = Addition(terms)
        return o


MultiplicationBase = namedtuple('MultiplicationBase', ['numerators', 'denominators'])
class Multiplication(MultiplicationBase):

    def __new__(cls, numerators, denominators):
        obj = MultiplicationBase.__new__(
            cls, frozenset(numerators), frozenset(denominators))
        return obj

    def transform(self, f):
        numerators = [f(item) for item in self.numerators]
        denominators = [f(item) for item in self.denominators]
        t = Multiplication(numerators, denominators)
        return t

    def collect(self, f):
        collected = []
        for item in list(self.numerators) + list(self.denominators):
            collected += f(item)
        return collected

    def value(self):
        numerator_values = [get_value(item) for item in self.numerators]
        denominator_values = [get_value(item) for item in self.denominators]
        result = 1.0
        for n in numerator_values:
            result *= n
        for d in denominator_values:
            result /= d
        return result

    def str_expression(self):
        numerator = '*'.join([str_expression(item) for item in self.numerators])
        if self.denominators:
            denominator = '/'.join([str_expression(item) for item in self.denominators])
            s = '{}/{}'.format(numerator, denominator)
        else:
            s = numerator
        return s

    def simplify_multiplication(self):
        numerators = [transform(item, simplify_multiplication)
                      for item in self.numerators]
        denominators = [transform(item, simplify_multiplication)
                        for item in self.denominators]
        new_numerators = []
        new_denominators = []
        for x in numerators:
            if isinstance(x, Multiplication):
                new_numerators += x.numerators
                new_denominators += x.denominators
            else:
                new_numerators.append(x)
        for x in denominators:
            if isinstance(x, Multiplication):
                new_numerators += x.denominators
                new_denominators += x.numerators
            else:
                new_denominators.append(x)
        in_both = set(new_numerators) & set(new_denominators)
        numerator_int = 1
        final_numerators = []
        for x in set(new_numerators) - in_both:
            if is_int(x):
                numerator_int *= int(x)
            else:
                final_numerators.append(x)
        denominator_int = 1
        final_denominators = []
        for x in set(new_denominators) - in_both:
            if is_int(x):
                denominator_int *= int(x)
            else:
                final_denominators.append(x)
        if (not final_numerators) and (not final_denominators) and (denominator_int == 1):
            o = numerator_int
        else:
            if (len(final_numerators) == 1) and (denominator_int == 1):
                o = Term(numerator_int, final_numerators[0])
            else:
                if numerator_int != 1:
                    final_numerators.append(numerator_int)
                if denominator_int != 1:
                    final_denominators.append(denominator_int)
                o = Multiplication(final_numerators, final_denominators)
        return o


    @staticmethod
    def from_items(items):
        # Expression should be a list of objects separated by
        # '*' or '/'
        assert(len(items) % 2 == 1)
        assert(len(items) >= 3)
        denominators = []
        numerators = [items.pop(0)]
        while items:
            op = items.pop(0)
            val = items.pop(0)
            if op == '*':
                numerators.append(val)
            elif op == '/':
                denominators.append(val)
            else:
                raise ValueError('Invalid operator {}'.format(op))
        return Multiplication(numerators, denominators)


TermBase = namedtuple('TermBase', ['number', 'expression'])
class Term(TermBase):

    def __new__(cls, number, expression):
        assert(is_int(number))
        obj = MultiplicationBase.__new__(
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
        if self.number == 1:
            s = str_expression(self.expression)
        elif self.expression == 1:
            s = self.number
        else:
            s = '{}*{}'.format(self.number, str_expression(self.expression))
        return s


AdditionBase = namedtuple('AdditionBase', ['terms'])
class Addition(AdditionBase):

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
        s = '('
        first = True
        for t in self.terms:
            st = str_expression(t)
            if (st[0] == '-') or first:
                prefix = ''
            else:
                prefix = '+'
            s += prefix + st
            first = False
        s += ')'
        return s

    @staticmethod
    def from_items(items):
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
                    raise Exception('Unknown sign')
                numbers.append(sign)
                expressions.append(e)
                sign = None
        assert(sign is None)
        terms = [Term(number=number, expression=expression) for
                 number, expression in zip(numbers, expressions)]
        return Addition(terms=terms)

    def simplify_addition(self):
        # Get a list of terms.
        # If any of the expressions in the terms, are Addition or terms bring them in.
        expanded_terms = []
        for term in self.terms:
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
        d = {}
        int_part = 0
        for n, e in numbers_and_expressions:
            if is_int(e):
                int_part += int(e) * n
            else:
                if e not in d:
                    d[e] = n
                else:
                    d[e] += n
        d[int_part] = 1
        cleaned_d = dict([(k, v) for k, v in d.items() if (v != 0) and (k != 0)])
        new_expressions = list(cleaned_d.keys())
        new_numbers = [cleaned_d[k] for k in new_expressions]
        if len(new_expressions) == 1:
            if new_numbers[0] == 1:
                o = new_expressions[0]
            else:
                o = Term([new_numbers[0], new_expressions[0]])
        else:
            ts = [Term(number=n, expression=e) for n, e in zip(new_numbers, new_expressions)]
            if not ts:
                o = 0
            else:
                o = Addition(ts)
        return o


def string_to_expression(s):
    expression = Expression(
        [t.string for t in tokenize.generate_tokens(StringIO(s).readline)
         if t.string])
    return expression


def simplify(item):
    parsed_parentheses = parse_parentheses(item)
    parsed_multiplication = parse_multiplication(parsed_parentheses)
    simplified = simplify_multiplication(parsed_multiplication)
    parsed_addition = parse_addition(simplified)
    simplified_addition = simplify_addition(parsed_addition)
    parsed_integers = parse_integers(simplified_addition)
    final = parsed_integers
    return final


def parse_and_simplify(s):
    expression = string_to_expression(s)
    simplified = simplify(expression)
    return simplified


def test_multiplication():
    string = '3 * 2 / fish / (3 / 4)'
    simplified = parse_and_simplify(string)
    expected_answer = Multiplication([8], ['fish'])
    assert(simplified == expected_answer)


def test_multiplication2():
    string = 'fish / 2 * 3 * (burp/fish)'
    simplified = parse_and_simplify(string)
    expected_answer = Multiplication([3, 'burp'], [2])
    assert(simplified == expected_answer)


def test_addition():
    string = '1 + 2'
    simplified = parse_and_simplify(string)
    assert(simplified == 3)


def test_addition2():
    string = '1 + 2 + 4*5'
    simplified = parse_and_simplify(string)
    assert(simplified == 23)


def test_addition3():
    string = '1 +(1 + 1)'
    simplified = parse_and_simplify(string)
    assert(simplified == 3)


def test_substitute():
    string = 'fish + 3 * bear'
    simplified = parse_and_simplify(string)
    substituted = make_substitute_function({
        'fish': 2,
        'bear': 4,
        })(simplified)
    final = simplify(substituted)
    assert(final == 2 + 3 * 4)


def test_constant_list():
    string = '3 * (fish + 6) - 2 * bear'
    simplified = parse_and_simplify(string)
    constants = get_constant_list(simplified)
    assert(set(constants) == set(['fish', 'bear']))


def test_str_expression():
    string = '3 * (fish + 6) - 2 * bear + 2*avo - avo - avo'
    print(string)
    simplified = parse_and_simplify(string)
    print(simplified)
    s = str_expression(simplified)
    print(s)


def test_integer():
    string = '4'
    simplified = parse_and_simplify(string)
    assert(simplified == 4)

def test_simplication():
    string = '(width + 1) - 1'
    simplified = parse_and_simplify(string)
    assert(simplified == 'width')

def test_multiply_simplification():
    string = '2*fish - fish - fish'
    simplified = parse_and_simplify(string)
    assert(simplified == 0)


if __name__ == '__main__':
    #test_str_expression()
    test_multiply_simplification()
    test_constant_list()
    test_simplication()
    test_integer()
    test_multiplication()
    test_multiplication2()
    test_addition()
    test_addition2()
    test_substitute()
