#!/usr/bin/env python3
"""
rudp_server_skeleton.py — STUDENT SKELETON
Goal: Implement a minimal "Reliable UDP" (RUDP) server over UDP.

YOU MUST IMPLEMENT:
  1) 3-way handshake:  SYN -> (you send) SYN-ACK -> (expect) ACK
  2) DATA handling with sequence numbers + send DATA-ACK for each in-order DATA
     - maintain 'expect_seq' (next in-order sequence number you expect)
     - if out-of-order, re-ACK the last in-order seq (expect_seq - 1)
  3) Teardown: (expect) FIN -> (you send) FIN-ACK

Tips:
  - Use Wireshark with filter: udp.port == <your_assigned_port>
  - Keep the server single-client and single-threaded for simplicity.
  - Only accept packets from the first client after handshake begins.
"""
import socket, struct, random, time

# ===================== CONFIG (EDIT YOUR PORT) =====================
ASSIGNED_PORT = 30038  # <-- REPLACE with your assigned UDP port
# ==================================================================

# --- Protocol type codes (1 byte) ---
SYN, SYN_ACK, ACK, DATA, DATA_ACK, FIN, FIN_ACK = 1,2,3,4,5,6,7

# Header format: type(1B) | seq(4B) | len(2B)
HDR = '!B I H'
HDR_SZ = struct.calcsize(HDR)

def pack_msg(tp: int, seq: int, payload: bytes = b'') -> bytes:
    if isinstance(payload, str):
        payload = payload.encode()
    return struct.pack(HDR, tp, seq, len(payload)) + payload

def unpack_msg(pkt: bytes):
    if len(pkt) < HDR_SZ:
        return None, None, b''
    tp, seq, ln = struct.unpack(HDR, pkt[:HDR_SZ])
    return tp, seq, pkt[HDR_SZ:HDR_SZ+ln]

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', ASSIGNED_PORT))
    print(f'[SERVER] Listening on 0.0.0.0:{ASSIGNED_PORT} (UDP)')
    
    client_addr = None
    established = False
    expect_seq = 0  # next in-order DATA seq we expect

    while True:
        pkt, addr = sock.recvfrom(2048)
        tp, seq, pl = unpack_msg(pkt)
        if tp is None:
            continue

        # ============ PHASE 1: THREE-WAY HANDSHAKE ============
        if not established:
            if tp == SYN and client_addr is None:
                client_addr = addr
                print('[SERVER] Received SYN from client:', addr)
                syn_ack_pkt = pack_msg(SYN_ACK, 0)
                sock.sendto(syn_ack_pkt, addr)
                print('[SERVER] Sent SYN-ACK response')

                pkt, addr2 = sock.recvfrom(2048)
                tp2, s2, payload2 = unpack_msg(pkt)
                if addr2 == client_addr and tp2 == ACK:
                    print('[SERVER] Received ACK - Handshake complete')
                    established = True
                    expect_seq = 0
                else:
                    print('[SERVER] Invalid ACK received, handshake failed')
                    client_addr = None
            continue
        # ============================================================

        # Ignore packets from other addresses once a client is set
        if client_addr is not None and addr != client_addr:
            continue

        # ============ PHASE 2: DATA ================================
        if tp == DATA:
            if seq == expect_seq:
                # "Deliver" payload
                try:
                    text = pl.decode(errors='replace')
                except Exception:
                    text = str(pl)
                print(f'[SERVER] DATA seq={seq} len={len(pl)}')
                if text:
                    print(text, end='')

                # Random delay before ACK (100–1000 ms)
                delay_ms = random.randint(100, 1000)
                time.sleep(delay_ms / 1000.0)

                # Send ACK for this seq
                ack_pkt = pack_msg(DATA_ACK, seq)
                sock.sendto(ack_pkt, client_addr)
                print(f'[SERVER] Sent DATA-ACK seq={seq} (delay {delay_ms} ms)')
                expect_seq += 1
            else:
                # Out-of-order/duplicate: re-ACK last in-order
                last_in_order = expect_seq - 1
                if last_in_order < 0:
                    last_in_order = 0
                ack_pkt = pack_msg(DATA_ACK, last_in_order)
                sock.sendto(ack_pkt, client_addr)
                print(f'[SERVER] Re-ACK seq={last_in_order} (received {seq})')
            continue
        # ============================================================

        # ============ PHASE 3: TEARDOWN =============================
        if tp == FIN:
            print('[SERVER] FIN received, closing')
            fin_ack_pkt = pack_msg(FIN_ACK, 0)
            sock.sendto(fin_ack_pkt, client_addr)
            print('[SERVER] Connection closed')
            # Reset state for next client
            established = False
            client_addr = None
            expect_seq = 0
            continue
        # ============================================================

if __name__ == '__main__':
    main()