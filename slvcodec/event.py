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
    analyzed = []
    for filename in filenames:
        if filename not in analyzed:
            subprocess.call(['ghdl', '-a', '--std=08', filename])
            analyzed.append(filename)
    cmd = ['ghdl', '-r', '--std=08', testbench_name]
    dump_wave = True
    if dump_wave:
        cmd.append('--wave=wave.ghw')
    cmd += ['-gPIPE_PATH=' + directory]
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    os.chdir(pwd)
    return process


class Simulator:

    def __init__(self, directory, filenames, top_entity, generics, clk_name='clk'):
        clock_domains = {clk_name: ['.*']}
        generation_directory = os.path.join(directory, 'generated')
        os.makedirs(generation_directory)
        ftb_directory = os.path.join(directory, 'ftb')
        os.makedirs(ftb_directory)

        top_testbench = top_entity + '_tb'

        with_slvcodec_files = add_slvcodec_files(directory, filenames)
        generated_fns, generated_wrapper_fns, resolved = filetestbench_generator.prepare_files(
            directory=ftb_directory, filenames=with_slvcodec_files,
            top_entity=top_entity, use_pipes=True, use_vunit=False,
            clock_domains=clock_domains, default_generics=generics,
        )
        combined_filenames = with_slvcodec_files + generated_fns + generated_wrapper_fns

        os.mkfifo(os.path.join(directory, 'indata_{}.dat'.format(clk_name)))
        os.mkfifo(os.path.join(directory, 'outdata_{}.dat'.format(clk_name)))
        self.process = start_ghdl_process(directory, combined_filenames, top_testbench)

        self.stdout_poll = select.poll()
        self.stdout_poll.register(self.process.stdout, select.POLLIN)

        self.stderr_poll = select.poll()
        self.stderr_poll.register(self.process.stderr, select.POLLIN)

        self.entity = resolved['entities'][top_entity]
        self.in_handle = open(os.path.join(directory, 'indata_{}.dat'.format(clk_name)), 'w')
        self.out_handle = open(os.path.join(directory, 'outdata_{}.dat'.format(clk_name)))
        self.out_width = self.entity.output_width(generics)

        self.clk_name = clk_name
        self.generics = generics
        self.dut = DutInterface(resolved, top_entity, ignored_ports=['clk'])

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
        self.out_handle.close()
        self.in_handle.close()


class Numeric:

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

    def set(self, value):
        assert value in (0, 1, None)
        self.value = value

    def get(self):
        assert self.value in (0, 1, None)
        return self.value

    def __eq__(self, other):
        return self.get() == other
        
    def __ne__(self, other):
        return self.get() != other


class Unsigned(Numeric):
    
    def __init__(self, direction, width):
        self.direction = direction
        self.value = None
        self.max_value = pow(2, width)-1

    def set(self, value):
        assert (value is None) or ((value >=0) and (value <= self.max_value))
        self.value = value

    def get(self):
        assert (self.value is None) or ((self.value >=0) and (self.value <= self.max_value))
        return self.value


class Record:

    def __init__(self, direction, typ):
        self.__dict__['typ'] = typ
        self.__dict__['_pieces'] = {}
        for sub_name, sub_typ in typ.names_and_subtypes:
            self.__dict__['_pieces'][sub_name] = interface_from_type(direction, sub_typ)
        self.__dict__['direction'] = direction

    def __setattr__(self, name, value):
        piece = self.__dict__['_pieces'][name]
        piece.set(value)

    def __getattr__(self, name):
        piece = self.__dict__['_pieces'][name]
        return piece

    def set(self, value):
        for key, sub_value in value.items():
            setattr(self, key, sub_value)

    def get(self):
        value = {}
        for name, piece in self.__dict__['_pieces'].items():
            value[name] = getattr(self, name).get()
        return value

    def get_inputs(self):
        value = {}
        for name, piece in self.__dict__['_pieces'].items():
            if piece.direction == 'in':
                value[name] = piece.get()
        return value

    def __eq__(self, other):
        return self.get() == other
        
    def __ne__(self, other):
        return self.get() != other


def interface_from_type(direction, typ):
    if type(typ) == typs.StdLogic:
        interface = StdLogic(direction)
    elif type(typ) == typs.Record:
        interface = Record(direction, typ)
    elif type(typ) == typs.ConstrainedStdLogicVector:
        interface = Unsigned(direction, typ.width)
    else:
        import pdb
        pdb.set_trace()
    return interface
    


class DutInterface(Record):

    def __init__(self, resolved, entity_name, ignored_ports=None):
        entity = resolved['entities'][entity_name]
        self.__dict__['_in_ports'] = {}
        self.__dict__['_pieces'] = {}
        for port_name, port in entity.ports.items():
            if (ignored_ports is None) or (port_name not in ignored_ports):
                self.__dict__['_in_ports'][port_name] = port
                self.__dict__['_pieces'][port_name] = interface_from_type(port.direction, port.typ)

    def set(self, value):
        for key, sub_value in value.items():
            piece = getattr(self, key)
            assert piece.direction == 'in'
            piece.set(sub_value)

    def set_from_simulation(self, value):
        for key, sub_value in value.items():
            piece = getattr(self, key)
            assert piece.direction == 'out'
            piece.set(sub_value)



class EventLoop(asyncio.AbstractEventLoop):

    def __init__(self, simulator):
        self._immediate = collections.deque()
        self._exc = None
        self.terminated = False
        self._running = False
        self.simulator = simulator
        global LOOP
        assert LOOP is None
        LOOP = self
        super().__init__()

    def run_forever(self):
        self._running = True
        while not self.terminated:
            while self._immediate:
                h = self._immediate.popleft()
                if not h._cancelled:
                    h._run()
                if self._exc is not None:
                    if isinstance(self._exc, TerminateException):
                        logger.debug('Terminating')
                        self.terminated = True
                        break
                    else:
                        raise self._exc
            self.simulator.step()
            NextCycleFuture.resolve_all()

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
        logger.debug('contenxt is {}'.format(context))
        raise context['exception']

    def close(self):
        del self.simulator


class NextCycleFuture(asyncio.Future):

    all_futures = collections.deque()

    def __init__(self):
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
