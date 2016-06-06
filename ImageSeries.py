# -*- coding: utf-8 -*-
from PIL import Image
import numpy as np
import json
import os
import math
from random import randint  #randint(a,b) returns random values a <= N <= b, so be careful, because b is included
from random import uniform
from random import choice

################## Config ##################
### Options about folders and filenames ###
PATHBACKGROUNDFOLDER = "backgrounds"
PATHOBJECTFOLDER = "objects"
PATHTOTRAJECTORYFILE = "trajectories/trajectories.json"
SERIESNAME = "Testserie"
SERIESFOLDER = "imgSeries"

### Options about the series ###
SIZE = [64,64]  #Size of the canvas
MINFRAMES = 9   #Minframes per trajectory
MAXFRAMES = 9   #Maxframes per trajectory   #has to be >=2
MINOBJ = 1      #at least one object should be displayed
MAXOBJ = 5      #max amount of objects per frame
TRANSLATIONLENGTH = (2,15)      #Length of the vector for the objects to move (min,max)
DEFLECTIONBORDERLENGTH = 10     #This value is divided by two in the further code. 
BGMAXTRANSLATION = (5,5)        #Maximum Translation of the background in a whole series
TRAJECTORYOFFSET = (0.001, 0.1) #The offset is multiplicative. So this value should stay 0<= x << 1
#The size of the objects has to be smaller than the canvas size. For optimizing the performance, the images should be resized.
#A script is provided
MINSCALE = 0.5      #min scale for image (it should be visible) #for best performance of imageFlow this shouldn't be too small
MAXSCALE = 1.0      #max scale for image (should not fill whole background) #for best performance of imageFlow this has to be <=1
MINROTATE = -45.0   #minimum rotation angle degree (negative values turn object right)
MAXROTATE =  45.0   #maximum rotation angle degree (positive values turn object left) 

################## Mode declaration ##################
#Modes operate on the interval [0,1]. 
#0: do nothing (turns mode off e.g. no rotation wanted)
#1: linear
#2: quadratic = slow in beginning, speeds up to the end
#3: sqrt = speeds up fast in the beginning and slows down later, 
#4: slow in beginning and end, fast in the middle
#e.g. [0,2,4] makes all modes possible except mode 1 and 3
TRANSLATIONMODEX =  [0,1,2,3,4]
TRANSLATIONMODEY = [0,1,2,3,4]   
SCALEMODE = [0,1,2,3,4]    
ROTATIONMODE = [0,1,2,3,4] 

###### Additional options and modes ######
SAFETRAJECTORY = True
SAFEIMAGES = True
KEEPMIDDLEOFIMAGEONCANVAS = False 
IMAGENOISE = False   #adds a random noise to the picture. 
MOVEABLEBACKGROUND = True       #Mode if background also moves
GETSEGMENTATIONMASK = False     #gets the individual segmentationMask for each frame for each object
SAVESEGMENTATIONMASK = False    #saves the segmentationMasks as picture in the folder "test"
GETOPTICALFLOW = False          #currently not working
TESTOPTICALFLOW = False         #currently not working
WITHRANDOMTRAJECTORYOFFSET = False

################ End Config ################

class ImageHandler():
    def __init__(self, background, objects):    
        self.bgList = {}
        self.objList = {}
        for file in self.getFilesFromDirectory(background,''):
            img = Image.open(file)
            self.bgList[file] = img.convert('RGBA')
        print("Backgrounds loaded")
        for file in self.getFilesFromDirectory(objects,''):
            img = Image.open(file)
            self.objList[file] = img.convert('RGBA')
        print("Objects loaded")
        self.bgKeys = list(self.bgList.keys())
        self.objKeys = list(self.objList.keys())

    #This can be used for creating the lists for the backgrounds and the moveable objects. 
    #It will find all subsequent files recursively
    #enter the path to the folder that should be added and the filetype to select for. ('' for all)
    def getFilesFromDirectory(self, path, filetype):
        files=[]
        for file in os.listdir(path):
            if(os.path.isfile(path+"/"+file)): 
                if file.endswith(filetype):
                    files.append(path+"/" + file)
            else:            
                for f in self.getFilesFromDirectory(path+"/"+file, filetype):
                    files.append(f)
        return files        

    def getRandomObj(self):
        key = choice(self.objKeys)
        return self.objList[key], key
    
    def getRandomBg(self):
        key = choice(self.bgKeys)
        return self.bgList[key], key
        
    def getObjFromKey(self, key):
        return self.objList[key]    #don't raise an error here if file doesn't exist.
    
    def getBgFromKey(self, key):
        return self.bgList[key]     #don't raise an error here if file doesn't exist.
        
    def __str__(self):
        print("Objects loaded: ", len(self.objList))
        print("Backgrounds loaded: ", len(self.bgList))
        return ""
            
