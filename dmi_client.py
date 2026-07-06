import socket
import struct
import time


# Helper to ensure we get exactly N bytes from the socket
def recv_exactly(sock, n):
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            raise EOFError("Socket closed before receiving enough data")
        data.extend(packet)
    return data


# ── 1. CONNECT ──────────────────────────────────────────────────
HOST = 'localhost'
PORT = 30000
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((HOST, PORT))
print("Connected to Flute debug server")

# ── 2. PROTOCOL HELPERS ─────────────────────────────────────────
# 7-byte request packet: op (1 byte) + addr (2 bytes) + data (4 bytes)
# Response: 4 bytes of data

def dmi_read(addr):
    # op=1 (READ), addr=2 bytes, data=4 bytes (0 for read)
    pkt = struct.pack('<BHI', 1, addr, 0)
    sock.sendall(pkt)
    # Use the helper to guarantee we get all 4 bytes
    resp = recv_exactly(sock, 4)
    return struct.unpack('<I', resp)[0]


def dmi_write(addr, data):
    # 7-byte packet: op=2 (WRITE), addr = 2 bytes, data = 4 bytes
    pkt = struct.pack('<BHI', 2, addr, data)
    sock.sendall(pkt)

def read_pc():
    # 1. Write the command to read the PC (GPR register access)
    # The command 0x00220000 is for reading GRPs (x0-x31)
    # 0x17 is the command register!
    dmi_write(0x17, 0x002207b1)

    # 2. Add a busy-wait check (Check 'abstractcs' register at 0x16)
    # Bit 12 of abstractcs is 'busy'. Wait while it is 1.
    while (dmi_read(0x16) & (1 << 12)):
        pass # Busy wait


    # 3. CHECK FOR ERRORS
    # Read abstractcs (0x16) to check for errors
    status = dmi_read(0x16)
    # The error filed is typically bits 8-10 of abstractcs
    err_field = (status >> 8) & 0x7
    if err_field != 0:
        print(f"DEBUG: Hardware returned error code {err_field} in abstractcs (0x16)")
    
    # 4. Read the PC value from the data register (0x04)
    pc_val = dmi_read(0x04)
    return pc_val

# verify register values as we run!
def verify_register(reg_name, actual_value, expected_value):
    if expected_value is None:
        print(f"{reg_name} actual value: 0x{actual_value:08x}")
    elif actual_value == expected_value:
        print(f"{reg_name} verification passed: 0x{actual_value:08x}")
    else:
        print(f"{reg_name} verification FAILED: expected 0x{expected_value:08x}, got 0x{actual_value:08x}") 
# ── 3. DO SOMETHING USEFUL ──────────────────────────────────────

# Write 0x700 to abstractcs to clear cmderr field (write-1-to-clear)
dmi_write(0x16, 0x00000700)
# 1. HALT the processor first
print("Sending HALT command...")
dmi_write(0x10, 0x80000001)
time.sleep(0.1)  # Give it a moment to process

# 2. Wait until dmstatus (0x11) shows the processor is actually halted
# Bit 9 is typically the 'halted' bit 

while not (dmi_read(0x11) & (1 << 9)):
    pass  # Wait until the processor is halted

print("Processor successfully halted!")

# Example: read the DM status register (DMI addr 0x10)
val_before = dmi_read(0x10)
print(f"DM status register: 0x{val_before:08x}")

# WRITE to dmcontrol (0x10) to Resume
# 0x40000001 sets resumereq (bit 30) and dmactive (bit 0)

print("Sending RESUME command...")
dmi_write(0x10, 0x40000001)
time.sleep(0.1)  # Give it a moment to process
while (dmi_read(0x11) & (1 << 9)):
    pass  # Wait until the processor is resumed

# Poll the status again to see if it changed
new_val = dmi_read(0x11)
print(f"Post-Resume DM status register: 0x{new_val:08x}")

# 4. HALT the processor again
print("Sending HALT command...")
dmi_write(0x10, 0x80000001)
time.sleep(0.1)  # Give it a moment to process

while not (dmi_read(0x11) & (1 << 9)):
    pass
print("Processor halted again for test suite!")

dmi_write(0x16, 0x00000700)
# Define your test suite
test_suite = [
    {"name": "DM Control", "addr": 0x10, "expected": 0x00000001},
    {"name": "Program Counter", "addr": 0x04, "expected": None}
]

# Run the loop
for test in test_suite:
    # Special case: If it is the PC, use the new read function
    if test["name"] == "Program Counter":
        actual = read_pc()
    else:
        actual = dmi_read(test["addr"])

    verify_register(test["name"], actual, test["expected"])

# ── 5. DISCONNECT ───────────────────────────────────────────────
sock.close()
print("Done")