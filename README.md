# sentinel2

## Entorno virtual

Correr en Ubuntu server (version 16.04 o 20.04). Instalar Conda para python. 

Verificar que `ROOTDIR` (en flask_server.py esté correctamente apuntado).

```
conda create --name sentinel2 python=2.7 pip ipython gdal flask
conda activate sentinel2
pip install flask_login sentinelsat

ipython sentinel2/web/flask_server.py
```

## Ejemplo

Una prueba del servicio está corriendo (espero) en [sentinel2.tecpar.cl](sentinel2.tecpar.cl).

Usuario: user
Contraseña: changos!

