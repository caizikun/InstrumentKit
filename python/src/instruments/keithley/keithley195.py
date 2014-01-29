#!/usr/bin/python
# -*- coding: utf-8 -*-
##
# keithley195.py: Driver for the Keithley 195 multimeter.
##
# © 2013-2014 Steven Casagrande (scasagrande@galvant.ca).
#
# This file is a part of the InstrumentKit project.
# Licensed under the AGPL version 3.
##
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
##

## FEATURES ####################################################################

from __future__ import division

## IMPORTS #####################################################################

import time
from flufl.enum import Enum, IntEnum
import struct

import quantities as pq
import numpy as np

from instruments.abstract_instruments import Multimeter

## CLASSES #####################################################################

class Keithley195(Multimeter):
    '''
    The Keithley 195 is a 5 1/2 digit auto-ranging digital multimeter. You can 
    find the full specifications list in the `user's guide`_.
    
    Example usage:
    
    >>> import instruments as ik
    >>> import quantities as pq
    >>> dmm = ik.keithley.Keithley195.open_gpibusb('/dev/ttyUSB0', 12)
    >>> print dmm.measure(dmm.Mode.resistance)
    
    .. _user's guide: http://www.keithley.com/data?asset=803
    '''

    def __init__(self, filelike):
        super(Keithley195, self).__init__(filelike)
        self.sendcmd('YX') # Removes the termination CRLF 
                           # characters from the instrument

    ## ENUMS ##
    
    class Mode(IntEnum):
        voltage_dc = 0
        voltage_ac = 1
        resistance = 2
        current_dc = 3
        current_ac = 4
        
    class TriggerMode(IntEnum):
        talk_continuous = 0
        talk_one_shot = 1
        get_continuous = 2
        get_one_shot = 3
        x_continuous = 4
        x_one_shot = 5
        ext_continuous = 6
        ext_one_shot = 7
        
    ## PROPERTIES ##    
        
    @property
    def mode(self):
        '''
        Gets/sets the measurement mode for the Keithley 195. The base model
        only has DC voltage and resistance measurements. In order to use AC
        voltage, DC current, and AC current measurements your unit must be 
        equiped with option 1950.
        
        Example use:
        
        >>> import instruments as ik
        >>> dmm = ik.keithley.Keithley195.open_gpibusb('/dev/ttyUSB0', 12)
        >>> dmm.mode = dmm.Mode.resistance
        
        :type: `Keithley195.Mode`
        '''
        return self.parse_status_word(self.get_status_word())['mode']
    @mode.setter
    def mode(self, newval):
        if isinstance(newval, str):
            newval = self.Mode[newval]
        if newval not in Keithley195.Mode:
            raise TypeError("Mode must be specified as a Keithley195.Mode "
                            "value, got {} instead.".format(newval))
        self.sendcmd('F{}DX'.format(newval.value))
        
    @property
    def trigger_mode(self):
        """
        Gets/sets the trigger mode of the Keithley 195.
        
        There are two different trigger settings for four different sources.
        This means there are eight different settings for the trigger mode.
        
        The two types are continuous and one-shot. Continuous has the instrument
        continuously sample the resistance. One-shot performs a single
        resistance measurement.
        
        The three trigger sources are on talk, on GET, and on "X". On talk 
        refers to addressing the instrument to talk over GPIB. On GET is when
        the instrument receives the GPIB command byte for "group execute 
        trigger". On "X" is when one sends the ASCII character "X" to the 
        instrument. This character is used as a general execute to confirm 
        commands send to the instrument. In InstrumentKit, "X" is sent after
        each command so it is not suggested that one uses on "X" triggering.
        Last, is external triggering. This is the port on the rear of the 
        instrument. Refer to the manual for electrical characteristics of this
        port.
        
        :type: `Keithley195.TriggerMode`
        """
        return self.parse_status_word(self.get_status_word())['trigger']
    @trigger_mode.setter
    def trigger_mode(self, newval):
        if isinstance(newval, str):
            newval = Keithley195.TriggerMode[newval]
        if newval not in Keithley195.TriggerMode:
            raise TypeError('Drive must be specified as a ' 
                            'Keithley195.TriggerMode, got {} '
                            'instead.'.format(newval))
        self.sendcmd('T{}X'.format(newval.value))
    
    @property
    def relative(self):
        """
        Gets/sets the zero command (relative measurement) mode of the 
        Keithley 195.
        
        As stated in the manual: The zero mode serves as a means for a baseline
        suppression. When the correct zero command is send over the bus, the 
        instrument will enter the zero mode, as indicated by the front panel
        ZERO indicator light. All reading displayed or send over the bus while
        zero is enabled are the difference between the stored baseline adn the 
        actual voltage level. For example, if a 100mV baseline is stored, 100mV
        will be subtracted from all subsequent readings as long as the zero mode
        is enabled. The value of the stored baseline can be as little as a few 
        microvolts or as large as the selected range will permit.
        
        See the manual for more information.
        
        :type: `bool`
        """
        return self.parse_status_word(self.get_status_word())['relative']
    @relative.setter
    def relative(self, newval):
        if not isinstance(newval, bool):
            raise TypeError('Relative mode must be a boolean.')
        self.sendcmd('Z{}DX'.format(int(newval)))
        
    ## METHODS ##
    
    def measure(self, mode=None):
        '''
        Instruct the Keithley 195 to perform a one time measurement. The 
        instrument will use default parameters for the requested measurement.
        The measurement will immediately take place, and the results are 
        directly sent to the instrument's output buffer.
        
        Method returns a Python quantity consisting of a numpy array with the
        instrument value and appropriate units.
        
        Example usage:
    
        >>> import instruments as ik
        >>> import quantities as pq
        >>> dmm = ik.keithley.Keithley195.open_gpibusb('/dev/ttyUSB0', 12)
        >>> print dmm.measure(dmm.Mode.resistance)
        
        :param mode: Desired measurement mode. This must always be specified
            in order to provide the correct return units.
        :type mode: `Keithley195.Mode`
        :rtype: `~quantities.quantity.Quantity`
        '''
        #self.mode = mode
        #time.sleep(0.1)
        value = self.query('')
        return float(value[4:]) * UNITS[value[1:4]]
        
    def get_status_word(self):
        """
        Retreive the status word from the instrument. This contains information
        regarding the various settings of the instrument.
        
        The function `~Keithley195.parse_status_word` is designed to parse
        the return string from this function.
        
        :rtype: `str`
        """
        return self.query('U0DX')
        
    def parse_status_word(self, statusword):
        """
        Parse the status word returned by the function
        `~Keithley195.get_status_word`.
        
        Returns a `dict` with teh following keys:
        ``{trigger,mode,range,eoi,buffer,rate,srqmode,relative,delay,multiplex,
        selftest,dataformat,datacontrol,filter,terminator}``
        
        :param statusword: Byte string to be unpacked and parsed
        :type: `str`
        
        :rtype: `dict`
        """
        if statusword[:3] != '195':
            raise ValueError('Status word starts with wrong prefix, expected '
                             '195, got {}'.format(statusword))
        
        (trigger, function, input_range, eoi, buf, rate, srqmode, relative, \
         delay, multiplex, selftest, data_fmt, data_ctrl, filter_mode, \
         terminator) = struct.unpack('@4c2s3c2s5c2s', statusword[4:])
        
        return { 'trigger': Keithley195.TriggerMode[int(trigger)],
                 'mode': Keithley195.Mode[int(function)],
                 'range': input_range,
                 'eoi': (eoi == '1'),
                 'buffer': buf,
                 'rate': rate,
                 'srqmode': srqmode,
                 'relative': (relative == '1'),
                 'delay': delay,
                 'multiplex': (multiplex == '1'),
                 'selftest': selftest,
                 'dataformat': data_fmt,
                 'datacontrol': data_ctrl,
                 'filter': filter_mode,
                 'terminator': terminator }
    
    def trigger(self):
        '''
        Tell the Keithley 195 to execute all commands that it has received.
        
        Do note that this is different from the standard SCPI \*TRG command
        (which is not supported by the 195 anyways).
        '''
        self.sendcmd('X')
        
    def set_voltage_dc_range(self, voltage='AUTO'):
        '''
        Manually set the voltage DC range of the Keithley 195.
        
        :param voltage: Voltage DC range. One of 
            ``{AUTO|20e-3|200e-3|2|20|200|1000}``
        :type: `str` or `int`
        '''
        if isinstance(voltage, str):
            voltage = voltage.lower()
            if voltage == 'auto':
                voltage = 0
            else:
                raise ValueError('Only valid string for voltage range '
                    'is "auto".')
        elif isinstance(voltage, float) or isinstance(voltage, int):
            valid = [20e-3, 200e-3, 2, 20, 200, 1000]
            if voltage in valid:
                voltage = valid.index(voltage) + 1
            else:
                raise ValueError('Valid voltage ranges are: ' + str(valid))
        else:
            raise TypeError('Instrument voltage range must be specified as '
                'a float, integer, or string.')
            
        self.sendcmd('R{}X'.format(voltage))
    
    def set_voltage_ac_range(self, voltage='AUTO'):
        '''
        Manually set the voltage AC range of the Keithley 195.
        
        :param voltage: Voltage AC range. One of 
            ``{AUTO|20e-3|200e-3|2|20|200|700}``
        :type: `str` or `int`
        '''
        if isinstance(voltage,str):
            voltage = voltage.lower()
            if voltage == 'auto':
                voltage = 0
            else:
                raise ValueError('Only valid string for voltage range '
                    'is "auto".')
        elif isinstance(voltage, float) or isinstance(voltage, int):
            valid = [20e-3, 200e-3, 2, 20, 200, 700]
            if voltage in valid:
                voltage = valid.index(voltage) + 1
            else:
                raise ValueError('Valid voltage ranges are: ' + str(valid))
        else:
            raise TypeError('Instrument voltage range must be specified as '
                'a float, integer, or string.')
            
        self.sendcmd('R{}X'.format(voltage))
            
    def set_current_range(self, current='AUTO'):
        '''
        Manually set the current range of the Keithley 195.
        
        :param current: Current range. One of 
            ``{AUTO|20e-6|200e-6|2e-3|20e-3|200e-3|2}``
        :type: `str` or `int`
        '''
        if isinstance(current, str):
            current = current.lower()
            if current == 'auto':
                current = 0
            else:
                raise ValueError('Only valid string for current range '
                    'is "auto".')
        elif isinstance(current, float) or isinstance(current, int):
            valid = [20e-6, 200e-6, 2e-3, 20e-3, 200e-3, 2]
            if current in valid:
                current = valid.index(current) + 1
            else:
                raise ValueError('Valid current ranges are: ' + str(valid))
        else:
            raise TypeError('Instrument current range must be specified as '
                'a float, integer, or string.')
            
        self.sendcmd('R{}X'.format(current))
            
    def set_resistance_range(self, res='AUTO'):
        '''
        Manually set the resistance range of the Keithley 195.
        
        :param res: Resistance range. One of 
            ``{AUTO|20|200|2000|20e3|200e3|2e6|20e6}``
        :type: `str` or `int`
        '''
        if isinstance(res,str):
            res = res.lower()
            if res == 'auto':
                res = 0
            else:
                raise ValueError('Only valid string for resistance range '
                    'is "auto".')
        elif isinstance(res, float) or isinstance(res, int):
            valid = [20, 200, 2000, 20e3, 200e3, 2e6, 20e6]
            if res in valid:
                res = valid.index(res) + 1
            else:
                raise ValueError('Valid resistance ranges are: ' + str(valid))
        else:
            raise TypeError('Instrument resistance range must be specified '
                'as a float, integer, or string.')
            
        self.sendcmd('R{}X'.format(res))
            
    def auto_range(self):
        '''
        Turn on auto range for the Keithley 195. 
        
        This is the same as calling the associated set_[function]_range method
        and setting the parameter to "AUTO".
        '''
        self.sendcmd('R0X')
            
## UNITS #######################################################################

UNITS = {
    'DCV':  pq.volt,
    'ACV':  pq.volt,
    'ACA':  pq.amp,
    'DCA':  pq.amp,
    'OHM':  pq.ohm,
}            
        
