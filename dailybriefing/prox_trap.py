import asyncio
from bleak import BleakScanner, BleakClient

async def main():
    print("Setting the Proximity Trap...")
    print("Make sure the printer is physically touching (or inches from) the Pi.")
    print("Turn the printer ON now...\n")
    
    target_device = None

    # This callback fires on every single BLE packet in the air
    def detection_callback(device, advertisement_data):
        nonlocal target_device
        
        # -35 dBm is incredibly loud. Only a device right next to the antenna can hit this.
        if device.rssi > -35 and target_device is None:
            print(f"🚨 TRAP TRIGGERED! Physics caught a device at {device.rssi} dBm")
            print(f"Current Burner MAC: {device.address}")
            target_device = device

    scanner = BleakScanner(detection_callback=detection_callback)
    await scanner.start()

    # The script waits here indefinitely until the trap catches something
    while target_device is None:
        await asyncio.sleep(0.1)

    # The millisecond it's caught, we stop scanning and attack
    await scanner.stop()
    print("\nInitiating immediate connection to the burner address...")
    
    try:
        # We pass the caught device object directly to the client
        async with BleakClient(target_device, timeout=10.0) as client:
            print("✅ SUCCESS! The shapeshifter has been cornered.")
            print("\nReading internal services:")
            services = await client.get_services()
            for service in services:
                print(f" - {service.uuid}")
    except Exception as e:
        print(f"\nConnection dropped: {e}")

asyncio.run(main())
