# python Thermostat and ThermostatApp class
# SJC 2/2018

"""
Thermostat
this class represents all of the rigging and associated IO for a DIY 
thermostat you should be able to subclass this object to override the hard 
coded behaviors for your own purpose. 

It assumes a series of pins that can be set on and off to call for 
heat/cool/fan and a dht22 sensor, and that its running on a raspberry pi.
Following the common Honeywell HVAC systems I'm most familiar with, there
are calls for heat, cooling, and operating the fan. 

based on reading, I'm told this mechanism of thermostat control is called a
"bang bang", I believe because the metaphorical needle bangs against the 
ceiling, then bangs against the floor, and that back and forth determines
the states during which it calls for heating / cooling.

the class is intended to be an instrumentation interface for the hardware, 
in order to make the control logic that uses it be very legible and clear.

the class also implements a set of modifier parameters intended to be set 
from outside the basic control code, for purposes of researching machine 
learning algorithms as related to home HVAC systems, for people who are too
cheap // too curious to just buy a friggin' box for $300 that already does it

ThermostatApp
this class presents an interface for communicating with an outside control 
surface, in our case a Blynk application. The hope for our case is that we
can keep the implementation specific peanut butter out of our more general
purpose logic chocolate. We'll see how it goes. There will be many cases where
we pass the Thermostat object into a function on the App object in order to 
harvest values from it and update the Blynk application.
"""

class Thermostat( object ):
    def __init__(self, 
        heat_pin = -1,
        cool_pin = -1,
        fan_pin = -1,
        dht22_pin = -1,
        on_val = -1,
        off_val = -1,
        pin_mode = -1,
        ):
        import RPi.GPIO as GPIO
        self.heat_pin = heat_pin
        self.cool_pin = cool_pin
        self.fan_pin = fan_pin
        self.dht22_pin = dht22_pin
        self.ON_V = on_val
        self.OFF_V = off_val
        self.pin_mode = pin_mode
        
        # the sensor only generates good information every two seconds
        # we will cache the value until at least two seconds have passed
        self.dht22_last_read = -1
        self.dht22_temp = -1
        self.dht22_hum = -1
        
        #setup gpio pins
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        pins = [self.heat_pin,
                self.cool_pin,
                self.fan_pin]
        GPIO.setup(pins, GPIO.OUT)
        GPIO.output(pins, self.OFF_V)

    def set_pin(self, pin, val):
        import RPi.GPIO as GPIO
        GPIO.output(pin, val)
    
    def get_pin(self, pin):
        import RPi.GPIO as GPIO
        return GPIO.input(pin)
    
    def heat_on(self):
        self.set_pin(self.heat_pin, self.ON_V)
    
    def heat_off(self):
        self.set_pin(self.heat_pin, self.OFF_V)
    
    @property
    def heat(self):
        return self.get_pin(self.heat_pin)
    
    def cool_on(self):
        self.set_pin(self.cool_pin, self.ON_V)
    
    def cool_off(self):
        self.set_pin(self.cool_pin, self.OFF_V)
    
    @property
    def cool(self):
        return self.get_pin(self.cool_pin)
    
    def fan_on(self):
        self.set_pin(self.fan_pin, self.ON_V)
    
    def fan_off(self):
        self.set_pin(self.fan_pin, self.OFF_V)
    
    @property
    def fan(self):
        return self.get_pin(self.fan_pin)
    
    def read_dht22(self):
        from Adafruit_DHT import read_retry
        from time import time
        if (time() - self.dht22_last_read) >= 2:
            h,t = read_retry(22, self.dht22_pin)
            self.dht22_last_read = time()
            self.dht22_temp = t
            self.dht22_hum = h
    
    @property
    def temp(self):
        self.read_dht22()
        return (self.dht22_temp*1.8)+32
    
    @property
    def tempc(self):
        self.read_dht22()
        return self.dht22_temp
    
    @property
    def hum(self):
        self.read_dht22()
        return self.dht22_hum
    
    def shutdown( self ):
        import RPi.GPIO as GPIO
        #bail out function - turns off all the relays
        pins = [self.heat_pin,
                self.cool_pin,
                self.fan_pin]
        GPIO.setup(pins, GPIO.OUT)
        GPIO.output(pins, self.OFF_V)

