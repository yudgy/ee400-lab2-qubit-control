#pulseblaster driver reformmated for qcodes from pulseblaster.py

from collections.abc import Mapping
import pyvisa
import numpy as np
import math
import qcodes.validators as vals
from typing import Any, ClassVar, Dict

from qcodes.instrument import Instrument, VisaInstrument
from qcodes.utils.delaykeyboardinterrupt import DelayedKeyboardInterrupt
from qcodes.validators import Arrays, ComplexNumbers, Enum, Ints, Numbers, Strings

from qcodes.parameters import (
    ArrayParameter,
    Parameter,
    ParameterWithSetpoints,
    ParamRawDataType,
)

from qt3utils.errors import PulseBlasterInitError, PulseBlasterError, PulseTrainWidthError


import pulseblaster.spinapi
from pulseblaster.PBInd import PBInd

class pulseblasterd(Instrument):
    '''QCoDeS Driver for SpinCore Pulseblaster using the SpinCore API to allow the user to program the pins of the pulseblaster independently of one another. Times are in ns. for rthe pb.on/pb.off functions'''
    def __init__(self, name: str, metadata: Mapping[Any, Any] | None = None, label: str | None = None) -> None:
        super().__init__(name, metadata, label)
        self.pb_board_number = 0
        self.aom_channel     = 0  #for AOM
        self.lock_in_channel = 1  #for lock in
        self.rf_channel      = 23 #for RF modulator

        self.rf_pulse_width = 5e-6
        self.aom_width = 5e-6  #for real life use 5e-6, for oscilliscope use 20e-6
        self.lock_in_width = 2.5e-3 #for the lock in amplifier

        self.t_pad = 1e-6 #sets padding between the RF and laser pules
        self.laser_delay = 0 #sets delay between the laser initalize pulse and readout pulse for the T1 experiment

    def print_parameters(self):
        params = {"laser_delay": self.laser_delay, "lock_in_width": self.lock_in_width,
                "aom_width": self.aom_width, "rf_pulse_width":self.rf_pulse_width}


    def open(self):
        pulseblaster.spinapi.pb_select_board(self.pb_board_number)
        ret = pulseblaster.spinapi.pb_init()
        if ret!= 0:
            self.close() #if opening fails, attempt to close and then raise error
            raise PulseBlasterInitError(f'{ret}: {pulseblaster.spinapi.pb_get_error()}')
        pulseblaster.spinapi.pb_core_clock(100*pulseblaster.spinapi.MHz)

    def close(self):
        ret = pulseblaster.spinapi.pb_close()
        if ret != 0:
            raise PulseBlasterError(f'{ret}: {pulseblaster.spinapi.pb_get_error()}')

    def start(self):
        self.open()
        ret = pulseblaster.spinapi.pb_start()
        if ret !=0:
            raise PulseBlasterError(f'{ret}: {pulseblaster.spinapi.pb_get_error()}')
        self.close()
        
    def stop(self):
        self.open()
        ret = pulseblaster.spinapi.pb_stop()
        if ret != 0:
            raise PulseBlasterError(f'{ret}: {pulseblaster.spinapi.pb_get_error()}')
        self.close()
        
    def reset(self):
        self.open()
        ret = pulseblaster.spinapi.pb_reset()
        if ret != 0:
            raise PulseBlasterError(f'{ret}: {pulseblaster.spinapi.pb_get_error()}')
        self.close()

    def stop_programming(self):
        if pulseblaster.spinapi.pb_stop_programming() != 0:
            raise PulseBlasterError(pulseblaster.spinapi.pb_get_error())
        
    def start_programming(self):
        if pulseblaster.spinapi.pb_start_programming(0) != 0:
            raise PulseBlasterError(pulseblaster.spinapi.pb_get_error())

    #TODO 1: Program a sample pulse        
    def program_samplePulse(self):
        channel_1 = 0                       #channel 1 is OUTPUT PORT 0 on the pulseblaster
        channel_2 = 1                        #channel 2 is OUTPUT PORT 1 on the pulseblaster
        hardware_pins=[channel_1, channel_2] #define which pins we want to program a pulse on.
        
        full_cycle_width = 100e-6             #define the length of a full cycle in seconds

        self.open()                          #open the connection to the pulse blaster
        pb = PBInd(pins = hardware_pins, on_time=int(full_cycle_width*1e9)) #tell it which pins you are programming and the cycle length

        self.start_programming()             #puts the pulse blaster in program mode (if you forget this, it will not update your changes to the device)

        #to turn on a channel for a certain duration of time
        #pb.on(channel name, start time, pulse length (in ns - should be an integer))

        #to turn off a channel for a certain duration of time
        #pb.off(channel name, start time, pulse length (in ns - should be an integer))

        #adjust code below ---------------------------
        
        #turn on channel 1 for the whole cycle duration (on the entire time)
        pb.on(channel_1, 0, int((full_cycle_width / 2)*1e9))
        
        #turn on channel 2 for half the cycle duration (5us)
        pb.on(channel_2, 0, int((full_cycle_width / 2)*1e9))

        #adjust code above ---------------------------

        pb.program([],float('inf')) #set the pulse sequence to repeat forever

        self.stop_programming()   #the pulseblaster stops programming
        self.close()              #end the connection with the pulseblaster - will not be able to reopen until it is closed. Closing it after each use is good practice


    def program_LockinOpticalTest(self): 
        # lock in pulse width: 2.5e-3
        hardware_pins=[self.aom_channel, self.lock_in_channel]
        full_cycle_width = self.lock_in_width*2
        half_cycle_width = full_cycle_width/2

        self.open()
        pb = PBInd(pins = hardware_pins, on_time=int(full_cycle_width*1e9))

        self.start_programming()

        pb.on(self.lock_in_channel, 0, int(self.lock_in_width*1e9))
        pb.on(self.aom_channel,0, int((half_cycle_width/2)*1e9))
        pb.program([],float('inf'))

        self.stop_programming()
        self.close()
    
    def program_CWstate(self): 
        # lock in pulse width: 2.5e-3
        hardware_pins=[self.aom_channel, self.rf_channel, self.lock_in_channel]
        full_cycle_width = self.lock_in_width*2
        half_cycle_width = full_cycle_width/2

        self.open()
        pb = PBInd(pins = hardware_pins, on_time=int(full_cycle_width*1e9))

        self.start_programming()

        pb.on(self.lock_in_channel, 0, int(self.lock_in_width*1e9))
        pb.on(self.aom_channel,0, int(full_cycle_width*1e9))
        pb.on(self.rf_channel, 0, int(half_cycle_width*1e9))
        pb.program([],float('inf'))

        self.stop_programming()
        self.close()

    def program_pulser_stateT1(self):
        #lock in pulse width: 15e-3 s
        #aom_width = 5e-6 s
        hardware_pins=[self.aom_channel, self.lock_in_channel]

        full_cycle_width = self.lock_in_width*2
        half_cycle_width = full_cycle_width/2

        self.open()
        pb = PBInd(pins = hardware_pins, on_time= int(full_cycle_width*1e9))
        self.start_programming()

        pb.on(self.lock_in_channel, 0, int(self.lock_in_width*1e9))
        pb.on(self.aom_channel, 0, int(self.aom_width*1e9))
        pb.on(self.aom_channel, int(half_cycle_width*1e9), int(self.aom_width*1e9))  #add a 2us buffer
        pb.on(self.aom_channel, int((half_cycle_width+self.aom_width+self.laser_delay+(2e-6))*1e9), int(self.aom_width*1e9))
        pb.program([], float('inf'))
        self.stop_programming()
        self.close()

    def program_pulsedODMRstate(self):
        #lock in pulse width: 2.5e-3 s
        #aom_width = 5e-6 s
        #t_padding = 1e-6 s
        #rf_pulse_width = 5e-6 s
        hardware_pins=[self.aom_channel, self.rf_channel, self.lock_in_channel]

        full_cycle_width = self.lock_in_width*2
        half_cycle_width = full_cycle_width/2

        self.open()
        pb = PBInd(pins = hardware_pins, on_time= int(full_cycle_width*1e9))
        laser_rf_cycle = self.aom_width+self.t_pad+ self.rf_pulse_width+self.t_pad
        N = math.floor(self.lock_in_width/laser_rf_cycle)

        self.start_programming()

        pb.on(self.lock_in_channel, 0, int(half_cycle_width*1e9))
        for ii in range (0,N):
           # pb.on(self.aom_channel, int((ii*laser_rf_cycle)*1e9), int(self.aom_width*1e9))
           # pb.on(self.rf_channel, int((laser_rf_cycle*ii+(self.aom_width + self.t_pad))*1e9), int(self.rf_pulse_width*1e9))
           # pb.on(self.aom_channel, int((half_cycle_width+(ii*laser_rf_cycle))*1e9), int(self.aom_width*1e9))
            pb.on(self.rf_channel, int((ii*laser_rf_cycle)*1e9), int(self.rf_pulse_width*1e9))
            pb.on(self.aom_channel, int((laser_rf_cycle*ii+(self.rf_pulse_width + self.t_pad))*1e9), int(self.aom_width*1e9))
            pb.on(self.aom_channel, int((half_cycle_width+laser_rf_cycle*ii+(self.rf_pulse_width + self.t_pad))*1e9), int(self.aom_width*1e9))
        pb.program([],float('inf')) #set the pulse sequence to repeat forever
        self.stop_programming()
        self.close()

    def program_pulsedstateV2(self, max_rf_width):
        #lock in pulse width: 2.5e-3 s
        #aom_width = 5e-6 s
        #t_padding = 1e-6 s
        #rf_pulse_width = 5e-6 s
        hardware_pins=[self.aom_channel, self.rf_channel, self.lock_in_channel]

        full_cycle_width = self.lock_in_width*2
        half_cycle_width = full_cycle_width/2

        self.open()
        pb = PBInd(pins = hardware_pins, on_time= int(full_cycle_width*1e9))
        laser_rf_cycle = self.aom_width+self.t_pad+max_rf_width+self.t_pad
        N = math.floor(self.lock_in_width/laser_rf_cycle)

        self.start_programming()

        pb.on(self.lock_in_channel, 0, int(half_cycle_width*1e9))
        for ii in range (0,N):
            pb.on(self.rf_channel, int((ii*laser_rf_cycle)*1e9), int(self.rf_pulse_width*1e9))
            pb.on(self.aom_channel, int((laser_rf_cycle*ii+(self.rf_pulse_width + self.t_pad))*1e9), int(self.aom_width*1e9))
            pb.on(self.aom_channel, int((half_cycle_width+laser_rf_cycle*ii+(self.rf_pulse_width + self.t_pad))*1e9), int(self.aom_width*1e9))
        pb.program([],float('inf')) #set the pulse sequence to repeat forever
        self.stop_programming()
        self.close()


    def _set_laser_delay(self, laser_delay_in = None):
        if laser_delay_in:
            self.laser_delay = laser_delay_in
        else:
            return self.laser_delay
        
    def _set_lock_in_width(self, lock_in_width = None):
        if lock_in_width:
            self.lock_in_width = lock_in_width
        else:
            return self.lock_in_width
        
    def _set_aom_width(self, aom_width = None):
        if aom_width:
            self.aom_width = aom_width
        else:
            return self.aom_width
        
    def _set_rf_width(self, rf_width = None):
        if rf_width:
            self.rf_pulse_width = rf_width
        else:
            return self.rf_pulse_width
    
    