class ImageSeries():
    def __init__(self, background=PATHBACKGROUNDFOLDER, objects=PATHOBJECTFOLDER, size=SIZE, seriesLength=0):
        self.images = ImageHandler(background, objects)
        self.seriesLength = seriesLength if seriesLength > 0 else randint(MINFRAMES, MAXFRAMES)
        self.size = size
        self.output = np.array([None]*self.seriesLength)
        self.segmentationLayers = np.array([None]*(self.seriesLength))
        self.imageFlow = np.array([None]*(self.seriesLength))
        self.scene = []

        #assertions:
        if(KEEPMIDDLEOFIMAGEONCANVAS):
            assert min(size)/2. < TRANSLATIONLENGTH[0], "minimum translationLength is too high. No coordinates can be matched"
        
    def getSeries(self):
        numObjInScene = randint(MINOBJ,MAXOBJ)
        frames = self.seriesLength
        scene = np.array([None]*(1+numObjInScene))   #scene contains the trajectories of the background and the drawn objects
        scene[0], off = self.getBackground()        #get background image as trajectory and the offset to crop 
        scene[0].getBgTrajectory(frames, offset = off) 
        for i in range(numObjInScene):
            image = self.images.getRandomObj()       
            scene[i+1] = MoveableObject(img=image[0], filename = image[1], cvSize=self.size)  #i+1 because the scene starts with the background
            scene[i+1].getTrajectory(frames)  #i+1 because the scene starts with the background 
        self.getFramesFromScene(frames, scene, numObjInScene)
        self.scene = scene
        return self.output
    
    def getSeriesFromFile(self, file=PATHTOTRAJECTORYFILE, offset=None, maxLength=None): #be careful, this method returns several scenes
        with open(file, 'r') as f:
            lines = f.readlines()
            
        #Safe all lines in an array for later access and modulo operation
        allLines = np.array([None]*len(lines))    
        counter = 0
        for line in lines:  #lines can't be accessed by index. Need counter to provide this function
            allLines[counter] = json.loads(line)    #way faster then append
            counter += 1
            
        #apply only Trajectories of interest
        start = 0 if offset is None else offset
        end = len(allLines) if offset is None else start + maxLength
        output = []
        for i in range(start, end):
            oldScene = allLines[i%len(allLines)]
            output.append(self.getSeriesWithParam(oldScene['frames'], oldScene['objCount'], oldScene['trajectories']))
        return output

    def getSeriesWithParam(self, frames, objectCount, trajectories, offset=0):
        numObjInScene = objectCount
        scene = np.array([None]*(1+numObjInScene))   #scene contains the trajectories of the background and the drawn objects
        bg = trajectories[0]
        img = self.images.getBgFromKey(bg['f'])
        scene[0], off = self.getBackground([img, bg['f']], bg['cropPos'][0], bg['cropPos'][1])        #get background image as trajectory and the offset to crop 
        scene[0].getBgTrajectory(frames, off, bg['toPos'])
        for i in range(numObjInScene):
            obj = trajectories[i+1]
            image = self.images.getObjFromKey(obj['f'])
            scene[i+1] = MoveableObject(image, obj['f'], obj['fromPos'], obj['fromS'], obj['fromR'], self.size, offset)  #i+1 because the scene starts with the background
            scene[i+1].getTrajectoryWithParam(frames, obj['toPos'][0], obj['toPos'][1], obj['toS'], obj['toR'], obj['modes'])
        self.getFramesFromScene(frames, scene, numObjInScene)
        self.scene = scene
        return self.output       

    def getSeriesWithOffsetFromSeries(self, offset):
        #data = getTrajectoryData(self.seriesLength, self.scene)
        if(WITHRANDOMTRAJECTORYOFFSET):
            offset = uniform(TRAJECTORYOFFSET[0],TRAJECTORYOFFSET[1])
        traj = getTrajectoryData(self.seriesLength, self.scene)        
        self.getSeriesWithParam(traj['frames'], traj['objCount'], traj['trajectories'], offset)        
        
    def getBackground(self, bgFile=None, left=None, top=None):
        bgFile = self.images.getRandomBg() if bgFile is None else bgFile
        bgImg = bgFile[0] 
        if(left is None):        
            left = randint(0, bgImg.size[0]-self.size[0]-1-BGMAXTRANSLATION[0])   #just crops out parts of the background which really are on the img
        if(top is None):
            top  = randint(0, bgImg.size[1]-self.size[1]-1-BGMAXTRANSLATION[1])   #just crops out parts of the background which really are on the img
        bgImg = bgImg.crop((left, top, left+self.size[0]+2*BGMAXTRANSLATION[0], top+self.size[1]+2*BGMAXTRANSLATION[1]))   #crop background with random variables
        return MoveableObject(img=bgImg, filename = bgFile[1], pos=[-BGMAXTRANSLATION[0]+int(bgImg.size[0]/2.), -BGMAXTRANSLATION[1]+int(bgImg.size[1]/2.)], scale=1., rotation=0.) ,[left,top]       
        
    def getFramesFromScene(self, frames, scene, numObjInScene):
        #Creation of the single frames       
        #print ("Frames: ", frames)
        #print ("Objects in scene: ", numObjInScene)
        canvas = Image.new("RGBA", (self.size[0],self.size[1])) 
        for frame in range(frames):
            #print("Currently at frame: ",frame)   
            newFrame = canvas.copy()
            if(GETSEGMENTATIONMASK):
                frameLayer = np.array([None]*len(scene))
            for i in range(len(scene)):
                obj = scene[i]
                img = obj.img
                traj = obj.traj[frame]
                img = img.resize((int(round(img.size[0]*traj['s'])),int(round(img.size[1]*traj['s'])))).rotate(traj['r'], expand=1)   #scale first. If rotated, the size of the image is resized due expand=1!               
                posX, posY = int(traj['x']-img.size[0]/2.), int(traj['y']-img.size[0]/2.)
                if(GETSEGMENTATIONMASK):                        
                    layer = Image.new("RGBA", (self.size[0],self.size[1]))
                    layer.paste(img, (int(posX), int(posY)), img) 
                    frameLayer[i] = np.array(layer)                
                newFrame.paste(img, (posX,posY), img)
                
            npImg = np.array(newFrame)  #for faster pixel access convert image to np.array
            if(IMAGENOISE):
                self.output[frame] = addImageNoise(npImg, newFrame.size)
            else:
                self.output[frame] = npImg
            if(SAFEIMAGES): #Image noise needs fast pixel access --> numpy array. Must reconvert to PIL Image before saving
                Image.fromarray(npImg).save(getFilename(SERIESFOLDER, SERIESNAME, self.seriesLength, frame))
            if(GETSEGMENTATIONMASK):
                self.segmentationLayers[frame]=frameLayer

        #Additional options
        if(SAFETRAJECTORY):
            safeTrajectory(frames, scene)
        if(SAVESEGMENTATIONMASK):
            self.saveSegmentationMask()
        if(GETOPTICALFLOW):
            flow = getOpticalFlow(scene, frames, self.size)
        if(TESTOPTICALFLOW):
            applyFlowToImg(flow, self.output[frames-2], self.output[frames-1])          
        
    def saveSegmentationMask(self, withBg=False, folder="test", filename="segmentationMask"):
        start = 0 if(withBg) else 1
        for frame in range(len(self.segmentationLayers)):
            for obj in range(start, len(self.segmentationLayers[frame])):
                Image.fromarray(self.segmentationLayers[frame][obj]).save(folder+"/"+str(frame)+"-"+str(obj)+filename+".png")

    def getSegmentationMask(self):  #just returns the layer. If global GETSEGMENTATIONMASK is not set, the output is empty
        return self.segmentationLayers

    def getTrajectoryFromScene(self):
        return getTrajectoryData(self.seriesLength, self.scene)
    
    def __str__(self):
        print("Series length: ", self.seriesLength)
        print("Size of Canvas: ", self.size)
        print(self.images)
        return ""