class ThermostatApp( object ):
    def __init__(self, token=None,
                 setpoint=None,
                 upper=None,
                 lower=None,
                 min_run=None,
                 max_run=None,
                 rest=None,
                 away_setpoint=None,
                 lcd1=None,
                 lcd2=None,
                 away_switch=None,
                 temp_switch=None,
                 heat=None,
                 cool=None,
                 fan=None,
                 hum=None,
                 temp=None,
                 cache=5
                 ):
        from blynkapi import Blynk
        self.token = token
        self._project=Blynk(token=token)
        self._pin_setpoint=self._make_pin(setpoint)
        self._pin_upper=self._make_pin(upper)
        self._pin_lower=self._make_pin(lower)
        self._pin_min_run=self._make_pin(min_run)
        self._pin_max_run=self._make_pin(max_run)
        self._pin_rest=self._make_pin(rest)
        self._pin_away_setpoint=self._make_pin(away_setpoint)
        self._pin_lcd1=self._make_pin(lcd1)
        self._pin_lcd2=self._make_pin(lcd2)
        self._pin_away_switch=self._make_pin(away_switch)
        self._pin_temp_switch=self._make_pin(temp_switch)
        self._pin_heat=self._make_pin(heat)
        self._pin_cool=self._make_pin(cool)
        self._pin_fan=self._make_pin(fan)
        self._pin_temp=self._make_pin(temp)
        self._pin_hum=self._make_pin(hum)
        self.cache = cache
        self._cache = {}
        self._cache_hits = 0
        self._cache_miss = 0
    
    def _make_pin(self, pin):
        from blynkapi import Blynk
        return Blynk(pin='V{}'.format(pin), token=self.token)
    
    def _blynk_write(self, pin, value):
        from requests import get
        url = 'http://blynk-cloud.com/{}/update/{}'
        get(url.format(self.token,pin),params={'value':value})
    
    def _cache_get(self, pinobj):
        from time import time
        pin = pinobj.pin
        if pin in self._cache:
            if time() <= self._cache[pin]['time'] + self.cache:
                #cache is not expired, return val
                self._cache_hits += 1
                return self._cache[pin]['val']
        self._cache_miss += 1
        val = pinobj.get_val()
        self._cache[pin] = {
            'time': time(),
            'val': val
        }
        return val
    
    def update( self ):
        from time import time
        widgets = self._project.get_project()
        widgets = widgets['widgets']
        widgets = [i for i in widgets if 'pin' in i]
        for w in widgets:
            self._cache['V{}'.format(w['pin'])] = {
                'time': time(),
                'val': [w['value']]
            }
    
    @property
    def setpoint(self):
        return int(self._cache_get(self._pin_setpoint)[0])
    
    @setpoint.setter
    def setpoint(self, value):
        self._pin_setpoint.set_val([value])
    
    @property
    def upper(self):
        return int(self._cache_get(self._pin_upper)[0])
    
    @upper.setter
    def upper(self, value):
        self._pin_upper.set_val([value])
    
    @property
    def lower(self):
        return int(self._cache_get(self._pin_lower)[0])
    
    @lower.setter
    def lower(self, value):
        self._pin_lower.set_val([value])
    
    @property
    def min_run(self):
        return int(self._cache_get(self._pin_min_run)[0])
    
    @min_run.setter
    def min_run(self, value):
        self._pin_min_run.set_val([value])
    
    @property
    def max_run(self):
        return int(self._cache_get(self._pin_max_run)[0])
    
    @max_run.setter
    def max_run(self, value):
        self._pin_max_run.set_val([value])
    
    @property
    def rest(self):
        return int(self._cache_get(self._pin_rest)[0])
    
    @rest.setter
    def rest(self, value):
        self._pin_rest.set_val([value])
    
    @property
    def away_setpoint(self):
        return int(self._cache_get(self._pin_away_setpoint)[0])
    
    @away_setpoint.setter
    def away_setpoint(self, value):
        self._pin_away_setpoint.set_val([value])
    
    @property
    def lcd1(self):
        return str(self._cache_get(self._pin_lcd1)[0])
    
    @lcd1.setter
    def lcd1(self, value):
        if self.away_switch:
            value = 'AWAY:' + value
        self._blynk_write(self._pin_lcd1.pin,value)
    
    @property
    def lcd2(self):
        return str(self._cache_get(self._pin_lcd2)[0])
    
    @lcd2.setter
    def lcd2(self, value):
        self._blynk_write(self._pin_lcd2.pin,value)
    
    @property
    def away_switch(self):
        return int(self._cache_get(self._pin_away_switch)[0])
    
    @away_switch.setter
    def away_switch(self, value):
        self._pin_away_switch.set_val([value])
    
    @property
    def temp_switch(self):
        return int(self._cache_get(self._pin_temp_switch)[0])
    
    @temp_switch.setter
    def temp_switch(self, value):
        self._pin_temp_switch.set_val([value])
    
    @property
    def heat(self):
        return int(self._cache_get(self._pin_heat)[0])
    
    @heat.setter
    def heat(self, value):
        if value > 0:
            value = 255
        self._pin_heat.set_val([value])
    
    @property
    def cool(self):
        return float(self._cache_get(self._pin_cool)[0])
    
    @cool.setter
    def cool(self, value):
        if value > 0:
            value = 255
        self._pin_cool.set_val([value])
    
    @property
    def fan(self):
        return int(self._cache_get(self._pin_fan)[0])
    
    @fan.setter
    def fan(self, value):
        if value > 0:
            value = 255
        self._pin_fan.set_val([value])
    
    @property
    def hum(self):
        return float(self._cache_get(self._pin_hum)[0])
    
    @hum.setter
    def hum(self, value):
        self._pin_hum.set_val([value])
    
    @property
    def temp(self):
        return float(self._cache_get(self._pin_temp)[0])
    
    @temp.setter
    def temp(self, value):
        self._pin_temp.set_val([value])
    
