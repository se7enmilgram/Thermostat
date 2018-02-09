#! /usr/bin/python
# Thermostat Control
# SJC 2/2018

from Thermostat import Thermostat, ThermostatApp
from time import sleep, time
from splunk_http_event_collector import http_event_collector

IDLE='IDLE'
REST='REST'
HEAT='HEAT'
COOL='COOL'
FAN='FAN'

class State(object):
    state=None
    time=None
    def __init__(self, state, time):
        self.state = state
        self.time = time

state = State(IDLE, None)

ec = http_event_collector('redacted-reda-cted-reda-ctedredacted', 'splunk.hostname')

ta = ThermostatApp(
    token='redacted',
    setpoint=0,
    upper=8,
    lower=9,
    min_run=10,
    max_run=11,
    rest=12,
    away_setpoint=13,
    lcd1=20,
    lcd2=21,
    away_switch=50,
    temp_switch=51,
    heat=75,
    cool=76,
    fan=77,
    hum=126,
    temp=127)

th = Thermostat(
    heat_pin=16, 
    fan_pin=18, 
    cool_pin=22, 
    on_val=0, 
    off_val=1, 
    dht22_pin=25)

def idle():
    state.state = IDLE
    ta.lcd1 = "IDLE"
    ta.lcd2 = ""

def start_heat(t):
    state.state = HEAT
    state.time = time()
    th.heat_on()
    ta.lcd1 = "HEATING"
    ta.lcd2 = "" 
    ta.heat = 1

def stop_heat():
    state.state = IDLE
    th.heat_off()
    ta.lcd1 = "IDLE"
    ta.lcd2 = ""
    ta.heat = 0

def rest(t):
    state.state = REST
    state.time = time()
    th.heat_off()
    ta.lcd1 = "REST"
    ta.lcd2 = ""
    ta.heat = 0

def loop():
    t = th.temp
    h = th.hum
    ta.update()
    ta.temp = t
    ta.hum = h
    if ta.away_switch:
        sp = ta.away_setpoint
    else:
        sp = ta.setpoint
    u = ta.upper
    l = ta.lower
    lower = sp - l
    upper = sp + u
    if state.state == IDLE:
        if t <= lower:
            start_heat(t)
        else:
            pass
    elif state.state == HEAT:
        if time() <= state.time + ta.min_run*60:
            time_left = (state.time + ta.min_run*60) - time()
            ta.lcd2 = int(time_left)
            pass # maintain heat
        elif t >= upper:
            stop_heat()
        elif time() >= state.time + ta.min_run*60:
            # not above upper setpoint but past min runtime
            time_left = (state.time + ta.max_run*60) - time()
            ta.lcd2 = int(time_left)
        elif time() >= state.time + ta.max_run*60:
            rest(t)
    elif state.state == REST:
        if time() <= state.time + ta.rest*60:
            time_left = (state.time + ta.rest*60) - time()
            ta.lcd2 = int(time_left)
            pass # maintain rest
        elif t <= lower:
            start_heat(t)
        elif t >= upper:
            stop_heat()
        elif lower <= t <= upper:
            idle()

    e = {
        'temperature': t,
        'humidity': h,
        'upper': ta.upper,
        'lower': ta.lower,
        'setpoint': sp,
        'heat': ta.heat,
        'cool': ta.cool,
        'fan': ta.fan
    }
    ec.sendEvent({'event': e})

    e = {
        'debug': True,
        'cache_hits': ta._cache_hits,
        'cache_misses': ta._cache_miss,
        'away_switch': ta.away_switch,
        'temp_switch': ta.temp_switch,
        'setpoint': sp,
        'lower': lower,
        'upper': upper
    }
    
    ec.sendEvent({'event': e})
    
    if state.state == IDLE:
        sleep(5)
    else:
        sleep(1)
    
while True:
    loop()