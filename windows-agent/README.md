# PrintX Windows Print Controller Agent

The Windows Print Controller is a native Python service that runs on Windows 11 and directly interfaces with the Windows Print Spooler subsystem via `pywin32` and `SumatraPDF CLI`.

---

## 🚀 Features

- **Automatic Printer Discovery:** Uses `win32print.EnumPrinters` to detect installed printers, locating the physical **HP Smart Tank 585** (`HP Smart Tank 580-590 series`) or falling back to `Microsoft Print to PDF` for zero-waste local development.
- **Headless PDF Printing:** Constructs safe, deterministic SumatraPDF CLI arguments enforcing A4, copies (1-10), grayscale/color, custom page ranges, and strict simplex (single-sided).
- **Spooler Queue Telemetry:** Monitors Windows spooler job progress via `win32print.EnumJobs` and detects printer errors (Paper Out, Paper Jam, Offline, Paused).
- **Security & Authorization Guard:** Independently verifies payment status with the central backend before releasing any document to physical paper.
- **Idempotency & Duplicate Prevention:** Maintains a local persistent store of processed jobs (`data/processed_jobs.json`) to prevent replay attacks and accidental duplicate printing.

---

## 🛠️ Usage

To launch the agent on Windows 11:

```powershell
cd windows-agent
.\run-agent.ps1
```