class MoveableObject():
    '''
    supported file formats, see: http://pillow.readthedocs.org/en/3.1.x/handbook/image-file-formats.html
    rotation angle in degree (not radian!)
    translation Array in pixel [x,y]
    scale factor (multiplicative)
    '''
    def __init__(self, img, filename=None, pos=None, scale=None, rotation=None, cvSize=None, offset=None):
        self.img = img
        self.filename = filename if filename is not None else img.filename
        self.canvasSize = SIZE if cvSize is None else cvSize    #cvSize is the size of the canvas. initialized with global variable

        self.scale = scale if scale is not None else uniform(MINSCALE, MAXSCALE) #since we operate with floating point variables, this is uniform not randint  
        self.toScale = self.scale #just initializes the value. If not set, nothing happens! 

        if pos is None:
            #posX = randint(-int(self.img.size[0]*self.scale/2.), self.canvasSize[0]-1-int(self.img.size[0]*self.scale/2.))  #allows the image to partially leave the canvas on each side. Middle cannot leave Canvas (optional)
            #posY = randint(-int(self.img.size[1]*self.scale/2.), self.canvasSize[1]-1-int(self.img.size[1]*self.scale/2.))
            posX = randint(0, self.canvasSize[0]) #Sets the position of the middle of the image
            posY = randint(0, self.canvasSize[1])
            pos = [posX, posY]
        
        self.pos = pos
        self.toPos = self.pos   #just initializes the value. If not set, nothing happens!
        self.cropPos = [0,0]    #just initializes the value. If not set, nothing happens!
        self.offset = 0 if offset is None else offset

        #self.rotation = rotation if scale is not None else uniform(MINROTATE, MAXROTATE)  #since we operate with floating point variables, this is uniform not randint     
        self.rotation = rotation if scale is not None else uniform(0, 360)  #since we operate with floating point variables, this is uniform not randint     
        self.toRotation =  self.rotation #just initializes the value. If not set, nothing happens!
        
        self.modes = [0,0,0,0]  #initialized with linear acceleratingMode
        self.traj = {}
        self.param = {}

    def getTrajectory(self, frames): 
        #init all values
        self.toPos = getPossibleCoordinates(self.pos, self.canvasSize)
        self.toScale = uniform(MINSCALE, MAXSCALE)     #since we operate with floating point variables, this is uniform not randint
        self.toRotation = self.rotation + uniform(MINROTATE, MAXROTATE)  #since we operate with floating point variables, this is uniform not randint        
        translateModeX = randint(0, len(TRANSLATIONMODEX)-1)            
        translateModeY = randint(0, len(TRANSLATIONMODEY)-1)
        scaleMode = randint(0, len(SCALEMODE)-1)
        rotationMode = randint(0, len(ROTATIONMODE)-1)
        self.modes=[translateModeX, translateModeY, scaleMode, rotationMode]
        
        #apply trajectory
        step = 1./(frames-1) #-1 to include the last frame
        for frame in range(frames):   
            newx = round(acceleratingMode(translateModeX, self.toPos[0]-self.pos[0], frame, step))
            newy = round(acceleratingMode(translateModeY, self.toPos[1]-self.pos[1], frame, step))
            news = acceleratingMode(scaleMode, self.toScale-self.scale, frame, step)
            newr = acceleratingMode(rotationMode, self.toRotation-self.rotation, frame, step)
            self.traj[frame]={'x':self.pos[0]+newx,'y':self.pos[1]+newy,'s':self.scale+news,'r':self.rotation+newr}
        return self.traj   
        
    def getBgTrajectory(self, frames, offset, toPos=None):
        #init all values
        if(MOVEABLEBACKGROUND):
            if(toPos is not None):
                self.toPos = toPos
            else:
                toX = self.pos[0]+randint(-BGMAXTRANSLATION[0], BGMAXTRANSLATION[0])
                toY = self.pos[1]+randint(-BGMAXTRANSLATION[1], BGMAXTRANSLATION[1])        
                self.toPos=[toX, toY]
        self.toScale = 1.
        self.toRotation = 0.     
        self.modes = [0,0,0,0]
        self.cropPos = offset
        #apply trajectory
        step = 1./(frames-1) #-1 to include the last frame
        for frame in range(frames):   
            newx = round(acceleratingMode(0, self.toPos[0]-self.pos[0], frame, step))
            newy = round(acceleratingMode(0, self.toPos[1]-self.pos[1], frame, step))
            news = acceleratingMode(0, self.toScale-self.scale, frame, step)
            newr = acceleratingMode(0, self.toRotation-self.rotation, frame, step)
            self.traj[frame]={'x':self.pos[0]+newx,'y':self.pos[1]+newy,'s':self.scale+news,'r':self.rotation+newr}
        return self.traj   
    
    def getTrajectoryWithParam(self, frames, toX, toY, scale, rotate, modes): 
        step = 1./(frames-1)+self.offset   #-1 to include the last frame
        for frame in range(frames):
            newx = round(acceleratingMode(modes[0], toX-self.pos[0], frame, step))
            newy = round(acceleratingMode(modes[1], toY-self.pos[1], frame, step))
            news = acceleratingMode(modes[2], scale-self.scale, frame, step)
            newr = acceleratingMode(modes[3], rotate-self.rotation, frame, step)
            self.traj[frame]={'x':self.pos[0]+newx,'y':self.pos[1]+newy,'s':self.scale+news,'r':self.rotation+newr}
        return self.traj
        
    def getData(self): #brauche ich spaeter zum speichern der trajektorien
        data = {}
        data['f'] = self.filename
        data['fromPos'] = self.pos
        data['toPos'] = self.toPos
        data['cropPos'] = self.cropPos
        data['fromS'] = self.scale
        data['toS'] = self.toScale
        data['fromR'] = self.rotation
        data['toR'] = self.toRotation
        data['modes'] = self.modes
        data['offset'] = self.offset
        return data
        
    def __str__(self):
        print (self.filename)
        print ("pos: ", self.pos, "\ttoPos: ", self.toPos)
        print ("offset Crop: ", self.cropPos)
        print ("scale: ", self.scale, "\ttoScale: ", self.toScale)
        print ("rotation: ", self.rotation, "\tself.toRotation: ", self.toRotation)
        print ("modes: ", self.modes)
        for frame in self.traj:
            print (frame, self.traj[frame])
        return ""   #easier then making an object to print!
    
