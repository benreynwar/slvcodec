"""
This module lets communicate with a ghdl simulation over named pipes.

It also defines objects that behavior similarly to cocotb's 'dut' object
so that we can write tests that can be run both with cocotb or
using named pipes.
"""

import os
import asyncio
import collections
import subprocess
import logging
import select

from slvcodec import add_slvcodec_files
from slvcodec import filetestbench_generator
from slvcodec import config, typs


logger = logging.getLogger(__name__)

class TerminateException(Exception):
    pass


LOOP = None


def start_ghdl_process(directory, filenames, testbench_name):
    pwd = os.getcwd()
    os.chdir(directory)
    logger.debug('Directory is {}'.format(directory))
    analyzed = []
    for filename in filenames:
        if filename not in analyzed:
            subprocess.call(['ghdl', '-a', '--std=08', filename])
            analyzed.append(filename)
    cmd = ['ghdl', '-r', '--std=08', testbench_name]
    dump_wave = True
    if dump_wave:
        #cmd.append('--vcd=wave.vcd')
        cmd.append('--wave=wave.ghw')
    cmd += ['-gPIPE_PATH=' + directory]
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    os.chdir(pwd)
    return process



class Simulator:
    """
    The Simulator communicates with the real ghdl simulator over named pipes.
    """

    def __init__(self, directory, filenames, top_entity, generics, clk_name='clk'):
        clock_domains = {clk_name: ['.*']}
        generation_directory = os.path.join(directory, 'generated')
        os.makedirs(generation_directory)
        ftb_directory = os.path.join(directory, 'ftb')
        os.makedirs(ftb_directory)

        top_testbench = top_entity + '_tb'

        logger.debug('Making testbench')
        with_slvcodec_files = add_slvcodec_files(directory, filenames)
        generated_fns, generated_wrapper_fns, resolved = filetestbench_generator.prepare_files(
            directory=ftb_directory, filenames=with_slvcodec_files,
            top_entity=top_entity, use_pipes=True, use_vunit=False,
            clock_domains=clock_domains, default_generics=generics,
        )
        combined_filenames = with_slvcodec_files + generated_fns + generated_wrapper_fns

        logger.debug('Creating named pipes.')
        os.mkfifo(os.path.join(directory, 'indata_{}.dat'.format(clk_name)))
        os.mkfifo(os.path.join(directory, 'outdata_{}.dat'.format(clk_name)))

        self.entity = resolved['entities'][top_entity]
        self.resolved = resolved

        logger.debug('Start simulation process.')
        self.process = start_ghdl_process(directory, combined_filenames, top_testbench)
        logger.debug('Simulation process started.')
        self.stdout_poll = select.poll()
        self.stdout_poll.register(self.process.stdout, select.POLLIN)
        self.stderr_poll = select.poll()
        self.stderr_poll.register(self.process.stderr, select.POLLIN)
        self.log()

        logger.debug('Opening handles')
        self.in_handle = open(os.path.join(directory, 'indata_{}.dat'.format(clk_name)), 'w')
        self.out_handle = open(os.path.join(directory, 'outdata_{}.dat'.format(clk_name)))
        logger.debug('Opened handles')
        self.out_width = self.entity.output_width(generics)

        self.clk_name = clk_name
        self.generics = generics
        logger.debug('Making dut interface.')
        self.dut = DutInterface(resolved, top_entity, ignored_ports=[clk_name],
                                generics=self.generics)
        self.clk_signal = 'My clock signal'
        setattr(self.dut, clk_name, self.clk_signal)


    def log(self):
        logger.debug('Starting ghdl logging')
        while self.stdout_poll.poll(1):
            stdout_line = self.process.stdout.readline()
            logger.debug('ghdl stdout: ' + stdout_line.decode())
        while self.stderr_poll.poll(1):
            stderr_line = self.process.stderr.readline()
            logger.debug('ghdl stderr: ' + stderr_line.decode())
        logger.debug('Finishing ghdl logging')

    def step(self):
        input_slv = self.entity.inputs_to_slv(
            self.dut.get_inputs(), generics=self.generics, subset_only=False)
        self.in_handle.write(input_slv + '\n')
        self.in_handle.flush()
        length_required = self.out_width+1
        logger.debug('Trying to read')
        output_slv = self.out_handle.read(length_required)
        logger.debug('Succeeded reading')
        assert len(output_slv) == length_required
        assert output_slv[-1] == '\n'
        self.dut.set_from_simulation(self.entity.outputs_from_slv(output_slv, generics=self.generics))
        self.log()

    def __del__(self):
        logger.debug('Closing handles')
        if hasattr(self, 'out_handle'):
            self.out_handle.close()
        if hasattr(self, 'in_handle'):
            self.in_handle.close()


