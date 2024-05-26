# BeepBeep

BeepBeep (named from all the beeping sounds it makes!) is a custom designed PCB and firmware that provides access control. It seamlessly integrates with MemberMatters and allows enabling access control of a door, tool/appliance, or any vending machine that uses a vend relay.

<img src="./hardware/v1.0.1/3D_BeepBeep%20PCB_v1.0.1_2024-05-27.png" width="200px">

## Warning

The hardware and software is in Beta. It may be used with caution, but occasional bugs should be expected.

Before ordering any hardware, you should review the designs and check that they will meet your requirements. We strongly recommend that you order and build a very small batch (1 or 2 devices) to start with. Once you are happy that BeepBeep will meet your needs, only then should you order a larger batch.

By default, BeepBeep doesn't populate the relay/relay connector as it's unlikely to be used much and saves a reasonable amount of cost. Just solder a 5v relay and a connector if you need it.

## Compatibility

The firmware in this repository is exclusively designed to work with the BeepBeep PCB. Whilst this firmware will work with many ESP32 based boards, if you are not using our board, we may not be able to offer help.

The following configuration is currently supported:

- [BeepBeep v1.0.1 PCB](/hardware/v1.0.1/)
    - You can view the OSHWLAB page [here](https://oshwlab.com/member-matters/beepbeep).
    - It is recommended to order boards from JLCPCB using their SMT assembly service.
- BeepBeep v1.x.x firmware
- Micropython v1.22.0

## Getting Started

The first step is to install Micropython onto your ESP32 board. A full tutorial on how to do this is outside the scope of this document, but some quick steps for reference are included below.

1. [Install esptool.py](https://pypi.org/project/esptool/) and download the [appropriate version of Micropython](https://micropython.org/download/ESP32_GENERIC_S3/) for your ESP32-S3 board.

2. Connect your ESP32 board using a USB serial adapter.

3. Before you flash Micropython, you should erase the flash memory.

   Notes: this will erase the offline cache of authorised swipe cards and configuration changes made to `config.py`. Your port may be different, check your operating system (ie `ls /dev/`) to locate your specific serial port.

   ```bash
   esptool.py --chip esp32s3 --port /dev/tty.usbserial-210 erase_flash
   ```

4. Flash the Micropython binary you downloaded earlier by using:
   ```bash
   esptool.py --chip esp32s3 --port /dev/tty.usbserial-210 write_flash -z 0 ESP32_GENERIC_S3-20231227-v1.22.0.bin
   ```

5. Update `config.py` with the correct config for your setup then flash the software to your board using the VS Code plugin "pymakr". Alternatively, use another tool like "ampy".
   NOTE: You can find a list of files to exclude in the `pymakr.conf` file or just use pymakr which automatically does this for you.
