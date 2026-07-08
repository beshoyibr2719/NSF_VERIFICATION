import socket
import struct
import time
import json


# Helper to ensure we get exactly N bytes from the socket
def recv_exactly(sock, n):
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            raise EOFError("Socket closed before receiving enough data")
        data.extend(packet)
    return data

# Functiion to wait for the processor to halt, with a timeout
def wait_for_halted(max_attempts=1000):
    for i in range(max_attempts):
        if (dmi_read(0x11) & (1 << 9)):
            return True # Successfully halted
        time.sleep(0.01) # Small delay to give the hardware breathing room
    
    # If the loop finishes without returning, it timed out
    raise TimeoutError("Timed out waiting for processor to halt!")

# Function to wait for the processor to resume, with a timeout
def wait_for_ready(max_attempts=1000):
    for i in range(max_attempts):
        # Bit 12 of abstractcs is 'busy'
        if not (dmi_read(0x16) & (1 << 12)):
            print("Processor successfully resumed!")
            return True 
        time.sleep(0.01)
    raise TimeoutError("Timed out waiting for abstractcs 'busy' bit to clear!")

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

    try:
        wait_for_ready()
    except TimeoutError as e:
        print(f"CRITICAL ERROR: {e}")
        sock.close()
        exit(1)

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


def read_abstract_reg(regno):
    # 1. Write the command to 0x17 (Command Register)
    # cmdtype (bits 24-31) = 0 (Access Register)
    # regno (bits 0-15) = regno
    cmd = 0x00000000 | (regno & 0xFFFF) 
    dmi_write(0x17, cmd)
    
    # 2. Wait for completion (using your existing robust helper!)
    try:
        wait_for_ready()
    except TimeoutError as e:
        print(f"Error: {e}")
        return None

    # 3. Read the data from 0x04 (Data Register)
    return dmi_read(0x04)

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
# Bit 9 is typically the 'halted' bit, if not after 1000 attempts, timed out
try:
    wait_for_halted()
    print("Processor successfully halted!")
except TimeoutError as e:
    print(f"CRITICAL ERROR: {e}")
    sock.close()
    exit(1) # Stop the script immediately


# Verify that the processor actually halted
status = dmi_read(0x11)
verify_register("Halt State", (status >> 9) & 1, 1) # Expect bit 9 to be 1

print("Processor successfully halted!")

# Example: read the DM status register (DMI addr 0x10)
val_before = dmi_read(0x10)
print(f"DM status register: 0x{val_before:08x}")

# WRITE to dmcontrol (0x10) to Resume
# 0x40000001 sets resumereq (bit 30) and dmactive (bit 0)

print("Sending RESUME command...")
dmi_write(0x10, 0x40000001)
time.sleep(0.1)  # Give it a moment to process

# Verify that the processor is actually running (bit 9 is 0)
status_post_resume = dmi_read(0x11)
verify_register("Resume State", (status_post_resume >> 9) & 1, 0)


# Poll the status again to see if it changed
new_val = dmi_read(0x11)
print(f"Post-Resume DM status register: 0x{new_val:08x}")

# 4. HALT the processor again
print("Sending HALT command...")
dmi_write(0x10, 0x80000001)
time.sleep(0.1)  # Give it a moment to process

try:
    wait_for_halted()
    print("Processor successfully halted!")
except TimeoutError as e:
    print(f"CRITICAL ERROR: {e}")
    sock.close()
    exit(1) # Stop the script immediately
print("Processor halted again for test suite!")

# Verify halt after the second command
status_rehalt = dmi_read(0x11)
verify_register("Re-Halt State", (status_rehalt >> 9) & 1, 1)


dmi_write(0x16, 0x00000700)

# Verify error field (bits 8-10) is 0
abs_status = dmi_read(0x16)
err_field = (abs_status >> 8) & 0x7
verify_register("AbstractCS Error Field", err_field, 0)


# ── 4. LOAD EXTERNAL TEST SUITE ─────────────────────────────────
try:
    with open('tests.json', 'r') as f:
        test_suite = json.load(f)
    print("Test suite loaded successfully.")
except FileNotFoundError:
    print("Error: tests.json not found!")
    exit(1)

# Run the loop
for test in test_suite:
    # Clean dispatch based on register range
    # 0x1000 (4096) is the base for GPRs
    if test["addr"] >= 4096:
        actual = read_abstract_reg(test["addr"])
    elif test["name"] == "Program Counter":
        actual = read_pc()
    else:
        actual = dmi_read(test["addr"])
    
    verify_register(test["name"], actual, test["expected"])


# ── 5. INTERACTIVE INSPECTION (TEST MODE) ───────────────────────
print("\n--- Interactive Debug Mode ---")
print("Enter register ID (e.g., 4097 for x1, 4098 for x2) or 'q' to quit.")

while True:
    choice = input("Enter Register ID (or addr) or 'q' to quit: ")
    if choice.lower() == 'q':
        break
    
    try:
        addr = int(choice)
        # DECISION LOGIC:
        # If it's a DMI register (0x10, 0x11, 0x16, 0x17)
        if addr < 0x1000:
            val = dmi_read(addr)
            print(f"DMI Reg 0x{addr:02x} Value: 0x{val:08x}")
        # If it's an Abstract/GPR register (x0-x31 are 0x1000+)
        else:
            val = read_abstract_reg(addr)
            print(f"Abstract Reg 0x{addr:04x} Value: 0x{val:08x}")
            
    except ValueError:
        print("Invalid input.")

# ── 6. DISCONNECT ───────────────────────────────────────────────
sock.close()
print("Done")