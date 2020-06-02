# sentinel2-fix
# actualización a python 3 (probado en python 3.7.6)
este repo corrige el error de lectura de directorios creados por Sen2Cor al crear un directorio con la imagen Lv1 procesada a Lv2, ya que cambia un tag de tiempo en el nombre del directorio del producto.

## Entorno virtual

Correr en idealmente en Terminal *nix (puede ser OSX, WSL2, Ubuntu, etc.). Instalar Conda para python.
Verificar que `ROOTDIR` (en flask_server.py) esté correctamente apuntado.

```
conda create --name sentinel2py3 python=3.7 pip gdal flask
conda activate sentinel2py3
pip install flask_login sentinelsat

python sentinel2/web/flask_server.py
```
para procesar las imagenes Lv1 a Lv2, se debe bajar Sen2Cor, y para crear el Gtiff, se usa gdal instalado ya en el entorno de conda.

ref. Sen2Cor: http://step.esa.int/main/third-party-plugins-2/sen2cor/sen2cor_v2-8/