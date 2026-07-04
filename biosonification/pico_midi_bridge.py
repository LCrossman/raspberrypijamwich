import time
import serial
import mido

PICO_SERIAL_PORT='/dev/ttyACM0'
MIDI_OUTPUT_PORT='FLUID Synth (Qsynth1):Synth input port (Qsynth1:0) 129:0'

def scale_value(value, from_min, from_max, to_min, to_max):
   from_span = from_max - from_min
   to_span = to_max - to_min
   value_scaled = float(value - from_min) / float(from_span)
   return int(to_min + (value_scaled * to_span))

last_note_played = -1
try:
   print("starting midi range")
   pico = serial.Serial(PICO_SERIAL_PORT, baudrate=115200, timeout=1)
   midi_out = mido.open_output(MIDI_OUTPUT_PORT)
   midi_out.send(mido.Message('program_change', channel=0, program=46))
   print("successfully connected to both ports!")
   line=pico.readline().decode('utf8').strip()
   print("line", line)
   while line:
     line=pico.readline().decode('utf8').strip()
     print(line)
     sensor_value = line.rstrip()
     note_to_play = scale_value(int(sensor_value), 0, 65535, 25, 100)
     print("note is ", note_to_play)
     midi_out.send(mido.Message('note_on', note=note_to_play,velocity=100))
     #time.sleep(0.1)
     midi_out.send(mido.Message('note_off', note=note_to_play,velocity=100))
     print("it played")
   #note_to_play = scale_value(sensor_value, 0, 65535, 60, 84)
   #midi_out.send(mido.Message('note_on', note=note,velocity=100))
   #time.sleep(0.4)
   #midi_out.send(mido.Message('note_off', note=note,velocity=100))
except Exception as e:
   print("wrong, ", e)