#0=nothing, 1=linear, 2=quadratic, 3=sqrt, 4=accelerating&breaking    
def acceleratingMode(mode, val, frame, step):
    if mode == 4:
        newVal = val*(1-math.cos(frame*step*math.pi))/2.
    elif mode == 3:
        newVal = val*math.sqrt(frame*step)
    elif mode == 2:
        newVal = val*frame*step*frame*step
    elif mode == 1:
        newVal = val*frame*step 
    else:
        newVal = val 
    return newVal

#if the images should be saved, you can get the filenames with the following function    
def getFilename(folder, imgName, seriesLength, frame):
    b = len(str(seriesLength))
    f = len(str(frame))
    return folder+"/"+"0"*(b-f)+str(frame)+imgName+".png"    

def getTrajectoryData(frames, scene):
    data={}
    data['frames'] = frames
    data['objCount'] = len(scene)-1 #background not counted
    objects = [None]*len(scene)
    for i in range(len(scene)):
        objects[i] = scene[i].getData()
    data['trajectories'] = objects
    return data
    
def safeTrajectory(frames, scene):
    data = getTrajectoryData(frames, scene)
    tempStr = json.dumps(data)+"\n"
    with open(PATHTOTRAJECTORYFILE, 'a') as f:  #json dump can't append to a file, so dump it in a string and write this to a file
        #json.dump(data, f)   
        f.write(tempStr)    

