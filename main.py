import os, board, busio, digitalio, keypad, sdcardio, storage
import audiobusio, audiomp3, audiomixer
import displayio, i2cdisplaybus, terminalio, adafruit_displayio_ssd1306
from adafruit_display_text import label

# SD card (SPI0)
spi = busio.SPI(board.GP18, MOSI=board.GP19, MISO=board.GP16)
storage.mount(storage.VfsFat(sdcardio.SDCard(spi, board.GP17)), "/sd")
tracks = sorted(f for f in os.listdir("/sd")
                if f.lower().endswith(".mp3") and not f.startswith("."))

# OLED (I2C0)
displayio.release_displays()
i2c = busio.I2C(scl=board.GP1, sda=board.GP0)
disp = adafruit_displayio_ssd1306.SSD1306(
    i2cdisplaybus.I2CDisplayBus(i2c, device_address=0x3C), width=128, height=64)
grp = displayio.Group()
txt = label.Label(terminalio.FONT, text="", x=0, y=10, scale=1)
grp.append(txt)
disp.root_group = grp

# LEDs
led_play = digitalio.DigitalInOut(board.GP14)
led_pwr = digitalio.DigitalInOut(board.GP15)
for l in (led_play, led_pwr):
    l.direction = digitalio.Direction.OUTPUT
led_pwr.value = True

# Buttons: Play/Pause, Next, Prev, Vol+, Vol-
keys = keypad.Keys((board.GP2, board.GP3, board.GP4, board.GP5, board.GP6),
                   value_when_pressed=False, pull=True)

# Audio (I2S): BCLK=GP10, LRC=GP11 (must be consecutive), DIN=GP9
audio = audiobusio.I2SOut(board.GP10, board.GP11, board.GP9)

idx, vol, paused, mixer = 0, 0.5, False, None


def show(extra=""):
    name = tracks[idx][:-4][:21] if tracks else "No tracks"
    txt.text = "%d/%d\n%s\nVol %d%% %s" % (
        idx + 1, len(tracks), name, int(vol * 100), extra)


def play(i):
    global idx, mixer, paused
    idx = i % len(tracks)
    audio.stop()
    mp3 = audiomp3.MP3Decoder(open("/sd/" + tracks[idx], "rb"))
    mixer = audiomixer.Mixer(sample_rate=mp3.sample_rate,
                             channel_count=mp3.channel_count,
                             bits_per_sample=16, samples_signed=True)
    audio.play(mixer)
    mixer.voices[0].level = vol
    mixer.voices[0].play(mp3, loop=False)
    paused = False
    show()


def set_vol(v):
    global vol
    vol = min(1.0, max(0.0, v))
    if mixer:
        mixer.voices[0].level = vol
    show("PAUSED" if paused else "")


if tracks:
    play(0)
else:
    show()

while True:
    e = keys.events.get()
    if e and e.pressed and tracks:
        k = e.key_number
        if k == 0:
            if paused:
                audio.resume()
            else:
                audio.pause()
            paused = not paused
            show("PAUSED" if paused else "")
        elif k == 1:
            play(idx + 1)
        elif k == 2:
            play(idx - 1)
        elif k == 3:
            set_vol(vol + 0.1)
        elif k == 4:
            set_vol(vol - 0.1)
    if tracks and mixer and not paused and not mixer.voices[0].playing:
        play(idx + 1)
    led_play.value = bool(mixer and mixer.voices[0].playing and not paused)