import socket
import struct


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


def verify_register(reg_name, actual_value, expected_value):
    if actual_value == expected_value:
        print(f"{reg_name} verification passed: 0x{actual_value:08x}")
    else:
        print(f"{reg_name} verification failed: expected 0x{expected_value:08x}, got 0x{actual_value:08x}")


# ── 3. DO SOMETHING USEFUL ──────────────────────────────────────
# Example: read the DM status register (DMI addr 0x10)

val_before = dmi_read(0x10)
print(f"DM status register: 0x{val_before:08x}")

# WRITE to dmcontrol (0x10) to Resume
# 0x40000001 sets resumereq (bit 30) and dmactive (bit 0)
print("Sending RESUME command...")
dmi_write(0x10, 0x00000001)

# Poll the status again to see if it changed
new_val = dmi_read(0x11)
print(f"Post-Resume DM status register: 0x{new_val:08x}")

# Define your test suite
test_suite = [
    {"name": "DM Status", "addr": 0x11, "expected": 0x00000c82},
    {"name": "DM Control", "addr": 0x10, "expected": 0x00000001}
]

# Run the loop
for test in test_suite:
    actual = dmi_read(test["addr"])
    verify_register(test["name"], actual, test["expected"])

# ── 4. DISCONNECT ───────────────────────────────────────────────
sock.close()
print("Done")