def keepMiddlepointOnCanvas(canvasSize, newPos):    #This functions returns a boolean for getPossibleCoordinates. If True no rejection
    if(KEEPMIDDLEOFIMAGEONCANVAS):
        if(0 <= newPos[0] <= canvasSize[0] and 0 <= newPos[1] <= canvasSize[1]):
            return True
        else:
            return False
    else:
        return True
         
def addImageNoise(img, size): #noise range is normally distributed
    def noise(val):     #used closure, because noise not needed elsewhere
        absval = abs(val)
        if (absval>=0.56):
            return 0
        elif (absval >=0.8):
            return 1*sign(val)
        elif (absval >=0.92):
            return 2*sign(val)
        elif (absval >=0.96):
            return 3*sign(val)
        elif (absval >=0.98):
            return 4*sign(val)
        else:
            return 5*sign(val)
    for x in range(size[0]):    #in python 2.7 change this to xrange!
        for y in range(size[1]):
            col = (noise(1-uniform(0,2)), noise(1-uniform(0,2)), noise(1-uniform(0,2)))  #right bound is not included. should not matter that much.
            for i in range(3):  #only use rgb, not alpha
                dc = img[x][y][i]-col[i]
                if(dc>=0 and dc<=255):
                    img[x][y][i]=dc
    return img
    
