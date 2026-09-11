# LAVA E10 Documentation

Documentation and experiments for the Lava E10 USB and AT-command interface.

## Documents

- [Main investigation](docs/overview/info.md)
- [AT probe results](docs/at-probes/at_results.md)
- [AT probe phase 2](docs/at-probes/at_results2.md)
- [AT probe phase 3](docs/at-probes/at_results3.md)
- [AT probe phase 4](docs/at-probes/at_results4.md)
- [AT probe phase 4b](docs/at-probes/at_results4b.md)
- [AT probe phase 6](docs/at-probes/at_results6.md)
- [USB mode overview](docs/usb/usb_modes.md)
- [USB COM-port baseline](docs/usb/usb_mode_com_port_baseline.md)
- [USB mass-storage capture](docs/usb/usb_mode_mass_storage.md)
- [TekBuster analysis](docs/analysis/tekbuster_analysis.md)
- [URC capture results](docs/analysis/urc_capture_result.md)

## SMS demo

Native sender:

```bash
python3 scripts/sms/sms_native.py <PHONE_NUMBER> "HELLO"
```

Web interface:

```bash
python3 scripts/sms/sms_web.py
```

Open `http://localhost:8000`.

## Layout

- `docs/` — documentation and probe results
- `scripts/` — reusable probe, USB, call, and SMS tools
- `captured-output/` — raw logs and captured command output
