This project is a custom Python-based verification tool for a RISC-V processor. It uses a TCP-based debug client to communicate directly with the hardware, allowing us to pause, resume, and inspect CPU registers in real-time, making automated testing much faster and more reliable.

RISC-V Debug Client

This repository houses the custom debug interface I've been building for our RISC-V processor project for my NSF research in the 2026 summer!

Why does this exist?
Instead of relying on manual checks or slow, bloated debugging tools, I built this Python client to talk directly 
to the processor's Debug Module via a TCP socket. 

This allows the user to:

Control the CPU: Easily pause and resume execution.

Inspect State: Read and write to internal registers (like the Program Counter/ dmstatus) on the fly.

Automate Testing: Run a suite of tests and verify outcomes automatically, so we don't have 
to check everything by hand which would be VERY tedious.

Getting Started
You'll need the simulation running with the debug module enabled. The client connects to localhost on port 30000.

I’ve included a simple test suite in the script—just run it, and it will automatically verify the processor's status for you. 
I'm currently working on adding more registers and expanding our automated test coverage!

Built for our hardware verification research—keeping it simple and effective.

### Register Map

| Register Name | DMI Address | Description |
| `data`        | `0x04`   | Data register used to retrieve values (e.g., PC). |

| `dmcontrol`   | `0x10`   | Used for processor control (Halt/Resume commands). |

| `dmstatus`    | `0x11`   | Used to poll processor status (e.g., bit 9 for halted state).  |

| `abstractcs`  | `0x16`   | Used to check for command errors and monitor the "busy" status.  |

| `command` | `0x17`       | Used to send commands to the processor (e.g., reading GPRs/PC). |