class Numeric:
    """
    A base class that lets us directly do math on an object that
    exposes a numeric value via the .get() method.
    """

    def __add__(self, other):
        return self.get() + other
    def __radd__(self, other):
        return self.get() + other
    def __sub__(self, other):
        return self.get() - other
    def __rsub__(self, other):
        return other - self.get()
    def __mul__(self, other):
        return other * self.get()
    def __rmul__(self, other):
        return other * self.get()
    def __truediv__(self, other):
        return self.get() / other
    def __rtruediv__(self, other):
        return other / self.get()
    def __mod__(self, other):
        return self.get() % other
    def __rmod__(self, other):
        return other % self.get()
    def __lt__(self, other):
        return self.get() < other
    def __rlt__(self, other):
        return other < self.get()
    def __le__(self, other):
        return self.get() <= other
    def __rle__(self, other):
        return other <= self.get()
    def __eq__(self, other):
        return self.get() == other
    def __req__(self, other):
        return other == self.get()
    def __ne__(self, other):
        return self.get() != other
    def __rne__(self, other):
        return other != self.get()
    def __gt__(self, other):
        return self.get() > other
    def __rgt__(self, other):
        return other > self.get()
    def __ge__(self, other):
        return self.get() >= other
    def __rge__(self, other):
        return other >= self.get()


class StdLogic:

    def __init__(self, direction):
        self.direction = direction
        self.value = None
        self.next_value = None
        self.locked = False

    def update(self):
        self.value = self.next_value

    def lock(self):
        self.locked = True

    def __str__(self):
        if self.value == 0:
            return '0'
        elif self.value == 1:
            return '1'
        else:
            return 'U'

    def unlock(self):
        self.locked = False

    def set(self, value):
        assert value in (0, 1, None)
        self.next_value = value

    def get(self):
        assert self.value in (0, 1, None)
        return self.value

    def get_if_leaf(self):
        return self.get()

    def __eq__(self, other):
        return self.get() == other

    def __ne__(self, other):
        return self.get() != other

    def __le__(self, value):
        self.set(value)

    def __bool__(self):
        if self.value == 0:
            return False
        elif self.value == 1:
            return True
        else:
            raise ValueError('StdLogic has value {}. Cannot be cast to boolean'.format(self.value))


class Unsigned(Numeric):
    
    def __init__(self, direction, width):
        self.direction = direction
        self.value = None
        self.max_value = pow(2, width)-1
        self.next_value = None
        self.locked = False

    def update(self):
        self.value = self.next_value

    def lock(self):
        self.locked = True

    def unlock(self):
        self.locked = False

    def set(self, value):
        assert (value is None) or ((value >=0) and (value <= self.max_value))
        self.next_value = value

    def get(self):
        assert (self.value is None) or ((self.value >=0) and (self.value <= self.max_value))
        return self.value

    def get_if_leaf(self):
        return self.get()

    def __le__(self, value):
        self.set(value)


class Array:

    def __init__(self, direction, typ, generics=None):
        sub_type = typ.unconstrained_type.subtype
        if generics:
            self.size = typs.make_substitute_generics_function(generics)(typ.size)
        else:
            self.size = typ.size.value()
        self.items = [interface_from_type(direction, sub_type) for i in range(self.size)]

    def update(self):
        for item in self.items:
            item.update()

    def lock(self):
        for item in self.items:
            item.lock()

    def unlock(self):
        for item in self.items:
            item.unlock()

    def __getitem__(self, index):
        return self.items[index].get_if_leaf()

    def __setitem__(self, index, value):
        self.items[index].set(value)

    def get(self):
        return [item.get() for item in self.items]

    def set(self, items):
        if items is None:
            items = [None] * len(self.items)
        assert len(items) == self.size
        for index, item in enumerate(items):
            self.items[index].set(item)

    def get_if_leaf(self):
        return self

    def __le__(self, items):
        self.set(items)

    def __eq__(self, items):
        return self.get() == items


