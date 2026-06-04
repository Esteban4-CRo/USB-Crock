import socket
import subprocess
import platform
import os

SYSTEM = platform.system()

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def open_firewall(port, rule_name="CROCK"):
    """Abre puerto TCP en firewall de Windows con nombre configurable"""
    try:
        if SYSTEM == "Windows":
            # Primero borrar regla vieja si existe
            subprocess.run(
                f'netsh advfirewall firewall delete rule name="{rule_name}"',
                shell=True, capture_output=True
            )
            # Crear regla de entrada
            cmd_in = (
                f'netsh advfirewall firewall add rule name="{rule_name}" '
                f'dir=in action=allow protocol=TCP localport={port} '
                f'profile=any enable=yes'
            )
            result = subprocess.run(cmd_in, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                return False
            # Crear regla de salida
            cmd_out = (
                f'netsh advfirewall firewall add rule name="{rule_name}_OUT" '
                f'dir=out action=allow protocol=TCP localport={port} '
                f'profile=any enable=yes'
            )
            subprocess.run(cmd_out, shell=True, capture_output=True)
            return True
        return False
    except:
        return False

def close_firewall(rule_name="CROCK"):
    """Cierra regla de firewall"""
    try:
        if SYSTEM == "Windows":
            subprocess.run(
                f'netsh advfirewall firewall delete rule name="{rule_name}"',
                shell=True, capture_output=True
            )
            subprocess.run(
                f'netsh advfirewall firewall delete rule name="{rule_name}_OUT"',
                shell=True, capture_output=True
            )
            return True
        return False
    except:
        return False

def get_public_ip():
    """Intenta obtener IP pública"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect(("ifconfig.me", 80))
        s.sendall(b"GET / HTTP/1.1\r\nHost: ifconfig.me\r\n\r\n")
        data = s.recv(4096).decode()
        s.close()
        # Parsear respuesta HTTP
        lines = data.split('\r\n')
        for line in reversed(lines):
            line = line.strip()
            if line and '.' in line and len(line) < 20:
                return line
    except:
        pass
    return None
