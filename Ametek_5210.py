import pyvisa
import numpy as np
import qcodes.validators as vals
from typing import ClassVar, Dict

from qcodes.instrument import VisaInstrument
from qcodes.utils.delaykeyboardinterrupt import DelayedKeyboardInterrupt
from qcodes.validators import Arrays, ComplexNumbers, Enum, Ints, Numbers, Strings

from qcodes.parameters import (
    ArrayParameter,
    Parameter,
    ParameterWithSetpoints,
    ParamRawDataType,
)

#TODO: Need to verify that the queries work without the "?". For example, now I am using "MAG" instead of "MAG?"

class Ametek5210(VisaInstrument):
    """
    QCoDeS driver for the Ametek Dual Phase Model 5210 Lock-in Amplifier.
    """

    """ 
    The following in commands are included in this driver.
    
    ATC, DR, EX, F2F, FF, FLT, 
    FRQ, G, IE, LF, MP, N, NN, P, 
    PHA, SEN, TC, TRIG, XDB, XTC, MAG   
    """
    
    SENSITIVITY: ClassVar[Dict[str, int]] = {
        '100 nV': 0,
        '300 nV': 1,
        '1 uV': 2,
        '3 uV': 3,
        '10 uV': 4,
        '30 uV': 5,
        '100 uV': 6,
        '300 uV': 7,
        '1 mV': 8,
        '3 mV': 9,
        '10 mV': 10,
        '30 mV': 11,
        '100 mV': 12,
        '300 mV': 13,
        '1 V': 14,
        '3 V': 15} 
    
    TIME_CONSTANT: ClassVar[Dict[str, int]] = {
        '1 ms': 0,
        '3 ms': 1,
        '10 ms': 2,
        '30 ms': 3,
        '100 ms': 4,
        '300 ms': 5,
        '1 s': 6,
        '3 s': 7,
        '10 s': 8,
        '30 s': 9,
        '100 s': 10,
        '300 s': 11,
        '1 ks': 12,
        '3 ks': 13}

    # Initialization and methods of the Princeton Instruments Ametek Model5210 instrument
    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, terminator="\r", **kwargs)
        
        # SIGNAL CHANNEL COMMANDS
        self.add_parameter('sensitivity',
                            get_cmd='SEN?',
                            set_cmd='SEN {}', 
                            label='Sensitivity',
                            unit='nV to V',  # Adjusting the unit based on the actual sensitivity range
                            val_mapping =  self.SENSITIVITY,
                            docstring='Controls the full-scale sensitivity of the lock-in amplifier.')
        
        self.add_parameter('vernier_gain',
                            get_cmd='G?',
                            set_cmd='G {n1} {n2}', #TODO: This needs to be fixed to be able to set values. The get works fine though
                            label='Vernier Gain Control',
                            #get_parser=float,
                            vals = vals.Numbers(min_value=0, max_value=255),
                            docstring='Sets or reads the status and gain of the signal-channel gain vernier control.')
        
        
        # SIGNAL CHANNEL FILTERS
        self.add_parameter('filter_operator',
                            get_cmd='FLT?', 
                            set_cmd='FLT {}',
                            val_mapping={
                                'FLAT': 0,
                                'NOTCH': 1,
                                'LB': 2,
                                'BP': 3
                            },
                            docstring='Controls the signal-channel filter mode.')
        
        self.add_parameter('ff_tuning_mode',
                            get_cmd='ATC?',
                            set_cmd='ATC {}',
                            val_mapping={
                                'manual': 0,
                                'automatic': 1
                            },
                            docstring='Controls the filter frequency tuning mode.')
        
        self.add_parameter('filter_frequency',
                            get_cmd='FF?',
                            set_cmd='FF {} {}', #TODO: This needs to be fixed to be able to set values.
                            unit='Hz',
                            docstring='Controls the filter filtering band.')
        
        self.add_parameter('frequency_rejection',
                            get_cmd='LF?',
                            set_cmd='LF {}',
                            get_parser=int,
                            docstring='Control the signal channel line frequency rejection filter control.')
        
        # REFERENCE CHANNEL
        self.add_parameter('channel_source',
                            get_cmd='IE?', 
                            set_cmd='IE {}',
                            val_mapping={
                                'EXT': 0,
                                'INT': 1},
                            docstring='Controls the channel source.')

        self.add_parameter('harmonic_mode',
                            get_cmd='F2F?', 
                            set_cmd='F2F {}', 
                            get_parser=int,
                            docstring='Controls the harmonic mode.')
        
        self.add_parameter('reference_phase',
                            get_cmd='P?',
                            set_cmd='P {} {}',  #TODO: This needs to be fixed to be able to set values.
                            get_parser=float,
                            unit = 'Degrees',
                            docstring='Controls the phase quadrants.'
                            )
        
        self.add_parameter('frequency',
                            label='Reference Frequency',
                            get_cmd='FRQ.',
                            get_parser=float,
                            unit='mHz',
                            vals = vals.Numbers(),
                            docstring="Gets frequency in mHz. This is only a getter.")
        
        #SIGNAL CHANNEL OUTPUT FILTERS
        self.add_parameter('output_filters',
                            get_cmd='XDB?',
                            set_cmd='XDB {}',
                            label='Filter Slope',
                            unit='dB/octave',
                            get_parser=float,
                            val_mapping={
                                6: 0,
                                12: 1},
                            docstring='Sets or reads the slope of the output filters according to the hashtable.')
        
        self.add_parameter('time_constant',
                            get_cmd='TC?',
                            set_cmd='TC {}',
                            unit='s',
                            label='time constant',
                            val_mapping=self.TIME_CONSTANT,
                            docstring='Output filter time constant.')
        
        self.add_parameter('dynamic_reserve',
                            get_cmd='DR?',
                            set_cmd='DR {}',
                            val_mapping={
                                'HI STAB': 0,
                                'NORM': 1,
                                'HI RES': 2},
                            docstring='Set or reads the instrumets dynamic reserve.')
        
        self.add_parameter('expansion_control',
                            get_cmd='EX?',
                            set_cmd='EX {}',
                            val_mapping={
                                'Off': 0,
                                '10X': 1},
                            label='Output expansion control',
                            docstring='Sets or reads the X-channel output expansion mode.')
        
        #INSTRUMENT OUTPUTS
        self.add_parameter('magnitude',
                            get_parser=float,
                            get_cmd='MAG.',
                            label='Magnitude',
                            unit='V',
                            vals = vals.Numbers(),
                            docstring='Magnitude of input signal. This is only a getter.')
        
        self.add_parameter('signal_phase',
                            get_parser=float,
                            get_cmd='PHA.',
                            label='Signal phase',
                            unit='Degrees',
                            vals = vals.Numbers(),
                            docstring='Responds with the signal phase in millidegrees.')
        
        self.add_parameter('magnitude_and_phase',
                            get_cmd='MP.',
                            label='MAG and Phase',
                            vals = vals.Numbers(),
                            docstring='This is equivalent to the compound command MAG;PHA.')
           
        self.add_parameter('noise',
                            get_cmd='NN.',
                            label='Noise Output',
                            vals = vals.Numbers(),
                            docstring='This will cause the lock-in to respond with the noise. This is only a getter.')
        
        #AUXILIARY INPUTS
        self.add_parameter('trig',
                            get_cmd='TRIG?',
                            set_cmd='TRIG {}',
                            val_mapping={
                                    'Reference': 0,
                                    'External': 1, 
                                    'Asynchronous': 2, 
                                    'Ratio': 4,
                                    '8F': 8},
                            docstring='Sets or reads the trigger mode of the ADC converter.')                  
        
        #COMPUTER INTERFACES
        self.add_parameter('overload_byte',
                            get_cmd='N?',
                            label='Report overload byte',
                            docstring='Will cause the lock-in to respond with the overload byte. This is only a getter.')
    
    
    def get_idn(self):
        """
        Support for generic VISA '*IDN?' query.

        Returns:
            A dict containing vendor, model, serial, and firmware.
        """
        vendor = 'Ametek'
        model = self.ask('ID')
        serial = self.ask('NAME').strip()
        firmware = self.ask('VER')

        return dict(zip(('vendor', 'model', 'serial', 'firmware'), [vendor, model, serial, firmware]))