class Record:

    def __init__(self, direction, typ):
        self.__dict__['typ'] = typ
        self.__dict__['_pieces'] = {}
        for sub_name, sub_typ in typ.names_and_subtypes:
            self.__dict__['_pieces'][sub_name] = interface_from_type(direction, sub_typ)
        self.__dict__['direction'] = direction

    def update(self):
        for item in self.__dict__['_pieces'].values():
            item.update()

    def lock(self):
        for item in self.__dict__['_pieces'].values():
            item.lock()

    def unlock(self):
        for item in self.__dict__['_pieces'].values():
            item.unlock()

    def __setattr__(self, name, value):
        piece = self.__dict__['_pieces'][name]
        piece.set(value)

    def __getattr__(self, name):
        return self.get_element(name)

    def get_element(self, name):
        piece = self.__dict__['_pieces'][name]
        return piece

    def set(self, value):
        if value is None:
            for piece in self.__dict__['_pieces'].values():
                piece.set(value)
        else:
            for key, sub_value in value.items():
                setattr(self, key, sub_value)

    def get(self):
        value = {}
        for name, piece in self.__dict__['_pieces'].items():
            value[name] = getattr(self, name)
            if hasattr(value[name], 'get'):
                value[name] = value[name].get()
        return value

    def __eq__(self, other):
        return self.get() == other
        
    def __ne__(self, other):
        return self.get() != other

    def get_if_leaf(self):
        return self

    def __le__(self, value):
        self.set(value)


def interface_from_type(direction, typ, generics={}):
    if type(typ) == typs.StdLogic:
        interface = StdLogic(direction)
    elif type(typ) == typs.Record:
        interface = Record(direction, typ)
    elif type(typ) in (typs.ConstrainedStdLogicVector, typs.ConstrainedUnsigned):
        width = typs.make_substitute_generics_function(generics)(typ.width)
        if not isinstance(width, int):
            width = width.value()
        interface = Unsigned(direction, width)
    elif type(typ) == typs.ConstrainedArray:
        interface = Array(direction, typ, generics)
    else:
        raise Exception('Unsupported type {}'.format(typ))
    return interface


class DutInterface(Record):

    def __init__(self, resolved, entity_name, ignored_ports=None, generics=None):
        entity = resolved['entities'][entity_name]
        self.__dict__['_in_ports'] = set()
        self.__dict__['_out_ports'] = set()
        self.__dict__['_pieces'] = {}
        self.__dict__['_ignored_ports'] = {}
        if ignored_ports is not None:
            for ignored_port in ignored_ports:
                self.__dict__['_ignored_ports'][ignored_port] = None
        for port_name, port in entity.ports.items():
            if (ignored_ports is None) or (port_name not in ignored_ports):
                if port.direction == 'in':
                    self.__dict__['_in_ports'].add(port_name)
                elif port.direction == 'out':
                    self.__dict__['_out_ports'].add(port_name)
                else:
                    raise ValueError('Invalid port direction')
                self.__dict__['_pieces'][port_name] = interface_from_type(
                    port.direction, port.typ, generics)

    def set_from_simulation(self, value):
        if value is None:
            for port_name in self.__dict__['_out_ports']:
                piece = self.__dict__['_pieces'][port_name]
                piece.set(value)
        else:
            for key, sub_value in value.items():
                assert key in self.__dict__['_out_ports']
                piece = self.__dict__['_pieces'][key]
                piece.set(sub_value)

    def update_in(self):
        for port_name in self.__dict__['_in_ports']:
            self.__dict__['_pieces'][port_name].update()

    def update_out(self):
        for port_name in self.__dict__['_out_ports']:
            self.__dict__['_pieces'][port_name].update()

    def lock(self):
        for port_name in self.__dict__['_in_ports']:
            self.__dict__['_pieces'][port_name].lock()

    def unlock(self):
        for port_name in self.__dict__['_in_ports']:
            self.__dict__['_pieces'][port_name].lock()

    def get_inputs(self):
        value = {}
        for port_name in self.__dict__['_in_ports']:
            piece = self.__dict__['_pieces'][port_name]
            value[port_name] = piece.get()
        return value

    def get_outputs(self):
        value = {}
        for port_name in self.__dict__['_out_ports']:
            piece = self.__dict__['_pieces'][port_name]
            value[port_name] = piece.get()
        return value

    def set(self, value):
        if value is None:
            for port_name in self.__dict__['_in_ports']:
                piece = self.__dict__['_pieces'][port_name]
                piece.set(value)
        else:
            for key, sub_value in value.items():
                assert key in self.__dict__['_in_ports']
                piece = self.__dict__['_pieces'][key]
                piece.set(sub_value)

    def __setattr__(self, name, value):
        if name in self.__dict__['_ignored_ports']:
            self.__dict__['_ignored_ports'][name] = value
        else:
            piece = self.__dict__['_pieces'][name]
            piece.set(value)

    def __getattr__(self, name):
        if name in self.__dict__['_ignored_ports']:
            return self.__dict__['_ignored_ports'][name]
        else:
            return self.get_element(name)


