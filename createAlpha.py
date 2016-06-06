from PIL import Image
import numpy as np
import json
import os
import math
from time import sleep
import shutil

''' #das hier wird nicht mehr gebraucht.
#Hat nur dazu gedient, die Bilder von den restlichen html etc Dateien zu trennen und an einen anderen Ort zu speichern
def getFiles(sourceFolder, destinationFolder):
    for files in getFilesFromDirectory(sourceFolder, ".png"):
        if(not os.path.exists(destinationFolder+"/"+files[1])):
            os.makedirs("BilderMitAlpha/"+files[1])
        shutil.copy(files[0], destinationFolder+"/"+files[1])           
getFiles('C:/Users/Daniel/Desktop/httpshapenet.cs.stanford.edu', 'D:/programmieren/Python/BilderMitAlpha')
'''

def deleteLogo(path):
    files=[]
    for file in os.listdir(path):
        if(os.path.isfile(path+"/"+file)): 
            if(file=="logo-thumbnail.png"): #deletes the Image named logo-thumbnail
                os.remove(path+"/logo-thumbnail.png") 
        else:            
            deleteLogo(path+"/"+file) 
                
def getFilesFromDirectory(path, filetype):
    files=[]
    for file in os.listdir(path):
        if(os.path.isfile(path+"/"+file)): 
            if file.endswith(filetype):
                files.append(path+"/" + file)
        else:            
            for f in getFilesFromDirectory(path+"/"+file, filetype):
                files.append(f)
    return files

def setAlpha(newSize=32.): #Images are currently overwritten, so take care if you want to keep them
    files = getFilesFromDirectory("BilderMitAlpha", ".png")
    counter=0
    for file in files:
        counter+=1
        print("currently at: "+str(counter/len(files))+"%")
        img = Image.open(file)
        img = img.convert('RGBA')
        pixdata = img.load()

        for y in range(img.size[1]):
            for x in range(img.size[0]):
                if pixdata[x, y][0]+pixdata[x, y][1]+pixdata[x, y][2]>=760:
                    pixdata[x, y] = (0, 0, 0, 0)
                elif pixdata[x, y][0]+pixdata[x, y][1]+pixdata[x, y][2]>=755:
                    pixdata[x, y] = (pixdata[x, y][0],pixdata[x, y][1],pixdata[x, y][2],100)
        #Crop Image to boundingBox
        img = img.crop(getBoundingBox(img))
        
        #Resize to newSize and keep ratio
        print(img.size)
        maxPixel = max(img.size)
        newscaleX = round(img.size[0]*newSize/maxPixel)
        newscaleY = round(img.size[1]*newSize/maxPixel)
        img.resize((int(newscaleX),int(newscaleY))).save(file, "PNG")
    

  
def getBoundingBox(img):
    npImg = np.array(img)
    marker = [True,True,True,True]
    boundingBox = [0, 0, img.size[0], img.size[1]]
    for i in range(img.size[0]):
        #print(pixdata[i,16])
        for j in range(img.size[1]):
            if(marker[0] and not np.array_equal(npImg[j][i],[0,0,0,0])):
                boundingBox[0] = i
                marker[0] = False
            if(marker[1] and not np.array_equal(npImg[i][j],[0,0,0,0])):
                boundingBox[1] = i
                marker[1] = False
            if(marker[2] and not np.array_equal(npImg[j][img.size[0]-1-i],[0,0,0,0])):
                boundingBox[2] = img.size[0]-1-i
                marker[2] = False                
            if(marker[3] and not np.array_equal(npImg[img.size[1]-1-i][j],[0,0,0,0])):
                boundingBox[3] = img.size[1]-1-i
                marker[3] = False
    return boundingBox

    
   
#deleteLogo("Sicherungen/BilderMitAlpha")    
#setAlpha()     
    