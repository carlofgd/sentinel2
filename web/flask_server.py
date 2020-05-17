#!/usr/local/bin/python2.7
# -*- coding: utf-8 -*-

import datetime
import flask
import os
import zipfile
import glob
from flask import request
from login import flask_login, login_manager, login, logout, protected
#from multiprocessing.dummy import Pool as ThreadPool
from osgeo import ogr
from sentinelsat import SentinelAPI
# from shutil import rmtree
from subprocess import call, Popen, PIPE
#from timeit import time

ROOTDIR = '/Users/carlo/sentinel2-master/sets/'

# ROOTDIR = '/mnt/raid51/imagery/sentinel/web_served/original'
# ROOTDIR = 'F:/'
# PROJDIR = os.path.join(ROOTDIR, 'Tongoy_Musels'); ZIPDIR = os.path.join(PROJDIR, 'zip'); L1DIR = os.path.join(PROJDIR, 'l1')
# L2DIR = os.path.join(PROJDIR, 'l2'); TIFDIR = os.path.join(PROJDIR, 'l2_tif')
PROJDIR = None
ZIPDIR = None
L1DIR = None
L2DIR = None
TIFDIR = None
DIRS = ['zip', 'l1', 'l2', 'l2_tif']  # the order is important! do not move without check!

@flask_login.login_required
def inicio():
    if request.method == 'POST':
        pac = request.form

        # Setting directories
        fullpath = os.path.join(ROOTDIR, pac['project'])
        if not os.path.exists(fullpath):
            os.makedirs(fullpath)
        for sdir in DIRS:
            if not os.path.exists(os.path.join(fullpath, sdir)):
                os.makedirs(os.path.join(fullpath, sdir))

        # Setting square of interest, based on 4 coordinates
        line = ogr.Geometry(ogr.wkbLinearRing)
        poly = ogr.Geometry(ogr.wkbPolygon)
        coord = zip([pac['west']]*2 + [pac['east']]*2, [pac['north'], pac['south']] + [pac['south'], pac['north']])
        coord.append(coord[0])
        for i in coord:
            line.AddPoint(float(i[0]), float(i[1]))
        poly.AddGeometry(line)

        # Setting api, query, and download
        api = SentinelAPI('aparedes', 'N1E3I3ipjdm5FEV8oaQN', 'https://scihub.copernicus.eu/dhus')
        filesd = {}; failed = {}
        date=(''.join(pac['start_date'].split("-")), ''.join(pac['end_date'].split("-")))
        products = api.query(poly.ExportToWkt(),
                             date,
                             platformname='Sentinel-2',
                             cloudcoverpercentage=(0, int(pac['max_cloud'])),
                             producttype='S2MSI1C') #lv1 sale en el dia, lv2 sale como postproceso, 48 hrs dpues
        productos = []
        ids = []
        down_size = sum([float(v['size'].split(' ')[0]) for k, v in products.iteritems()])
        productos.append([(v['filename']) for k, v in products.iteritems()])
        ids.append([(k) for k, v in products.iteritems()])
        filesd, triggered, failed = api.download_all(products, directory_path=os.path.join(fullpath, DIRS[0]))
        return 'Se descargaron {} productos, de {}MB en total.'.format(len(products), down_size)
    else:
        return flask.render_template('sentinel_selection.html')

@flask_login.login_required
def projects():
    if request.method == 'POST':
        global PROJDIR
        global ZIPDIR
        global L1DIR
        global L2DIR
        global TIFDIR
        pac = request.form
        selected_dir = pac['selected']
        PROJDIR = os.path.join(ROOTDIR, selected_dir)
        ZIPDIR = os.path.join(PROJDIR, DIRS[0])
        L1DIR = os.path.join(PROJDIR, DIRS[1])
        L2DIR = os.path.join(PROJDIR, DIRS[2])
        TIFDIR = os.path.join(PROJDIR, DIRS[3])
        for sdir in DIRS:
            if not os.path.exists(os.path.join(PROJDIR, sdir)):
                os.makedirs(os.path.join(PROJDIR, sdir))
        l1zips = [f for f in os.listdir(ZIPDIR) if (f.endswith('zip') and not (os.path.isdir(f)))] # S2?_MSIL1C*.SAFE
        l2dirs = [f for f in os.listdir(L2DIR)] # S2?_MSIL1C*.SAFE
        print l2dirs
        if not l1zips: # if no files in zip folder, check l1 folder for SAFE dirs
            l1zips = [f for f in os.listdir(L1DIR) if f.endswith('SAFE')]
        return flask.render_template('sentinel_projects.html', projs=l1zips, type=2)
    else:
        projs = [d for d in os.walk(ROOTDIR).next()[1] if d[0] not in ['.', '$']]
        return flask.render_template('sentinel_projects.html', projs=projs, type=1)


