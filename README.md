# raspberrypijamwich
Python coding for Raspberry Pi


Daily briefing:

You can find these scripts in the daily briefing folder:

These are both Python scripts: prox_trap.py helps you attach to the catprinter and checks all your setup is working

briefing.py will provide your briefing on the printer's thermal paper.

briefing.py
prox_trap.py

The cat printer I used for thermal printing in these scripts is [click here](https://www.amazon.co.uk/gp/product/B0CWGYQX41/ref=ewc_pr_img_1?smid=A1UEZQEM257NU6&psc=1) at present £12.49

If purchasing another cat printer for this, you would need to find one that uses rolls of thermal paper and *NOT* sticker paper


Biosonification:

You can find these scripts in the biosonification folder:

measure_water.py 

This code needs to be run on the raspberry Pi pico2. 
It is in micropython and is for sensing electrical signals from moisture readings from a capacitive moisture sensor

pico_midi_bridge.py 

This code can be run on raspberry Pi 5.
It is in Python and is for collecting data sent from raspberry pi Pico2 and scaling the readings into notes we can hear
