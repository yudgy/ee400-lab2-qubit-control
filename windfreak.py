#windfreak

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
from typing import Any


class windfreak(VisaInstrument):
    '''QCoDeS driver for the Windfreak MW Signal Generator'''

    def __init__(self, name: str, address: str, timeout: float = 5, terminator: str | None = None, device_clear: bool = True, visalib: str | None = None, pyvisa_sim_file: str | None = None, **kwargs: Any):
        super().__init__(name, address, timeout, terminator, device_clear, visalib, pyvisa_sim_file, **kwargs)

        self.add_parameter('set_channel',
                           get_cmd='C?',
                           set_cmd='C{}',
                           label= 'Set Channel',
                           docstring='set the channel under control where x=0=channel0=RFoutA and where x=1=channel1=RFoutB'
                           )
        
        self.add_parameter('set_freq',
                           get_cmd='f?',
                           set_cmd='f{:.7f}',
                           label='Set Freq in MHz',
                           unit='MHz',
                           docstring='Frequency is settable between 53.0MHz and 13999.9999999MHz'
                           )
        
        self.add_parameter('set_power_dBm',
                           get_cmd= 'W?',
                           set_cmd='W{:.3f}',
                           label='set RF power in dBm',
                           unit='dBm',
                           docstring='RF power is settable between -60dBm and +20dBm depending on frequency. Calibrating will occur automatically and set power as close as it can get to what is requested'
                           )
        
        self.add_parameter('calib_complete',
                           get_cmd='V',
                           label='Query for successful calibration routine upon freq or amplitude set',
                           docstring='Queries if there was a successful calibration. 1= success, 0= failure'
                           )
        
        #to turn the RF output on/off -> essentially need h1r1E1
        self.add_parameter('set_RF_mute',
                           get_cmd='h?',
                           set_cmd='h{}',
                           docstring='mutes the output power without powering: x=1=not muted and x=0=muted')    

        self.add_parameter('set_PA_on',
                           get_cmd='r?',
                           set_cmd='r{}',
                           docstring='this commmand along with the PLL on, are used to toggle output RF on/off: x=1=powered on and x=0=powered off')
        
        self.add_parameter('set_PLL_on',
                           get_cmd='E?',
                           set_cmd='E{}',
                           docstring='This and the PA command turn the output RF on/off: x=0=powered off and x=1=powered on')
        
        #pulse commands 
        self.add_parameter('pulse_on_time',
                           get_cmd='P?',
                           set_cmd='P{}',
                           label='Pulse on time',
                           unit='uS',
                           docstring='sets the pulse modulation on time in microseconds. Range is 1uS to 10,000,000 uS (10 sec)'
                           )
        
        self.add_parameter('pulse_off_time',
                           get_cmd='O?',
                           set_cmd='O{}',
                           label='Pulse off time',
                           unit='uS',
                           docstring='sets the pulse modulation off time in microseconds. Range is 2uS to 10,000,000 uS (10 sec)'
                           )
        
        self.add_parameter('pulse_num',
                           get_cmd='R?',
                           set_cmd='R{}',
                           label='Pulse Number of Repetitions in a burst',
                           docstring='Sets the Pulse Modulation number of repetitions in a burst. Range is 1 to 65500. Burst size is used when mixed with other functions like stepping. It is possible to sweep and for every step in the sweep generate the given number of Pulse On/Off cycles in the burst'
                           )

        self.add_parameter('run_pulse_mod_cont',
                           get_cmd='j?',
                           set_cmd='j{}',
                           docstring='starts continuous pulse amplitude modulation')
        
        #TODO: make functions for on/off - have to make a set of functions using this driver elsewhere
    def on(self):
        self.set_PA_on(1)
        self.set_PLL_on(1)
        self.set_RF_mute(1)

    def off(self):
        self.set_PA_on(0)
        self.set_PLL_on(0)
        self.set_RF_mute(0)