@flask_login.login_required
def process_project():
    global L1DIR
    pac = request.form
    files = [f for f in pac if f not in ['submit', 'toTiff', 'selectAll', 'all']] #archivos seleccionados
    prior = [f for f in pac if f.endswith('SAFE') and '_MSIL_' in f] #archivos descomprimidos
    posteriori = []

    # descomprimir...
    if len(files) > 0:
        if files[0].endswith('.zip'):
            for fil in files:
                print("Descomprimiendo {} en {}".format(fil, L1DIR))
                zip_ref = zipfile.ZipFile(os.path.join(ZIPDIR, fil), 'r')
                zip_ref.extractall(L1DIR)
                zip_ref.close()
                filpath = os.path.splitext(fil)[0]
                filpath = filpath + '.SAFE'
                posteriori.append(filpath)
            l1folders = [f for f in posteriori if f not in prior]
        else:
            l1folders = [f for f in pac if f.endswith('SAFE') and '_MSIL_' in f]
    else:
        return "No se seleccionó ningun archivo."
    #----- Multi-thread
    # pool = ThreadPool(8)
    # marray = [[os.path.join(L1DIR, v), L2DIR, TIFDIR, '{}.log'.format(os.path.join(PROJDIR, os.path.basename(v)))] for v in l1folders]
    # results = pool.map(L1toTif, marray)
    #----- Single trhead:
    for l1folder in l1folders:
        proyecto=os.path.join(L1DIR, l1folder)
        #/blabla/sets/demo/l1/S2A_blablabla.SAFE
        l2=L2DIR
        #/blabla/sets/demo/l2
        tif=TIFDIR
        #/blabla/sets/demo/l2_tif
        logger='{}.log'.format(os.path.join(PROJDIR, os.path.basename(l1folder))),
        if 'toTiff' in pac:
            print("\nProcesando: L(1/2) -> GTiff, {} archivo(s) para ser procesado(s).\n".format(len(l1folders)))
            L1toTif(proyecto, l2, tif, logger)
        else:
            print("\nProcesando: L1 -> L2, {} archivo(s) para ser procesado(s).\n".format(len(l1folders)))
            L1toL2(proyecto, logger)
    return 'fin! Ir a <a href="/download">descargas</a>'

@flask_login.login_required
def download_view():
    if request.method == 'POST':
        pac = request.form
        selected_dir = pac['selected']
        files = os.listdir(os.path.join(ROOTDIR, selected_dir, DIRS[3]))
        header = "For 10m imagery band 1 to band 4 are: B02, B03, B04, B08" + \
        ". For 20 imagery band 1 to band 10 are: B02, B03, B04, B05, B06, B07, B08, B8A, B11, B12"
        downweb = '<p>{3} -<a href="/products/{0}/{1}/{2}"> {2}</a></p>'
        return header + ''.join([downweb.format(selected_dir, DIRS[3], i, ctr) for ctr, i in enumerate(files)])
    else:
        projs = [d for d in os.walk(ROOTDIR).next()[1] if d[0] not in ['.', '$']]
        return flask.render_template('sentinel_projects.html', projs=projs, type=1)

@flask_login.login_required
def products(filename):
    return flask.send_from_directory(ROOTDIR, filename, as_attachment=True)


app = flask.Flask("sentinel2", static_folder='static', template_folder='templates')
app.secret_key = '498fjohdfljgte03#@r421¬&69'
app.config['CUSTOM_STATIC_PATH'] = ROOTDIR
login_manager.init_app(app)

routes = {
    '/': {'func': inicio, 'method': ['GET', 'POST'], 'desc': 'root'},
    '/login': {'func': login, 'method': ['GET', 'POST'], 'desc': 'login page'},
    '/logout': {'func': logout, 'method': ['GET'], 'desc': 'logout page'},
    '/projects': {'func': projects, 'method': ['GET', 'POST'], 'desc': 'Proyects with data'},
    '/process': {'func': process_project, 'method': ['POST'], 'desc': 'Process data'},
    '/protected': {'func': protected, 'method': ['GET'], 'desc': 'after login page'},
    '/download': {'func': download_view, 'method': ['GET', 'POST'], 'desc': 'Download products'},
    '/products/<path:filename>': {'func': products, 'method': ['GET'], 'desc': 'URL to download products'},
}

# -------------------------------------------------------------------------------------------------------------------------------------