def sign(val):
    if val >= 0:
        return 1
    else:
        return -1

def getOpticalFlow():
    imgOrig = Image.open("test2.png").convert('RGBA')    #size = 64x64
    r = 45
    s = 1
    x = 63     #coordinates middle-point
    y = 63     #coordinates middle-point
    img = imgOrig.resize((int(round(imgOrig.size[0]*s)),int(round(imgOrig.size[1]*s)))).rotate(r, expand=1)
    canvas = Image.new("RGBA", (128,128)) 
    canvas.paste(img, (int(round(x-img.size[0]/2)), int(round(y-img.size[1]/2))), img)
    canvas.save("test/original.png")
    
    #Ab hier transformation!
    npcanvas = np.array(Image.new("RGBA", (128,128)))
    npObj = np.array(imgOrig)
    for i in range(imgOrig.size[0]):
        for j in range(imgOrig.size[1]):
            #pos = transformation([round(i-imgOrig.size[0]/2),round(j-imgOrig.size[1]/2)], r, s, [x,y])
            #pos = transformation([int(i-imgOrig.size[0]/2),int(j-imgOrig.size[1]/2)], r, s, [x,y])
            dx, dy = transformation([(i-imgOrig.size[0]/2),(j-imgOrig.size[1]/2)], r, s, [x,y])
            npcanvas[dx][dy] = npObj[i][j]
    Image.fromarray(npcanvas).save("test/erzeugt.png")