class EventLoop(asyncio.AbstractEventLoop):
    """
    An event loop that deals with running our python
    coroutines as well as communicating with the
    ghdl simulation (via the Simulator object).

    We need to make sure that all python coroutines that should be
    called are called before performing the next simulator step.

    This means that we can't use the default asyncio EventLoop and
    we have to create a custom one.

    I don't really know what I'm doing here yet, so this is a pretty
    crappy event loop, with heavy cut-and-paste stack-overflow
    influences.
    """

    def __init__(self, simulator):
        self._immediate = collections.deque()
        self._exc = None
        self.terminated = False
        self.post_terminate_count = 0
        self._running = False
        self.simulator = simulator
        global LOOP
        assert LOOP is None
        LOOP = self
        super().__init__()

    def run_non_simulation_tasks(self):
        while self._immediate:
            h = self._immediate.popleft()
            if not h._cancelled:
                h._run()
            if self._exc is not None:
                if isinstance(self._exc, TerminateException):
                    logger.debug('Terminating')
                    self.terminated = True
                else:
                    raise self._exc

    def run_forever(self):
        global LOOP
        self._running = True
        while True:
            self.run_non_simulation_tasks()
            if self.terminated:
                break
            self.simulator.dut.update_in()
            self.simulator.step()
            self.simulator.dut.update_out()
            ReadOnly.resolve_all()
            self.simulator.dut.lock()
            self.run_non_simulation_tasks()
            if self.terminated:
                break
            RisingEdge.resolve_all()
            self.simulator.dut.unlock()
        #self.cancel_all_tasks()
        #self.run_non_simulation_tasks()
        print(self._immediate)
        LOOP = None

    def call_soon(self, callback, *args, context=None):
        h = asyncio.Handle(callback, args, self)
        self._immediate.append(h)
        return h

    def get_debug(self):
        return False

    def create_task(self, coro):
        async def wrapper():
            try:
                await coro
            except Exception as e:
                logger.debug('Caught exception')
                self._exc = e
        return asyncio.Task(wrapper(), loop=self)

    def call_exception_handler(self, context):
        #logger.warning('context is {}'.format(context))
        logger.warning('messages is {}'.format(context['message']))
        raise Exception(str(list(context.keys())))#context['exception']

    def close(self):
        del self.simulator
        global LOOP
        LOOP = None


class ReadOnly(asyncio.Future):

    all_futures = collections.deque()

    def __init__(self):
        super().__init__(loop=LOOP)
        self.all_futures.append(self)

    @classmethod
    def resolve_all(cls):
        while cls.all_futures:
            future = cls.all_futures.popleft()
            future.set_result(None)


class RisingEdge(asyncio.Future):

    all_futures = collections.deque()

    def __init__(self, signal):
        assert signal == LOOP.simulator.clk_signal
        super().__init__(loop=LOOP)
        self.all_futures.append(self)

    @classmethod
    def resolve_all(cls):
        while cls.all_futures:
            future = cls.all_futures.popleft()
            future.set_result(None)


def gather(*args, **kwargs):
    if 'loop' not in kwargs:
        kwargs['loop'] = LOOP
    return asyncio.gather(*args, **kwargs)
