import ImageSeriesSKImage
import finalImageSeries
import threading
from multiprocessing import Pool
import timeit
import numpy as np
from skimage import io as SKIIO
import skimage
from skimage import *
from skimage import transform
if(False):   #test bg crop
    IH = ImageSeriesSKImage.ImageHandler("backgrounds","objects")
    bgImg = IH.getRandomBg()[0]
    top=50
    left = 90
    h = 64
    w = 64
    bgImg = util.crop(bgImg,((top,bgImg.shape[0]-h-top),(left, bgImg.shape[1]-w-left),(0,0)))
    #SKIIO.imsave("testbg.png", bgImg)
    
if(False):   #test transform with skimage
    IH = ImageSeriesSKImage.ImageHandler("backgrounds","objects")
    img = IH.getRandomObj()[0]
    trans = transform.AffineTransform(scale=(.2,.2), rotation=np.pi/2., translation=(10,10))
    newImg = transform.warp(img, inverse_map=trans, clip=False, preserve_range=False)
    SKIIO.imsave("transformationDavor.png", img)
    SKIIO.imsave("transformationDanach.png", newImg)
    
if(True):
    IM = finalImageSeries.ImageSeries()
    IM.getSeries()