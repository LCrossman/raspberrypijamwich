from machine import ADC, Pin
import time

adc = ADC(Pin(26))

while True:
   val = adc.read_u16()
   print(val) 
   time.sleep(0.8)
