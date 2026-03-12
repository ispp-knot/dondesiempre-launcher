# DondeSiempre Launcher

Este script facilita el lanzamiento de la aplicación DondeSiempre.

## Instalación

### Python

Para hacer uso del launcher, es necesario contar con una instalación de [Python](https://www.python.org/), preferiblemente la versión 3.12 o superior.

### Entorno virtual

Para ejecutarlo, se recomienda la creación de un entorno virtual de Python:

- En Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\activate.bat
```

- En derivados de Unix:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Dependencias

Antes de ejecutarlo, deben instalarse las dependencias del script:

- En Windows:

```powershell
python -m pip install -r requirements.txt
```

- En derivados de Unix:

```bash
python3 -m pip install -r requirements.txt
```

### Configuración

El launcher es configurable medinate el archivo `launch.cfg`. Se provee un archivo de ejemplo, `launch.cfg.example`.

Para configurar el launcher:

1. Crear una copia de `launch.cfg.example` con el nombre de `launch.cfg`.
2. Cambiar la variable `BACKEND_PATH` a la ruta (absoluta o relativa) del directorio en el que está clonado el [repositorio del backend](https://github.com/ispp-knot/dondesiempre-backend).
3. Cambiar la variable `FRONTEND_PATH` a la ruta (absoluta o relativa) del directorio en el que está clonado el [repositorio del frontend](https://github.com/ispp-knot/dondesiempre-frontend).

## Uso

### Invocación

Para invocar al launcher, solo es necesario ejectuar el siguiente comando:

- En Windows:

```powershell
python -m launch
```

- En derivados de Unix:

```bash
python3 -m launch
```

Dicho comando mostrará la guía de uso del launcher.