def L1toL2(path, logfile=None):
    """
    Need to install latest version of sen2cor first (http://step.esa.int/main/third-party-plugins-2/sen2cor/), and add L2A_Bashrc to
    the system path (i.e: add source /opt/sen2cor2.5.5/L2A_Bashrc to /opt/anaconda2/envs/image/etc/conda/activate.d/env_vars.sh).
    It will be a good thing to configure the L2A_GIPP.xml file

    path: fullpath to the .SAFE L1 folder

    """
    # path = '/mnt/raid51/imagery/sentinel/web_served/original/coquimbo/S2B_MSIL1C_20180412T144729_N0206_R139_T19JBG_20180412T194110.SAFE'
    # outpath = 'c/coquimbo/L2'
    parent_dir, dirname = os.path.split(path)
    dir_elems = dirname.split('_')
    sentinel = dir_elems[0]
    level = dir_elems[1]
    date_time = dir_elems[2]

    path2 = parent_dir.replace("/l1","/l2")
    level = level.replace("MSIL1C","MSIL2A")

    path_tif = path2 + '/' + sentinel + '_' + level + '_' + date_time
    cmd = ["L2A_Process",  "--resolution=10", path, "--output_dir", path2]
    # L2A_Process --resolution=60 '/blablabla/l1/S2A_MSIL1C_20200426T144731_N0209_R139_T19JBG_20200426T181352.SAFE' --output_dir '/blablabla/l2/S2A_MSIL1C_20200426T144731_N0209_R139_T19JBG_20200426T181352.SAFE'
    logfile = logfile[0]
    p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)

    if logfile:
        with p.stdout, open(logfile, 'ab') as file:
            for line in iter(p.stdout.readline, b''):
                print line,
                file.write(line)

    #no pude replicar el error que trataba de evitar el while true, asi que lo saque
    return path_tif


def L2toTif(pathlist, outpath=None, resolutions=[10, 20], allinfo=True, logfile=None):
    # path = '/mnt/raid51/imagery/sentinel/web_served/original/tongoy/l2/S2B_MSIL2A_20180611T144729_N0206_R139_T19JBG_20180611T195539.SAFE/'
    # path = '/mnt/raid51/imagery/sentinel/web_served/original/tongoy/l2/S2B_MSIL2A_20180611T144729_N0206_R139_T19JBG_20180611T195539.SAFE/GRANULE/L2A_T19JBG_A006600_20180611T145550/IMG_DATA/R10m'
    print 'L2 A TIFF!',
    path_to_conv = glob.glob(pathlist + '*')
    path = path_to_conv[0]
    granule = os.path.join(path, 'GRANULE')
    imdir = os.listdir(granule)[0]
    imdirdat = os.path.join(granule, imdir, 'IMG_DATA')
    imgsdir = {r: os.path.join(imdirdat, 'R{}m'.format(r)) for r in resolutions}
    pbands = ['B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B8A', 'B11', 'B12']
    sbands = ['AOT', 'SCL', 'TCI', 'WVP']
    stack = 'stack.vrt'
    if outpath is None:
        outp = os.path.join(granule, imdir)
    else:
        outp = outpath
    for res in imgsdir:
        stackpath = os.path.join(imgsdir[res], stack)
        imname = '{}_{}m.tif'.format(imdir, res)
        bands = os.listdir(imgsdir[res])
        files = [b for w in pbands for b in bands if w in b]
        fullname = os.path.join(outp, imname)
        if allinfo:
            files += [b for w in sbands for b in bands if w in b]
        
        print('Creando imagen GTiff: {}'.format(fullname))

        # el vrt..
        cmd = ["gdalbuildvrt", "-separate", stackpath] + [os.path.join(imgsdir[res], f) for f in files]
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        if logfile:
            with p.stdout, open(logfile, 'ab') as file:
                for line in iter(p.stdout.readline, b''):
                    print line,
                    file.write(line)
        # output, error = p.communicate()

        # a Gtiff..
        cmd2 = ['gdal_translate', '-co', 'COMPRESS=LZW', '-of', 'GTiff', '-co', 'predictor=2', stackpath, fullname]
        p2 = Popen(cmd2, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        if logfile:
            with p2.stdout, open(logfile, 'ab') as file:
                for line in iter(p2.stdout.readline, b''):
                    print line,
                    file.write(line)
    return 0


def L1toTif(l1dir, l2dir=None, tifdir=None, logfile=None):
    print 'L1 a TIFF!',
    if isinstance(l1dir, list): # for multithread solution!
        olist = l1dir
        l1dir = olist[0]
        l2dir = olist[1]
        tifdir = olist[2]
        logfile = olist[3]
    if l2dir is None or tifdir is None: 
        raise Exception("l2dir y tifdir no pueden ser None: llamada hecha desde L1toTif, on {}".format(l1dir))
    print("Leyendo {}".format(l1dir))

    pathl2 = L1toL2(l1dir, logfile=logfile)
    l2tif = L2toTif(pathl2, tifdir, logfile=logfile[0])

    return 0


@app.before_request
def before_request():
    # This will keep a session alive for an x amount of inactive time. Every time the website is used, the countdown
    # is restarted
    flask.session.permanent = True
    app.permanent_session_lifetime = datetime.timedelta(minutes=60*48) #falta probar si depende de timeit o datetime
    flask.session.modified = True
    flask.g.user = flask_login.current_user


if __name__ == '__main__':
    for key, data in routes.iteritems():
        app.add_url_rule(key, view_func=data['func'], methods=data['method'])
    app.run(host='127.0.0.1', debug=True, port=5000, threaded=True)

