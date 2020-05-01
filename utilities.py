# -*- coding: utf-8 -*-
import gdal
import os
import shutil
from imutils import unzip
from subprocess import call


class Sentinel:
    """
    http://stackoverflow.com/questions/40044403/gdal-jp2-driver-missing-in-python
    http://www.gdal.org/frmt_sentinel2.html
    https://spectraldifferences.wordpress.com/2016/08/16/convert-sentinel-2-data-using-gdal/
    https://sentinel.esa.int/web/sentinel/user-guides/sentinel-2-msi/naming-convention

    The Flow class has incorporated necessary methods to calculate
    revenues, NPVs all around the thinning and harvesting of each stand.
    The class is as well useful to generate tables of values with the
    parameters described.

        :param arg1: input data
        :param arg2: mode, default "compute"
        :param arg3: verbose, default False
        :param arg4: overwrite, default False
        :type arg1: dictionary
        :type arg2: string
        :type arg3: boolean
        :type arg4: boolean

    """
    def __init__(self):
        self.download_info = {}
        self.paths = {"L1": None, "L1_tar": None, "L1_xml": None, "L2": None, "L2_tar": None, "L2_xml": None,
                      "root": None, "tif": None, "vrt": None}
        self.initlevel = None #initial read level
        self.level = None #actual processing level, L1 or L2
        self.cards = {"L1": {'pre': 'SENTINEL2_L1C'},
                      "L2": {'pre': 'SENTINEL2_L2A'}}
        self.args = None # locals arguments for local last call
        self.gdal_par = None # gdal parameters

    def unzipme(self, level, skip=True, **kwargs):
        """

        :param level: 'L1' or 'L2'
        :param skip: if True, it will skip decompressed files if they already exists. Default is True.
        :param kwargs: parameters to the utils.unzip function
        :return: None
        """
        self.args = locals()  # save local variables (at this point, all the input to the function)
        filen = kwargs.get("infile").replace("\\\\?\\", "") # search for long names solution in windows
        nfilen = filen[:-3] + "SAFE"
        exists = False
        if skip:
            exists = os.path.exists(nfilen)

        if not(exists and skip):
            print "File {} decompressing".format(filen)
            name = unzip(**kwargs)
            print "File {} decompressed".format(filen)
            self.paths["root"] = name.replace("\\\\?\\", "") # search for long names solution in windows
            self.paths["{}_tar".format(level)] = filen
            self.paths["{}".format(level)] = nfilen
            xmlf = [f for f in os.listdir(self.paths["{}".format(level)]) if f.endswith(".xml") and "MTD_" in f][0]
            self.paths["{}_xml".format(level)] = os.path.join(self.paths["{}".format(level)], xmlf)
            self.initlevel = level
            self.level = level
            return True
        else:
            print "File {} already present, skipping".format(filen)
            return False

    def load(self, dirname, level="L1"):
        """

        :param dirname: full path to directory
        :param level:
        :return:
        """
        # dir = 'Y:\\IMAGES\\sentinel\\pradaria\\original\\S2A_OPER_PRD_MSIL1C_PDMC_20160705T183753_R124_V20160705T134412_20160705T134412.SAFE'
        self.args = locals()  # save local variables (at this point, all the input to the function)

        if os.path.isdir(dirname) and dirname.endswith('.SAFE'):
            files = os.listdir(dirname)
            xmlf = sorted([f for f in files if f.endswith('.xml') and "MTD_" in f])[-1]
            self.paths["root"] = dirname
            self.paths["{}".format(level)] = dirname
            self.paths["{}_xml".format(level)] = os.path.join(self.paths["{}".format(level)], xmlf)
            self.initlevel = level
            self.level = level
            return True
        else:
            print "This is not a Sentinel Folder"
            return False

    def L1toL2(self, path=None, *args):
        """

        :param path: if None provided, use actual
        :param args: arguments passed to L2A_Process as in the console or command prompt
        :return: None
        """
        self.args = locals()  # save local variables (at this point, all the input to the function)
        # from SENTINEL.utilities import *; t1 = Sentinel()
        # t1.L1toL2("F:/ensayos/sentinel/S2A_OPER_PRD_MSIL1C_PDMC_20161202T223817_R124_V20161202T134212_20161202T134212.SAFE", "--resolution=10", "--sc_only")
        # t1.L1toL2("F:/ensayos/sentinel/S2A_OPER_PRD_MSIL1C_PDMC_20161202T223817_R124_V20161202T134212_20161202T134212.SAFE", "--resolution=10")
        if self.level == "L1":
            if path:
                self.paths["L1"] = path
            else:
                path = self.paths["L1"]

            lista = list(args)
            call(["L2A_Process"] + lista + [path])
            l2name = self.paths['L1']
            l2name = l2name.replace("_MSIL1C_", "_MSIL2A_")
            l2name = l2name.replace("_OPER_", "_USER_")
            self.paths['L2'] = l2name.replace("MSIL1C", "MSIL2A")
            n1 = os.path.split(self.paths['L2'])[-1]
            n1 = n1.replace("_PRD_", "_MTD_")
            n1 = n1.replace("_MSIL2A_", "_SAFL2A_")
            self.paths['L2_xml'] = os.path.join(self.paths['L2'], n1.replace(".SAFE", ".xml"))
            self.level = "L2"
        else:
            raise Exception("We are not in a level 1 image")

    def __get_tile_info(self, image):
        """
        Get the tile information
        :param image: image opened by gdal.Open()
        :return:
        """
        catalog = image.GetSubDatasets()
        img2 = gdal.Open(catalog[0])  # 10m; 1 for 20m, 2 for 60m
        fil = img2.GetFileList()
        import pdb; pdb.set_trace()

    def jpg2tiff(self, outpath=None, outname=None, resolution=10, EPSG=[], bands=[], clean=False, out_epsg=None,
                 overwrite=False, args=[]):
        """

        :param outpath:
        :param outname: without extension. Tiff will be automatically used
        :param resolution:
        :param EPSG: a list with all possible EPSGs
        :param bands: a list of the desired bands, ie: [1,3,4]
        :param clean: should unmcompressed L1 and L2 folder be deleted? Default is False.
        :param out_epsg: the output epsg for all images. If not match, the image will be reprojected
        :param overwrite: if True, overwrites an existing file, otherwise will be skipped. Default is False.
        :param args: a list, with arguments passed to gdal_translate as text (as directly from console)
        :return:
        """
        self.args = locals() # save local variables (at this point, all the input to the function)
        if not outpath:
            import pdb; pdb.set_trace() # do something
        if not EPSG:
            import pdb; pdb.set_trace()  # do something

        xmlFile = os.path.join(self.paths["{}".format(self.level)], self.paths["{}_xml".format(self.level)])
        granule_dict = os.path.join(self.paths["{}".format(self.level)], "GRANULE")
        tiles = os.listdir(granule_dict)

        sent_header = "SENTINEL2_L2A:{}:{}m:EPSG_{}"
        ext = "_{}{}.tif"
        disposer = []

        if tiles:
            # self.paths["vrt"] = xmlFile[:-3] + "vrt"
            print 'Attempting to convert {}, with {} tiles\n'.format(xmlFile, len(tiles))

            # imgs = {k: 0 for k in EPSG} # mosaic image container
            # project = False
            # mosaic = False
            # (DEPRECATED) First, retrieve information and see if project and mosaic are necessary
            # if out_epsg:
            #     for epsg in EPSG:
            #         img = gdal.Open(sent_header.format(xmlFile, resolution, epsg))
            #         if img:
            #             imgs[epsg] += 1
            #
            #     project = True if sum([v for k, v in imgs.iteritems() if k != out_epsg]) > 0 else False
            #     mosaic = True if sum(imgs.values()) > 1 else False
            #     img = None
            #
            #     if mosaic:
            #         ext = "_temp_{}.tif"
            # for til in tiles:
            #     til_dir = os.path.join(granule_dict, til)
            #     xmls = [f for f in os.listdir(til_dir) if f.endswith('.xml')]
            for epsg in EPSG:
                img0 = None
                print '1A.......'
                try:
                    # img0 = gdal.Open("SENTINEL2_L2A:{}:{}m:EPSG_{}".format(os.path.join(til_dir, xmls[0]), resolution, epsg))
                    img0 = gdal.Open("SENTINEL2_L2A:{}:{}m:EPSG_{}".format(xmlFile, resolution, epsg))
                except Exception:
                    pass
                # open(self.paths["vrt"], 'wb').write(img.GetMetadata('xml:VRT')[0].encode('utf-8'))
                if img0:
                    nam = self.__get_tile_info()
                    if not outname:
                        outfilename = os.path.basename(xmlFile).replace(".xml", ext.format(epsg, ""))
                    else:
                        outfilename = outname + ext.format(epsg, "")
                    bandsn = img0.RasterCount
                    if bands:
                        if len(bands) > bands:
                            raise Exception("You specified more bands than the available")
                        else:
                            bandsg = ['-b ' + ' -b '.join([str(b) for b in bands])]

                    imname = os.path.join(outpath, outfilename)
                    imname2 = None
                    # imgs[epsg] = imname
                    # tempimage = self.paths["tif"] if epsg == out_epsg else os.path.join(outpath, outfilename + "_tempProj.tif")
                    self.gdal_par = ["gdal_translate", "SENTINEL2_L2A:{}:{}m:EPSG_{}".format(xmlFile, resolution, epsg), imname]
                    print '     Bands: {}'.format(bands)
                    print '     Resolution: {}'.format(resolution)
                    print '     EPSG: {}\n'.format(epsg)
                    print 'Converting from SENTINEL2 to tif...\n'
                    call(' '.join(self.gdal_par + bandsg + args), shell=True)

                    # Reproject if necessary
                    if out_epsg:
                        if epsg != out_epsg:
                            if not outname:
                                outfilename = os.path.basename(xmlFile).replace(".xml", ext.format(out_epsg, "_c"))
                            else:
                                outfilename = outname + ext.format(out_epsg, "_c")
                            imname2 = os.path.join(outpath, outfilename)
                            print '\nConverting image from EPSG {} to EPSG {}\n'.format(epsg, out_epsg)
                            call("gdalwarp -t_srs EPSG:{} {} {} ".format(out_epsg, imname, imname2) + ' '.join(args))
                            os.remove(imname)

                    self.paths["tif"] = imname2 if imname2 is not None else imname

                    print '\n----------------- Finished!!! ---------------\n\n'
                    if clean:
                        # if self.paths["L1"]:
                        #     shutil.rmtree(self.paths["L1"], ignore_errors=True)
                        if self.paths["L2"]:
                            shutil.rmtree(self.paths["L2"], ignore_errors=True)
                else:
                    print '\nNo image can be found for epsg {}\n'.format(epsg)
                img = None
                img0 = None

            # if project and mosaic:
            #     print '\nMosaicking image'
            #     # gdalbuildvrt
            #     if not outname:
            #         outfilename = os.path.join(outpath, os.path.basename(xmlFile).replace(".xml", ""))
            #     else:
            #         outfilename = outname
            #     call(["gdalbuildvrt", outfilename + '.vrt'] + imgs.values())
            #     # gdal_translate
            #     call("gdal_translate {0}.vrt {0}.tif ".format(outfilename) + ' '.join(args))
            #     # remove temp images
            #     for k, v in img.iteritems():
            #         os.remove(v)
            #     os.remove("{}.vrt".format(outname))
            #     print 'Mosaick finished!!'