#def getOpticalFlow2(imgOrig):
def getOpticalFlow2(imgOrig, r, s, x, y):
    '''
    imgOrig = Image.open("test2.png").convert('RGBA')    #size = 64x64
    r = 22.1
    s = 2
    x = 63     #coordinates middle-point
    y = 63     #coordinates middle-point
    img = imgOrig.resize((int(round(imgOrig.size[0]*s)),int(round(imgOrig.size[1]*s)))).rotate(r, expand=1)
    canvas = Image.new("RGBA", (128,128)) 
    canvas.paste(img, (int(round(x-img.size[0]/2)), int(round(y-img.size[1]/2))), img)
    canvas.save("test/original.png")
    '''
    
    #Ab hier transformation!
    npcanvas = np.array(Image.new("RGBA", (128,128)))
    npObj = np.array(imgOrig)
    #Hole hier die wichtige Information über die Ränder:
    p1x, p1y = transformation([-imgOrig.size[0]/2,-imgOrig.size[1]/2], r, s, [0,0])
    p2x, p2y = transformation([-imgOrig.size[0]/2,imgOrig.size[1]/2], r, s, [0,0])
    mx, my = 0, 0
    sizex = int(2*max(abs(abs(p1x)-mx),abs(abs(p2x)-mx)))
    sizey = int(2*max(abs(abs(p1y)-my),abs(abs(p2y)-my)))
    #print("sizex,y", sizex, sizey)
    #print(inverseTransformation([(-sizex/2),(-sizey/2)], r, 1/s, [imgOrig.size[0]/2,imgOrig.size[1]/2]))
    #print(inverseTransformation([(sizex/2),(-sizey/2)], r, 1/s, [imgOrig.size[0]/2,imgOrig.size[1]/2]))
    #print(inverseTransformation([(sizex/2),(sizey/2)], r, 1/s, [imgOrig.size[0]/2,imgOrig.size[1]/2]))
    #print(inverseTransformation([(-sizex/2),(sizey/2)], r, 1/s, [imgOrig.size[0]/2,imgOrig.size[1]/2]))
    for i in range(sizex):
        for j in range(sizey):
            dx, dy = inverseTransformation([i-sizex/2,j-sizey/2], r, 1/s, [imgOrig.size[0]/2,imgOrig.size[1]/2])
            if(0<=dx<imgOrig.size[0] and 0<=dy<imgOrig.size[1]):
                #npcanvas[dx][dy] = npObj[i][j]
                #npcanvas[int(round(i+x-imgOrig.size[0]/2))][int(round(j+y-imgOrig.size[0]/2))] = npObj[dx][dy]
                npcanvas[int(round(i+x-sizex/2))][int(round(j+y-sizey/2))] = npObj[dx][dy]

    #Image.fromarray(npcanvas).save("test/erzeugt.png")   
    Image.fromarray(npcanvas)  
    
def transformation(vector, r, s, transl):
    cr = s*np.cos(r*np.pi/180)
    sr = s*np.sin(r*np.pi/180)
    x, y = vector[0], vector[1]
    newx = cr*x-sr*y
    newy = sr*x+cr*y
    #return (newx+transl[0], newy+transl[1])
    #return (np.ceil(newx+transl[0]), np.ceil(newy+transl[1]))
    return round(newx+transl[0]), round(newy+transl[1])

def inverseTransformation(vector, r, s, transl):
    cr = s*np.cos(r*np.pi/180)
    sr = s*np.sin(r*np.pi/180)
    x, y = vector[0], vector[1]
    newx = cr*x+sr*y
    newy = -sr*x+cr*y
    return int(newx+transl[0]), int(newy+transl[1])
    
def getPossibleCoordinates(fromPos, cvSize, a=None):
    a = DEFLECTIONBORDERLENGTH/2. if a is None else a
    counter = 0
    while(True):
        counter+=1
        if(counter==1000):
            print("Warning: needed 1000 attempts to find new coordinates for trajectory")
        newPos = [None, None]
        alpha = uniform(0, 2*np.pi)
        translationLength = uniform(TRANSLATIONLENGTH[0],TRANSLATIONLENGTH[1])
        
        if(a==0):
            x = math.floor(fromPos[0]+np.cos(alpha)*translationLength)
            y = math.floor(fromPos[1]-np.sin(alpha)*translationLength)
            return [x,y]
        else:
            if(fromPos[0] < cvSize[0]/2.):                  #wenn das Bild in der linken Hälfte
                alpha1 = np.arctan(fromPos[0]/a)
                if(alpha < np.pi/2. + alpha1 or alpha > np.pi*3/2. - alpha1):
                    newPos[0] = math.floor(fromPos[0]+np.cos(alpha)*translationLength)
            else:
                alpha1 = np.arctan((cvSize[0]-fromPos[0])/a)
                if(alpha > np.pi/2. - alpha1 and alpha < np.pi*3/2. + alpha1):
                    newPos[0] = math.floor(fromPos[0]+np.cos(alpha)*translationLength)            
            if(fromPos[1]<cvSize[1]/2.):                #wenn das Bild in der oberen Hälfte
                alpha2 = np.arctan(fromPos[1]/a)
                if(alpha < alpha2 or alpha > np.pi-alpha2):
                    newPos[1] = math.floor(fromPos[1]-np.sin(alpha)*translationLength)
            else:
                alpha2 = np.arctan((cvSize[1]-fromPos[1])/a) 
                if(alpha < np.pi+alpha2 or alpha > 2*np.pi - alpha2):
                    newPos[1] = math.floor(fromPos[1]-np.sin(alpha)*translationLength) 
            
            if(newPos[0] is not None and newPos[1] is not None and keepMiddlepointOnCanvas(cvSize, newPos)):
                return newPos

