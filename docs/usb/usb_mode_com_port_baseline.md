# USB mode snapshot: com_port_baseline — 2026-09-11 18:51:30

## lsusb
```text
Bus 003 Device 009: ID 0e8d:0003 MediaTek Inc. MT6227 phone
```

## device nodes
```text
brw-rw---- 1 root disk   8,  0 Sep 11 18:25 /dev/sda
brw-rw---- 1 root disk   8, 16 Sep 11 18:25 /dev/sdb
crw-rw---- 1 root uucp 166,  0 Sep 11 18:45 /dev/ttyACM0
```

## usb-devices
```text
P:  Vendor=0e8d ProdID=0003 Rev=01.00
S:  Manufacturer=Lava E10̚Lav
S:  Product=Lava E10̜Mas
C:  #Ifs= 2 Cfg#= 1 Atr=80 MxPwr=500mA
I:  If#= 0 Alt= 0 #EPs= 2 Cls=0a(data ) Sub=00 Prot=00 Driver=cdc_acm
E:  Ad=01(O) Atr=02(Bulk) MxPS=  64 Ivl=0ms
E:  Ad=81(I) Atr=02(Bulk) MxPS=  64 Ivl=0ms
I:  If#= 1 Alt= 0 #EPs= 1 Cls=02(commc) Sub=02 Prot=01 Driver=cdc_acm
E:  Ad=84(I) Atr=03(Int.) MxPS=  16 Ivl=3ms

```

## lsusb -v (interfaces, filtered; PID=0003)
```text
  idProduct          0x0003 MT6227 phone
  bcdDevice            1.00
      bNumEndpoints           2
      bInterfaceClass        10 CDC Data
      bInterfaceSubClass      0 [unknown]
      bInterfaceProtocol      0 
      iInterface              1 COM(data_if)
      bNumEndpoints           1
      bInterfaceClass         2 Communications
      bInterfaceSubClass      2 Abstract (modem)
      bInterfaceProtocol      1 AT-commands (v.25ter)
      iInterface              2 COM(comm_if)
      bNumEndpoints           2
      bInterfaceClass        10 CDC Data
      bInterfaceSubClass      0 [unknown]
      bInterfaceProtocol      0 
      iInterface              1 COM(data_if)
      bNumEndpoints           1
      bInterfaceClass         2 Communications
      bInterfaceSubClass      2 Abstract (modem)
      bInterfaceProtocol      1 AT-commands (v.25ter)
      iInterface              2 COM(comm_if)
      bNumEndpoints           2
      bInterfaceClass        10 CDC Data
      bInterfaceSubClass      0 [unknown]
      bInterfaceProtocol      0 
      iInterface              1 COM(data_if)
      bNumEndpoints           1
      bInterfaceClass         2 Communications
      bInterfaceSubClass      2 Abstract (modem)
      bInterfaceProtocol      1 AT-commands (v.25ter)
      iInterface              2 COM(comm_if)
```

## dmesg tail
```text
[  134.466731] cdc_ncm 2-1.1:2.0 eth0: register 'cdc_ncm' at usb-0000:00:0d.0-1.1, CDC NCM (NO ZLP), <HOST_MAC_REDACTED>
[  134.547176] usb 2-1.2: new SuperSpeed USB device number 8 using xhci_hcd
[  134.561727] usb 2-1.2: New USB device found, idVendor=05e3, idProduct=0626, bcdDevice= 6.63
[  134.565480] usb 2-1.2: New USB device strings: Mfr=1, Product=2, SerialNumber=0
[  134.565490] usb 2-1.2: Product: USB3.1 Hub
[  134.565494] usb 2-1.2: Manufacturer: GenesysLogic
[  134.568452] hub 2-1.2:1.0: USB hub found
[  134.569314] hub 2-1.2:1.0: 4 ports detected
[  134.597009] cdc_ncm 2-1.1:2.0 enp0s13f0u1u1c2: renamed from eth0
[  134.634769] usb 2-1.3: new SuperSpeed USB device number 9 using xhci_hcd
[  134.649692] usb 2-1.3: New USB device found, idVendor=05e3, idProduct=0749, bcdDevice=15.39
[  134.652144] usb 2-1.3: New USB device strings: Mfr=3, Product=4, SerialNumber=5
[  134.652153] usb 2-1.3: Product: USB3.0 Card Reader
[  134.652157] usb 2-1.3: Manufacturer: Generic
[  134.652160] usb 2-1.3: SerialNumber: <HOST_SERIAL_REDACTED>
[  134.657670] usb-storage 2-1.3:1.0: USB Mass Storage device detected
[  134.658644] scsi host0: usb-storage 2-1.3:1.0
[  135.681502] scsi 0:0:0:0: Direct-Access     Generic  MassStorageClass 1539 PQ: 0 ANSI: 6
[  135.684167] scsi 0:0:0:1: Direct-Access     Generic  MassStorageClass 1539 PQ: 0 ANSI: 6
[  135.888214] sd 0:0:0:0: [sda] Media removed, stopped polling
[  135.897566] sd 0:0:0:0: [sda] Attached SCSI removable disk
[  136.091429] sd 0:0:0:1: [sdb] Media removed, stopped polling
[  136.101610] sd 0:0:0:1: [sdb] Attached SCSI removable disk
[  162.690030] warning: `Socket Thread' uses wireless extensions which will stop working for Wi-Fi 7 hardware; use nl80211
[ 1625.666149] perf: interrupt took too long (2523 > 2500), lowering kernel.perf_event_max_sample_rate to 79000
```
