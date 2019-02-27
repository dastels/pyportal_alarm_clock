"""
PyPortal based alarm clock.

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2019 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

#pylint:disable=redefined-outer-name,no-member,global-statement

import time
import json
import board
from adafruit_pyportal import PyPortal
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.text_area import TextArea
import analogio
import displayio
from secrets import secrets

alarm_hour = 20
alarm_minute = 57

LOCATION = 'America/Toronto'
WEATHER_LOCATION='London,ca'
# Set up where we'll be fetching data from
DATA_SOURCE = 'http://api.openweathermap.org/data/2.5/weather?q='+WEATHER_LOCATION
DATA_SOURCE += '&appid='+secrets['openweather_token']
# You'll need to get a token from openweather.org, looks like 'b6907d289e10d714a6e88b30761fae22'
DATA_LOCATION = []



pyportal = PyPortal(url=DATA_SOURCE,
                    json_path=DATA_LOCATION,
                    status_neopixel=board.NEOPIXEL)

light = analogio.AnalogIn(board.LIGHT)

main_background_day = 'main_background_day.bmp'
main_background_night = 'main_background_night.bmp'
alarm_file = 'computer-alert20.wav'
alarm_interval = 5.0
icon_file = None
icon_sprite = None

refresh_time = None
update_time = None
sound_alarm_time = None
weather_refresh = None

low_light = False
celcius = secrets['celcius']

####################
# Functions

def load_fonts():
    time_font_name = '/fonts/Anton-Regular-104.bdf'
    alarm_font_name = '/fonts/Helvetica-Bold-36.bdf'
    temperature_font_name = '/fonts/Arial-16.bdf'

    time_font = bitmap_font.load_font(time_font_name)
    time_font.load_glyphs(b'0123456789:') # pre-load glyphs for fast printing

    alarm_font = bitmap_font.load_font(alarm_font_name)
    alarm_font.load_glyphs(b'0123456789:')

    temperature_font = bitmap_font.load_font(temperature_font_name)
    temperature_font.load_glyphs(b'0123456789C')

    return alarm_font, time_font, temperature_font

def create_text_areas(configs):
    text_areas = []
    for cfg in configs:
        textarea = TextArea(cfg['font'], text=' '*cfg['size'])
        textarea.x = cfg['x']
        textarea.y = cfg['y']
        textarea.color = cfg['color']
        pyportal.splash.append(textarea)
        text_areas.append(textarea)
    return text_areas

def alarm_sounding():
    return not sound_alarm_time is None

def start_alarm():
    global sound_alarm_time
    sound_alarm_time = time.monotonic()

def snooze():
    print('Snoozing')

def stop_alarm():
    global sound_alarm_time
    sound_alarm_time = None


def check_and_handle_alarm(now, alarm_hour, alarm_minute):
    minutes_now = now.tm_hour * 60 + now.tm_min
    minutes_alarm = alarm_hour * 60 + alarm_minute
    if minutes_now == minutes_alarm and not alarm_sounding():
        start_alarm()

def adjust_backlight_based_on_light(force=False):
    global low_light
    if light.value <= 1000 and (force or not low_light):
        pyportal.set_backlight(0.01)
        pyportal.set_background(main_background_night)
        low_light = True
    elif light.value >= 2000 and (force or low_light):
        pyportal.set_backlight(1.00)
        pyportal.set_background(main_background_day)
        low_light = False

####################
# Buttons

def alarm_settings():
    pass

def poke_mugsy():
    pass

buttons = [dict(left=0, top=50, right=80, bottom=120, func=alarm_settings),
           dict(left=0, top=155, right=80, bottom=220, func=poke_mugsy)]

def process_touch(touch):
    stop_alarm()         # If the alarm is sounding, touching anywhere will stop it
    for button in buttons:
        if (button.left <= touch.x <= button.right and


####################
# And... go

alarm_font, time_font, temperature_font = load_fonts()
text_area_configs = [dict(x=88, y=30, size=5, color=0xFFFFFF, font=time_font),
                     dict(x=210, y=10, size=5, color=0xFF0000, font=alarm_font),
                     dict(x=88, y=65, size=6, color=0xFFFFFF, font=temperature_font)]
text_areas = create_text_areas(text_area_configs)
icon_group = displayio.Group(max_size=1)
icon_group.x = 88
icon_group.y = 20

for ta in text_areas:
    pyportal.splash.append(ta)
pyportal.splash.append(icon_group)

text_areas[1].text = '%2d:%02d' % (alarm_hour, alarm_minute) # set time textarea

adjust_backlight_based_on_light(force=True)

while True:
    # grab the current "time" which will be used later
    now = time.monotonic()

    # Handle touch input first to be as responsive as possible
    process_touch(pyportal.touchscreen.touch_point)

    # only query the online time once per hour (and on first run)
    if (not refresh_time) or (now - refresh_time) > 3600:
        try:
            print('Getting time from internet!')
            pyportal.get_local_time(location=LOCATION)
            refresh_time = now
        except RuntimeError as e:
            print('Some error occured, retrying! -', e)
            continue

    # only query the weather every 10 minutes (and on first run)
    if (not weather_refresh) or (now - weather_refresh) > 600:
        try:
            value = pyportal.fetch()
            print("Response is", value)
            weather = json.loads(value)

            # set the icon/background
            weather_icon = weather['weather'][0]['icon']
            try:
                icon_group.pop()
            except IndexError:
                pass
            filename = "/icons/"+weather_icon+".bmp"
            if filename:
                if icon_file:
                    icon_file.close()
                icon_file = open(filename, "rb")
                icon = displayio.OnDiskBitmap(icon_file)
                icon_sprite = displayio.TileGrid(icon,
                                                 pixel_shader=displayio.ColorConverter(),
                                                 position=(0, 0))

                icon_group.append(icon_sprite)
                board.DISPLAY.refresh_soon()
                board.DISPLAY.wait_for_frame()

            temperature = weather['main']['temp'] - 273.15 # its...in kelvin
            print(temperature)
            if celcius:
                temperature_text = '%3d C' % round(temperature)
            else:
                temperature_text = '%3d F' % round(((temperature * 9 / 5) + 32))
            print(temperature_text)
            text_areas[2].text = temperature_text
            weather_refresh = now
        except RuntimeError as e:
            print("Some error occured, retrying! -", e)
            continue

    if (not update_time) or (now - update_time) > 30:
        the_time = time.localtime()
        text_areas[0].text = '%02d:%02d' % (the_time.tm_hour,the_time.tm_min) # set time textarea

    adjust_backlight_based_on_light()
    check_and_handle_alarm(the_time, alarm_hour, alarm_minute)

    if sound_alarm_time and (now - sound_alarm_time) > alarm_interval:
        sound_alarm_time = now
        pyportal.play_file(alarm_file)