####################### tests #######################
if(False):   #test trajectory
    obj = MoveableObject(img = Image.open("objects/airplane/1e4fb40e5908f2bddf2f34e1100f0241-13_thumb.png"))
    obj.getTrajectory(9)
    print (obj)
    
if(False):  #test getFilesFromDirectory backgrounds
    files = getFilesFromDirectory("backgrounds","",False)
    file = files[0]
    print(file)    
    print (len(files))
    
if(False):  #test getFilesFromDirectory objects
    files = getFilesFromDirectory("objects","",True)
    file = files[0]
    print(file)
    print (len(files))

if(False): #test background trajectory
    IS = ImageSeries()
    obj = IS.getBackground()
    obj.getBgTrajectory(9)
    print (obj) 
    
if(False): #test safeTrajectory
    frames = 9
    IS = ImageSeries()
    obj1 = IS.getBackground()
    obj1.getBgTrajectory(frames)  
    obj2 = IS.getBackground()
    obj2.getBgTrajectory(frames)    
    scene = [obj1, obj2]
    safeTrajectory(frames, scene)
    
if(False):   #test getSeries
    IS = ImageSeries()
    obj = IS.getSeries()   
    
if(False):  #test getFilename
    print(getFilename("imgSeries","testBild.jpg",1000,114))

if(False):   #test keepMiddlepointOnCanvas
    traj={}
    traj['x'] = -32
    traj['y'] = -32
    print(keepMiddlepointOnCanvas([32,32],SIZE,traj))   #-16,-16
    traj['x'] = SIZE[0]+32
    traj['y'] = SIZE[0]+32
    print(keepMiddlepointOnCanvas([32,32],SIZE,traj))   #SIZE -16

'''
todo:
#rename Folders and files. Makes saving easier and smaller!

############## changelog ##############
#16.05.2016
#Remade optical flow with new functions.
#added new acceleration Mode (0) and shifted all others.
#   New Mode ignores set parameters for movement e.g. no rotation wanted --> ROTATIONMODE=0
#While loop in getPossibleCoordinates has now a warning message after 1000 iterations
#Changed keepMiddlepointOnCanvas. Is now implemented in getPossibleCoordinates.
#   if the sampled value doesn't stay on canvas, the newPos is rejected
#Added Image Handler. Images are now loaded just once, even from 'getSeriesFromFile'
#Solved bug, where the start-rotation is depending on global (MINROTATE, MAXROTATE)

#08.05.2016 
#changed translation vector creation. Vector now is defined via polor coordinates.
#Middle of the Image is (at the start) always on the canvas
#Newpos of the trajectory can now be adjusted by DEFLECTIONBORDERLENGTH
#added new method getSeriesWithOffsetFromSeries 
#added new method getTrajectoryFromScene
#added new method getSegmentationMask

#04.05.2016
#Middlepoint of object cannot leave canvas through trajectory
#Implemented option, so the trajectory can be used with a little offset (for faster trajectories)
#Trajectories now also have an adjustable minimum translation 

#02.05.2016
#Bug fixed, where background still moves even if global option MOVEABLEBACKGROUND is False
#Segmentations maks is now implemented correctly and can be saved as image
#Objects are now copped to the relevant bounding box and then resized
#getSeriesFromFile implemented and it works

#26.04.2016
#Code restructured and optimized
#Background kann sich auch bewegen
#Bilder werden jetzt bereits zu beginn geladen
#Neuer Modus sqrt
#image noise
#follow given trajectory
#counter entfernt
#Speicherung der Trajektory geändert
#Alpha zu den Bildern hinzugefügt (mehrere Stufen)

#Ubuntu 14.04 auf externe installiert
#Installation caffe, cuda etc
#Rekursives Auffinden aller Bilddateien in einem Ordner (bisher werden einfache alle Dateien genommen!
'''
