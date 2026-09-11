# USB mode snapshot: mass_storage — 2026-09-11 18:54:21

## lsusb
```text
Bus 003 Device 010: ID 0e8d:0002 MediaTek Inc. phone (mass storage mode) [Doro Primo 413]
```

## device nodes
```text
brw-rw---- 1 root disk 8,  0 Sep 11 18:25 /dev/sda
brw-rw---- 1 root disk 8, 16 Sep 11 18:25 /dev/sdb
brw-rw---- 1 root disk 8, 32 Sep 11 18:52 /dev/sdc
```

## usb-devices
```text
P:  Vendor=0e8d ProdID=0002 Rev=01.00
S:  Manufacturer=Lava E10̚Lav
S:  Product=Lava E10̜Mas
S:  SerialNumber=<USB_SERIAL_REDACTED>
C:  #Ifs= 1 Cfg#= 1 Atr=80 MxPwr=500mA
I:  If#= 0 Alt= 0 #EPs= 2 Cls=08(stor.) Sub=06 Prot=50 Driver=usb-storage
E:  Ad=01(O) Atr=02(Bulk) MxPS=  64 Ivl=0ms
E:  Ad=81(I) Atr=02(Bulk) MxPS=  64 Ivl=0ms

```

## lsusb -v (interfaces, filtered; PID=0002)
```text
  idProduct          0x0002 phone (mass storage mode) [Doro Primo 413]
  bcdDevice            1.00
      bNumEndpoints           2
      bInterfaceClass         8 Mass Storage
      bInterfaceSubClass      6 SCSI
      bInterfaceProtocol     80 Bulk-Only
      iInterface              1 Mass Storage 
      bNumEndpoints           2
      bInterfaceClass         8 Mass Storage
      bInterfaceSubClass      6 SCSI
      bInterfaceProtocol     80 Bulk-Only
      iInterface              1 Mass Storage 
      bNumEndpoints           2
      bInterfaceClass         8 Mass Storage
      bInterfaceSubClass      6 SCSI
      bInterfaceProtocol     80 Bulk-Only
      iInterface              1 Mass Storage 
```

## dmesg tail
```text
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
[ 1781.787814] usb 3-2: USB disconnect, device number 9
[ 1794.694172] usb 3-2: new full-speed USB device number 10 using xhci_hcd
[ 1794.819863] usb 3-2: New USB device found, idVendor=0e8d, idProduct=0002, bcdDevice= 1.00
[ 1794.822606] usb 3-2: New USB device strings: Mfr=2, Product=3, SerialNumber=4
[ 1794.822616] usb 3-2: Product: Lava E10̜Mas
[ 1794.822622] usb 3-2: Manufacturer: Lava E10̚Lav
[ 1794.822626] usb 3-2: SerialNumber: <USB_SERIAL_REDACTED>
[ 1794.826850] usb-storage 3-2:1.0: USB Mass Storage device detected
[ 1794.827934] scsi host1: usb-storage 3-2:1.0
[ 1795.840460] scsi 1:0:0:0: Direct-Access     Lava E10                       PQ: 0 ANSI: 0 CCS
[ 1795.844281] sd 1:0:0:0: [sdc] Media removed, stopped polling
[ 1795.857397] sd 1:0:0:0: [sdc] Attached SCSI removable disk
```
