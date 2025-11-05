#!/usr/bin/env python3
"""
rudp_client_skeleton.py — STUDENT SKELETON
Goal: Implement a minimal "Reliable UDP" (RUDP) client over UDP (stop-and-wait).

YOU MUST IMPLEMENT:
  1) 3-way handshake:  (you send) SYN -> (expect) SYN-ACK -> (you send) ACK
  2) DATA send loop (stop-and-wait):
       - split MESSAGE into CHUNK-sized pieces (seq: 0,1,2,...)
       - for each chunk: send DATA, wait for DATA-ACK with matching seq
       - if timeout or wrong ACK: retransmit (retry up to RETRIES)
  3) Teardown: (you send) FIN -> (expect) FIN-ACK

Use Wireshark with: udp.port == <your_assigned_port>
"""
import socket, struct, time

# ===================== CONFIG (EDIT HOST/PORT) =====================
SERVER_HOST = '127.0.0.1'   # server IP or hostname
ASSIGNED_PORT = 30038       # <-- REPLACE with your assigned UDP port
SERVER = (SERVER_HOST, ASSIGNED_PORT)
# ==================================================================

# Timing/reliability parameters
RTO = 0.5        # retransmission timeout (seconds)
RETRIES = 5      # max retries per send
CHUNK = 200      # bytes per DATA chunk

# --- Protocol type codes (1 byte) ---
SYN, SYN_ACK, ACK, DATA, DATA_ACK, FIN, FIN_ACK = 1,2,3,4,5,6,7

# Header format: type(1B) | seq(4B) | len(2B)
HDR = '!B I H'
HDR_SZ = struct.calcsize(HDR)

# A larger message to force multiple DATA/ACK pairs.
MESSAGE = (
    'Hello from student RUDP client!\n'
    'This demo asks you to implement handshake, DATA+ACK with stop-and-wait, '
    'and FIN teardown.\n'
    'Below are numbered lines to create many packets.\n'
    + 'Line ' + '\nLine '.join(str(i) for i in range(1, 101)) + '\n'
)

def pack_msg(tp: int, seq: int, payload: bytes = b'') -> bytes:
    if isinstance(payload, str):
        payload = payload.encode()
    return struct.pack(HDR, tp, seq, len(payload)) + payload

def unpack_msg(pkt: bytes):
    if len(pkt) < HDR_SZ:
        return None, None, b''
    tp, seq, ln = struct.unpack(HDR, pkt[:HDR_SZ])
    return tp, seq, pkt[HDR_SZ:HDR_SZ+ln]

def send_recv_with_retry(sock, pkt, expect_types, expect_seq=None):
    """
    Utility: send a packet and wait (with timeout) for a response
    whose type is in 'expect_types' and optionally has matching seq.
    Retries up to RETRIES times.
    Returns (tp, seq) on success, (None, None) on failure.
    """
    for _ in range(RETRIES):
        sock.sendto(pkt, SERVER)
        sock.settimeout(RTO)
        try:
            resp, _ = sock.recvfrom(2048)
            tp, s, _ = unpack_msg(resp)
            if tp in expect_types and (expect_seq is None or s == expect_seq):
                return tp, s
        except socket.timeout:
            continue
    return None, None
def main():
    cli = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    seq = 0

    # ============ PHASE 1: THREE-WAY HANDSHAKE ============
    print('[CLIENT] Initiating handshake - Sending SYN')
    syn_pkt = pack_msg(SYN, seq)
    print('[CLIENT] Waiting for SYN-ACK response')
    tp, s = send_recv_with_retry(cli, syn_pkt, expect_types=[SYN_ACK], expect_seq=0)
    if tp != SYN_ACK:
        print('[CLIENT] Handshake failed: No SYN-ACK received after maximum retries')
        cli.close()
        return

    ack_pkt = pack_msg(ACK, seq + 1)
    cli.sendto(ack_pkt, SERVER)
    print('[CLIENT] Connection established')
    # ===============================================================

    # ============ PHASE 2: DATA SEND LOOP ==========================
    msg_bytes = MESSAGE.encode()
    seq = 0
    for offset in range(0, len(msg_bytes), CHUNK):
        chunk = msg_bytes[offset:offset + CHUNK]
        print(f'[CLIENT] DATA seq={seq}')
        data_pkt = pack_msg(DATA, seq, chunk)
        tp, s = send_recv_with_retry(cli, data_pkt, expect_types=[DATA_ACK], expect_seq=seq)
        if tp != DATA_ACK:
            print(f'[CLIENT] Failed to get ACK for seq={seq}, aborting.')
            cli.close()
            return
        print(f'[CLIENT] ACK seq={seq}')
        seq += 1
    # ===============================================================

    # ============ PHASE 3: TEARDOWN ================================
    print('[CLIENT] FIN')
    fin_pkt = pack_msg(FIN, 0)
    tp, s = send_recv_with_retry(cli, fin_pkt, expect_types=[FIN_ACK])
    if tp == FIN_ACK:
        print('[CLIENT] Connection closed')
    else:
        print('[CLIENT] FIN-ACK not received, closing anyway')
    # ===============================================================

    cli.close()

if __name__ == '__main__':
    main()