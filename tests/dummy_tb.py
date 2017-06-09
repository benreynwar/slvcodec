import random


class DummyTest:

    def __init__(self, entity, generics):
        self.entity = entity
        self.generics = generics
        self.length = generics['length']

    def make_input_data(self):
        data = [{
            'reset': random.randint(0, 1),
            'i_valid': random.randint(0, 1),
            'i_dummy': {
                'manydata': [0, 0],
                'data': 0,
                'anint': 0,
                'anotherint': 0,
                'logic': 0,
                'slv': 1,
                },
            } for i in range(20)]
        return data

    def check_output_data(self, input_data, output_data):
        o_data = [d['o_data'] for d in output_data]
        expected_data = [[0]*self.length] * len(o_data)
        assert(o_data == expected_data)
