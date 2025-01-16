# -*- coding: utf-8 -*-
"""
V1.0 created on Thu Jul 14 11:22:53 2022
V1.1 updated on Fri Jan 27 11:12:00 2023
@author: v13927rb

Hg Green Line: Image Analysis v1.1
Imports 16-bit TIF files and analyses them to extract data about the fringe pattern.

Bugs to fix:
    1. Baseline fitting doesn't show error message when fit fails.
    
    2. Resizeable window to allow display on other monitors.
    
    3. Conversion to f-space is inaccurate.

Changelog:
    1.1:
    1.Small UI changes
    2. In ImageImporter: 
        a. On conversion from 16bit to 8bit added a round before uint8 conversion, so that values are not concatenated.
        b. Removed grey_image as it didn't work as expected.
    3. In FindCentre:
        a. Changed thresholding algorithm.  Now the summation of the r,g,b channels and application of the threshold is done manually and works better, as expected.
        b. Changed the layout of the UI for the centre guess to make it clearer.
        
    1.2:
    1. Changed conversion to 8 bit to remove display issue of pixels going to 0 when saturated in 16bit.
    
"""

#import required modules
import os
import threading
import cv2
import csv
import numpy as np
import tkinter as tk
from tkinter import ttk
import matplotlib.figure as mpl
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)

#set window resolution
import ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(2)

class ImageAnalysis(tk.Tk):
    #image property attributes
    SATURATION = 65536 * 3
    PIXEL_SIZE = (36/6720)
    
    #visual style attributes
    INSTRUCTION_FONT = ("TkDefaultFont", 10,"normal", "italic")
    TITLE_FONT = ("Bahnschrift", 14, "bold")
    ERROR_FONT = ("TkDefaultFont", 10,"normal", "italic")
    INSTRUCTION_WIDTH = 180
    PAD_X = (10,10)
    PAD_Y = (10,10)
    FIG_SIZE = (12,8)
    
    #error message attributes
    NO_ERR = ''
    IMAGE_ERR = 'Error: No image loaded.'
    CENTRE_ERR = 'Error: Centre coordinates not found.'
    DATA_ERR = 'Error: Data has not been generated.'
    BACKGROUND_ERR = 'Error: No background loaded.'
    NOBG_WARNING = 'Warning: No background image loaded. No Y-errors will be generated.'
    
    
    #list of output figures, ordered by superiority
    FIG_TITLES = np.array(['Imported Image: ', 'Imported Background: ', 'Thresholded Image: ', 'Spatial Data: ', 'Frequency Data: '])
    
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        self.container = ttk.Frame(self, width = 800, height = 800)
        self.container.pack(side="top", fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure([0,1], weight=1)
        
        #geometry
        self.rowconfigure(index = [0,1,2], weight = 1, minsize = 100)
        self.columnconfigure(index = 0, weight = 1, minsize = 400)
        self.minsize(500,600)
        self.title('Image Analysis')
        #self.resizable(0, 0)
        
        #style
        style = ttk.Style()
        style.configure("Red.TButton", foreground="red")
        style.configure("Red.TLabel", foreground = "red")
        style.configure("RedWhite.TLabel", foreground = "red", background = "white")
        style.configure("Title.TLabel", forground = "black", background = "white")
        style.configure("White.TFrame", background = "white")
        style.configure("Error.TFrame", background = "white", highlightbackground="red", highlightthickness=10)
        
        #object attributes
        self.imageLoaded = False
        self.backgroundLoaded = False
        self.centreFound = False
        self.dataAveraged = False
        self.windows = {}
        #self.currentImage: holds importer for main image
        #self.currentBackground: holds importer for background image
        #self.centreCoordinate: coords of centre
        #self.spatialX
        #self.spatialXerr
        #self.intensityY
        #self.intensityYerr
        #self.FreqData
        self.FRAMES = np.array([ImageImport, BackgroundImport, FindCentre, Averaging])
        
        #contained objects
        frm_title = ttk.Frame(self.container, relief = "ridge", width = 400, height = 50, style = "White.TFrame")
        frm_title.grid(row = 0, column = 0, padx = ImageAnalysis.PAD_X, pady = ImageAnalysis.PAD_Y, sticky = 'new')
        frm_title.pack_propagate(0)
        lbl_title = ttk.Label(frm_title, font = ImageAnalysis.TITLE_FONT, text = "Hg Green Line Image Analysis", style = "Title.TLabel")
        lbl_title.pack(padx = ImageAnalysis.PAD_X, pady = ImageAnalysis.PAD_Y)
        
        frm_error = ttk.Frame(self.container, relief = tk.SUNKEN, width = 400, height = 100)
        frm_error.grid(row = 0, column = 1, padx = ImageAnalysis.PAD_X, pady = ImageAnalysis.PAD_Y)
        frm_error.pack_propagate(0)
        frm_innerError = ttk.Frame(frm_error, relief = tk.GROOVE, width = 380, height = 80, style = "White.TFrame")
        frm_innerError.pack(padx = (10,10), pady = (10,10))
        frm_innerError.pack_propagate(0)
        self.errorMessage = ttk.Label(frm_innerError, font = ImageAnalysis.ERROR_FONT, style = "RedWhite.TLabel", wraplength='380')
        self.errorMessage.pack(padx=ImageAnalysis.PAD_X, pady = (10,10), fill = "both")
        
        self.frames = {}
        for F in (ImageImport, BackgroundImport, FindCentre, Averaging):
            frame = F(self.container, self)
            self.frames[F] = frame
        
        
    def displayFig(self, fig, figTitle, figDescription):
        #name figure
        fig.suptitle(figTitle + figDescription,fontweight="bold")
        
        #create new window, place figure on canvas, then on window
        figWindow = self.createWindow(figTitle)
        figWindow.title = figTitle
        canvas = FigureCanvasTkAgg(fig,master = figWindow)  
        canvas.draw()
        canvas.get_tk_widget().pack()
      
        #create and place MatPlotLib toolbar
        toolbar = NavigationToolbar2Tk(canvas,figWindow)
        toolbar.update()
        canvas.get_tk_widget().pack()
    
    def createWindow(self, windowName):
        #check if window already exists, destroy self and all inferior windows
        if (windowName != 'Imported Background: '):
            if windowName in self.windows:
                start = np.where(ImageAnalysis.FIG_TITLES==windowName)[0][0]
                for x in range(start, len(ImageAnalysis.FIG_TITLES)):
                    if ImageAnalysis.FIG_TITLES[x] in self.windows:
                        self.windows[ImageAnalysis.FIG_TITLES[x]].destroy()
                for x in range(start + 1, len(self.FRAMES)):
                    if self.FRAMES[x] in self.frames:
                        self.frames[self.FRAMES[x]].grid_forget()
                        self.frames[self.FRAMES[x]].destroy()
                        F = self.FRAMES[x]
                        frame = F(self.container, self)
                        self.frames[F] = frame
        else:
            if windowName in self.windows:
                self.windows[windowName].destroy()
            
        #create new, desired window
        newwindow = tk.Toplevel(self)
        self.windows[windowName] = newwindow
        return newwindow
    
    def getSaturation(self):
        #accessor for private attribute saturation
        return ImageAnalysis.SATURATION

class ImageImport(ttk.Frame):
    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent, relief='raised', borderwidth = 1, style = "White.TFrame")
        
        #geometry
        self.grid(row = 1, column = 0, columnspan = 2, sticky = "nsew", padx=ImageAnalysis.PAD_X, pady=ImageAnalysis.PAD_Y)
        self.columnconfigure(index = [0,1], weight = 1)
        self.rowconfigure(index = [0], weight = 1)
        
        #object attributes
        self.controller = controller
        self.instructionText = tk.StringVar()
        self.instructionText.set('1. Import your image as a 16-bit .TIF file.')
        
        #contained objects
        
        #instructions
        self.frm_fileInstruction = ttk.Frame(self, relief = tk.GROOVE, borderwidth=2, width = 200, height = 80)
        self.frm_fileInstruction.grid_propagate(0)
        self.frm_fileInstruction.columnconfigure(index = [0], weight = 1)
        self.frm_fileInstruction.rowconfigure(index = [0], weight = 1)
        self.frm_fileInstruction.grid(row = 0, column = 0,padx=(10,5), pady=ImageAnalysis.PAD_Y, sticky = 'nsew')
        
        self.lbl_fileInstruction = ttk.Label(self.frm_fileInstruction,wraplength=ImageAnalysis.INSTRUCTION_WIDTH,justify=tk.LEFT, textvariable = self.instructionText, font= ImageAnalysis.INSTRUCTION_FONT, style = "Red.TLabel")
        self.lbl_fileInstruction.grid(padx= (5,10), pady=ImageAnalysis.PAD_Y, sticky = 'nsew')
        
        #interactable box
        self.frm_interact = ttk.Frame(self, relief = tk.GROOVE, borderwidth = 2, width = 600, height = 80)
        self.frm_interact.grid_propagate(0)
        self.frm_interact.grid(row = 0, column = 1, padx=ImageAnalysis.PAD_X, pady=ImageAnalysis.PAD_Y)
        
        lbl_filePath = ttk.Label(self.frm_interact, text = 'File path:',justify=tk.LEFT)
        lbl_filePath.grid(row=0,column=0, padx=ImageAnalysis.PAD_X, pady=ImageAnalysis.PAD_Y)
        self.ent_filePath = ttk.Entry(self.frm_interact, width = 40)
        self.ent_filePath.grid(row=0,column=1, pady=ImageAnalysis.PAD_Y)
        
        btn_import = ttk.Button(self.frm_interact, text = 'Browse Files', command = self.importImage)
        btn_import.grid(row=0,column=2, padx=ImageAnalysis.PAD_X, pady=ImageAnalysis.PAD_Y, sticky = 'w')
         
    def importImage(self):
        
        #get image filepath
        imageFilepath = tk.filedialog.askopenfilename(title='Import .TIF image',filetypes=((".TIF",".TIF"),))
        
        if imageFilepath != '':
            self.controller.imageLoaded = False
            self.controller.centreFound = False
            self.controller.dataAveraged = False
            self.controller.backgroundLoaded = False
            
            #display image filepath
            self.ent_filePath.delete(0, tk.END) 
            self.ent_filePath.insert(0, str(imageFilepath))
            
            #import image
            myImporter = ImageImporter(self.controller)
            myImporter.importImage(imageFilepath)
            
            #display imported image
            f = mpl.Figure(figsize = ImageAnalysis.FIG_SIZE)
            a = f.add_subplot(111)
            a.imshow(myImporter.img8)
            a.set_xticks([]), a.set_yticks([])
            self.controller.displayFig(fig = f, figTitle = ImageAnalysis.FIG_TITLES[0], figDescription = myImporter.file_name)
            
            #update controller attributes
            self.controller.errorMessage['text'] = ImageAnalysis.NO_ERR
            self.controller.currentImage = myImporter
            self.controller.imageLoaded = True

class BackgroundImport(ImageImport):
    def __init__(self, parent, controller):
        #inherit from ImageImport
        ImageImport.__init__(self, parent, controller)
        
        self.grid(row = 2, column = 0, columnspan = 2, sticky = "nsew", padx=ImageAnalysis.PAD_X, pady=ImageAnalysis.PAD_Y)
        
        #change instruction text
        self.instructionText.set('2. Import the corresponding background image as a a 16-bit .TIF file.')
        self.bgText = tk.StringVar()
        self.bgText.set('')
        
        #style
        style = ttk.Style()
        style.configure("Red.text", foreground="red")
        
        #contained objects
        self.frm_interact.config(height = 80)
        self.frm_fileInstruction.config(height = 80)
        
        self.lbl_backgroundValue = ttk.Label(master = self.frm_interact, textvariable = self.bgText, justify=tk.LEFT, style='Red.TLabel')
        self.lbl_backgroundValue.grid(row=1, column=1)
        
       # btn_calcbg = ttk.Button(self.frm_interact, text = 'Calculate Background', command=self.calcBackground)
       # btn_calcbg.grid(row = 1, column = 2, padx=ImageAnalysis.PAD_X, pady=ImageAnalysis.PAD_Y)
        
    def importImage(self):
        self.controller.backgroundLoaded = False
        #get image filepath
        imageFilepath = tk.filedialog.askopenfilename(title='Import .TIF image',filetypes=((".TIF",".TIF"),))
        
        if imageFilepath != '':
            #display image filepath
            self.ent_filePath.delete(0, tk.END) 
            self.ent_filePath.insert(0, str(imageFilepath))
            
            #import image
            myImporter = ImageImporter(self.controller)
            myImporter.importImage(imageFilepath)
            
            #display imported image
            f = mpl.Figure(figsize = ImageAnalysis.FIG_SIZE)
            a = f.add_subplot(111)
            a.imshow(myImporter.img8)
            a.set_xticks([]), a.set_yticks([])
            self.controller.displayFig(fig = f, figTitle = ImageAnalysis.FIG_TITLES[1], figDescription = myImporter.file_name)
            
            #update controller attributes
            self.controller.errorMessage['text'] = ImageAnalysis.NO_ERR
            self.controller.currentBackground = myImporter
            self.controller.backgroundLoaded = True
        
    def calcBackground(self):
        try:
            self.bgText.set("Mean pixel value: %.2f" % self.controller.currentBackground.average_value )
            avgBackground = self.controller.currentBackground.average_value
        
            if (self.controller.dataAveraged):
                self.controller.intensityYerr = np.full(shape=len(self.controller.intensityY), fill_value=(avgBackground/np.sqrt(360)))
            
            self.controller.errorMessage['text'] = ImageAnalysis.NO_ERR
            self.controller.backgroundLoaded = True
        except AttributeError:
            self.controller.errorMessage['text'] = ImageAnalysis.BACKGROUND_ERR
        
class FindCentre(ttk.Frame):
    def __init__(self, parent, controller):
        #geometry
        ttk.Frame.__init__(self, parent, width = 500, relief='raised', borderwidth = 1, style = "White.TFrame")
        self.grid(row = 3, column = 0, columnspan = 2, sticky = "nsew",padx=ImageAnalysis.PAD_X, pady=ImageAnalysis.PAD_Y)
        
        #object attributes
        self.controller = controller
        self.instructionText = '3. Calculate the centre of the fringe pattern. The calculated centre position is given as a coordinate and marked on the output image as a red cross. If the centre is inaccurate, adjust the parameters.'      
        self.baseText = 'Centre coordinates: '
        self.labelText = tk.StringVar()
        self.labelText.set(self.baseText)
        
        #contained objects
        #instructions
        frm_fileInstruction = ttk.Frame(self, relief = tk.GROOVE, borderwidth=2, width =190, height = 200)
        frm_fileInstruction.grid_propagate(0)
        frm_fileInstruction.columnconfigure(index = [0], weight = 1)
        frm_fileInstruction.rowconfigure(index = [0], weight = 1)
        frm_fileInstruction.grid(row = 0, column = 0,padx=(10,5), pady=ImageAnalysis.PAD_Y)
        
        self.lbl_fileInstruction = ttk.Label(frm_fileInstruction,wraplength=ImageAnalysis.INSTRUCTION_WIDTH,justify=tk.LEFT, text = self.instructionText, font= ImageAnalysis.INSTRUCTION_FONT, style = "Red.TLabel")
        self.lbl_fileInstruction.grid(padx=(5,10), pady=ImageAnalysis.PAD_Y)
        
        #interactable box
        frm_interact = ttk.Frame(self, relief = tk.GROOVE, borderwidth = 2, width = 600, height = 190)
        frm_interact.grid_propagate(0)
        frm_fileInstruction.columnconfigure(index = [0,1,2], weight = 1)
        frm_fileInstruction.rowconfigure(index = [0,1], weight = 1)
        frm_interact.grid(row = 0, column = 1, padx=ImageAnalysis.PAD_X, pady=ImageAnalysis.PAD_Y)
        
        #threshold
        lbl_threshold = ttk.Label(master = frm_interact, text = 'Intensity threshold:',justify=tk.LEFT)
        lbl_threshold.grid(row = 0, column = 1,padx=ImageAnalysis.PAD_X, pady=ImageAnalysis.PAD_Y, sticky = 'w')
        self.ent_threshold = ttk.Entry(master = frm_interact, width = 15)
        self.ent_threshold.grid(row = 0, column = 2,padx=(10,0), pady=ImageAnalysis.PAD_Y, sticky = 'w')
        lbl_thresholdUnit = ttk.Label(master = frm_interact, text = '%',justify=tk.LEFT)
        lbl_thresholdUnit.grid(row = 0, column = 3, pady=ImageAnalysis.PAD_Y, sticky = 'w')
        
        #maximum number of fringes to average over
        lbl_maximum = ttk.Label(master = frm_interact, text = 'Number of fringes to average over:',justify=tk.LEFT)
        lbl_maximum.grid(row = 1, column = 1,padx=ImageAnalysis.PAD_X, pady=ImageAnalysis.PAD_Y, sticky = 'w')
        self.ent_maximum = ttk.Entry(master = frm_interact, width = 15)
        self.ent_maximum.grid(row =1, column = 2,padx=ImageAnalysis.PAD_X, pady=ImageAnalysis.PAD_Y, sticky = 'w')
        
        #guess at centre position
        lbl_centreGuess = ttk.Label(master = frm_interact, text = 'Initial guess at centre position:\n                   ( x , y )',justify=tk.LEFT)
        lbl_centreGuess.grid(row = 2, column = 1,padx=ImageAnalysis.PAD_X, pady=ImageAnalysis.PAD_Y, sticky = 'w')
        
        lbl_openp = ttk.Label(master = frm_interact, text = "(")
        lbl_openp.grid(row=2,column=1, sticky = "e")
        self.ent_centreGuessX = ttk.Entry(master = frm_interact, width = 5)
        self.ent_centreGuessX.grid(row = 2, column = 2,padx=ImageAnalysis.PAD_X, pady=ImageAnalysis.PAD_Y, sticky = 'w')
        lbl_comma = ttk.Label(master = frm_interact, text = ",")
        lbl_comma.grid(row=2,column=2)
        self.ent_centreGuessY = ttk.Entry(master = frm_interact, width = 5)
        self.ent_centreGuessY.grid(row = 2, column = 2,padx=ImageAnalysis.PAD_X, pady=ImageAnalysis.PAD_Y, sticky = 'e')
        lbl_closep = ttk.Label(master = frm_interact, text = ")")
        lbl_closep.grid(row=2,column=3, sticky = "w")
        
        
        self.lbl_centre = ttk.Label(master = frm_interact, textvariable = self.labelText, justify=tk.LEFT, style = "Red.TLabel")
        self.lbl_centre.grid(row = 3, column = 1, columnspan = 2,padx=ImageAnalysis.PAD_X, pady=ImageAnalysis.PAD_Y, sticky = 'w')
        
        btn_centreFinding = ttk.Button(master = frm_interact, text = 'Go', command=self.calcCentre)
        btn_centreFinding.grid(row = 3, column = 3,padx=ImageAnalysis.PAD_X, pady=ImageAnalysis.PAD_Y)
        
    def calcCentre(self):
        if (self.controller.imageLoaded == True):
            try:
                #initialise error checking
                badValues = True
                badCentre = True
                self.controller.errorMessage['text'] = ImageAnalysis.NO_ERR
                self.controller.centreFound = False
                self.controller.dataAveraged = False
                
                #get user inputs
                centre_x_guess = int(self.ent_centreGuessX.get())
                centre_y_guess = int(self.ent_centreGuessY.get())
                max_a = int(self.ent_maximum.get())
                
                percent_filter = self.controller.getSaturation() * float(self.ent_threshold.get()) * 1/100
                
                #NEW threshold image
                image16rgb = self.controller.currentImage.img16
                image16i = np.sum(image16rgb, axis=2)
                
                
                thresholdImg = np.multiply(image16i>percent_filter, 1)
                
                badValues = False
                
                #calculate centre
                centre_x, centre_y = self.findCentre(centre_x_guess, centre_y_guess, max_a, thresholdImg)
                badCentre = False
                
            except ValueError:
                self.controller.errorMessage['text'] = "Error: Please enter valid values. Coordinates and number of fringes must be integer. Do not enter a percentage sign for the threshold."
                badValues = True
            except IndexError:
                self.controller.errorMessage['text'] = "Error: Centre could not be calculated. Change parameters and try again."
                badCentre = True
                
            if not(badValues):
                #display threshold image
                f = mpl.Figure(figsize = ImageAnalysis.FIG_SIZE)
                a = f.add_subplot(111)
                a.imshow(thresholdImg, cmap = 'gray')
                
                #display calculated centre
                if not(badCentre):
                    a.scatter(centre_x, centre_y, color= 'r', s = 10, marker = 'x')
                a.set_xticks([]), a.set_yticks([])
                
                title = ImageAnalysis.FIG_TITLES[2]
                self.controller.displayFig(fig = f, figTitle = title, figDescription = self.controller.currentImage.file_name)
                
                if not(badCentre):
                    #output centre
                    centreText = ' (' + str(centre_x) + ', ' + str(centre_y) + ')'
                    self.labelText.set(self.baseText + centreText)
                    #update controller attributes
                    self.controller.centreCoordinates = [centre_x, centre_y]
                    self.controller.centreFound = True
            
        else:
            self.controller.errorMessage['text'] = ImageAnalysis.IMAGE_ERR
        
    def fringeFinding(self, starting_point, direction, img):
        #finds and returns the locations of all the bright fringes in an image, either horizontally or vertically from a start pixel
        positive_start, negative_start = starting_point
        img = img.astype(int)
        if(direction == "vertical"):
            #go up and down
            starting_pix_value = (img[(positive_start[1]),(positive_start[0])])
            pix_value = starting_pix_value
            current_y = positive_start[1]
           
            while(pix_value == starting_pix_value):
                current_y += 1
                pix_value = (img[current_y,positive_start[0]])
               
            while(pix_value != starting_pix_value):
                current_y += 1
                pix_value = (img[current_y,positive_start[0]])
           
            top_edge = [positive_start[0], current_y]
           
            starting_pix_value = (img[negative_start[1],negative_start[0]])
            pix_value = starting_pix_value
            current_y = negative_start[1]
           
            while(pix_value == starting_pix_value):
                current_y -= 1
                pix_value = (img[current_y,negative_start[0]])
               
            while(pix_value != starting_pix_value):
                current_y -= 1
                pix_value = (img[current_y,negative_start[0]])
               
            bottom_edge = [negative_start[0], current_y]
           
        elif(direction == "horizontal"):
            #go side to side
            starting_pix_value = (img[positive_start[1],positive_start[0]])
            pix_value = starting_pix_value
            current_x = positive_start[0]
           
            while(pix_value == starting_pix_value):
                current_x += 1
                pix_value = (img[positive_start[1],current_x])
               
            while(pix_value != starting_pix_value):
                current_x += 1
                pix_value = (img[positive_start[1],current_x])
               
            top_edge = [current_x, positive_start[1]]
           
            starting_pix_value = (img[negative_start[1],negative_start[0]])
            pix_value = starting_pix_value
            current_x = negative_start[0]
           
            while(pix_value == starting_pix_value):
                current_x -= 1
                pix_value = (img[negative_start[1],current_x])
               
            while(pix_value != starting_pix_value):
                current_x -= 1
                pix_value = (img[negative_start[1],current_x])
               
            bottom_edge = [current_x, negative_start[1]]  
       
        return np.vstack([top_edge, bottom_edge])
    
    def findCentre(self, centre_x_guess, centre_y_guess, number_to_average, img):
        #Calculate the centre by averaging over several fringes
        centre_guess = np.array([[centre_x_guess, centre_y_guess], [centre_x_guess, centre_y_guess]])
        centre_calcs_y = np.array([])
    
        direction = "vertical"
        fringe_edges = self.fringeFinding(centre_guess, direction, img)
        for x in range(number_to_average):
            centre_calcs_y = np.append(centre_calcs_y, (fringe_edges[0][1] + fringe_edges[1][1]) / 2)  
            fringe_edges = self.fringeFinding(fringe_edges, direction, img)
       
        centre_y = round(centre_calcs_y.sum() / len(centre_calcs_y))    
    
    
        centre_guess = [[centre_x_guess, centre_y], [centre_x_guess, centre_y]]
        centre_calcs_x = np.array([])
    
        direction = "horizontal"
        fringe_edges = self.fringeFinding(centre_guess, direction, img)
        for x in range(number_to_average):
            centre_calcs_x = np.append(centre_calcs_x, (fringe_edges[0][0] + fringe_edges[1][0]) / 2)
            fringe_edges = self.fringeFinding(fringe_edges, direction, img)
           
        centre_x = round(centre_calcs_x.sum() / len(centre_calcs_x))    
       
        return centre_x, centre_y

class Averaging(ttk.Frame):
    def __init__(self, parent, controller):
        #geometry
        ttk.Frame.__init__(self, parent, height = 200, width = 500, relief='raised', borderwidth = 1, style = "White.TFrame")
        self.grid(row = 4, column = 0, columnspan = 2, sticky = "nsew", padx=(10,10), pady=(10,10))
        
        #object attributes
        self.controller = controller
        self.position = 0
        self.position_err = 0
        self.spatial_data = 0
        self.intensity_err = 0
        instructions = '4. Once the centre calculation is accurate, run the averaging algorithm to perform a 360\u00B0 average about the centre.'
        
        #contained objects
        #instructions
        frm_fileInstruction = ttk.Frame(self, relief = tk.GROOVE, borderwidth=2, width = 200, height = 120)
        frm_fileInstruction.grid_propagate(0)
        frm_fileInstruction.columnconfigure(index = [0], weight = 1)
        frm_fileInstruction.rowconfigure(index = [0], weight = 1)
        frm_fileInstruction.grid(row = 0, column = 0,padx=(10,5), pady=ImageAnalysis.PAD_Y)
        
        self.lbl_fileInstruction = ttk.Label(frm_fileInstruction,wraplength=ImageAnalysis.INSTRUCTION_WIDTH,justify=tk.LEFT, text = instructions, font= ImageAnalysis.INSTRUCTION_FONT, style = "Red.TLabel")
        self.lbl_fileInstruction.grid(padx=(5,10), pady=ImageAnalysis.PAD_Y)
        
        #interactable box
        frm_interact = ttk.Frame(self, relief = tk.GROOVE, borderwidth = 2, width = 600, height = 120)
        frm_interact.grid_propagate(0)
        frm_fileInstruction.columnconfigure(index = [0,1], weight = 1)
        frm_fileInstruction.rowconfigure(index = [0,1], weight = 1)
        frm_interact.grid(row = 0, column = 1, padx=ImageAnalysis.PAD_X, pady=ImageAnalysis.PAD_Y)
      
        btn_averaging = ttk.Button(master = frm_interact, text='Perform Averaging', command=lambda: doThread(self.performAveraging, self.controller.errorMessage))
        btn_averaging.grid(row=0,column=3,padx=ImageAnalysis.PAD_X, pady=ImageAnalysis.PAD_Y, sticky = 'w')
        
        btn_transform = ttk.Button(master = frm_interact, text='Transform to F-Space', command = self.transformToFSpace)
        btn_transform.grid(row=1,column=3,padx=ImageAnalysis.PAD_X, pady=ImageAnalysis.PAD_Y, sticky = 'w')

        btn_saveFile = ttk.Button(master = frm_interact, text = 'Save Spatial Data as .csv', command = lambda: self.saveFile(self.controller.spatialX, self.controller.spatialXerr, self.controller.intensityY, self.controller.intensityYerr, "myFile"))
        btn_saveFile.grid(row =0, column = 4,padx=ImageAnalysis.PAD_X, pady=ImageAnalysis.PAD_Y, sticky = 'w')
        
        btn_saveFileFreq = ttk.Button(master = frm_interact, text = 'Save Frequency Data as .csv', command = lambda: self.saveFile(self.controller.FreqData[:,0], self.controller.FreqData[:,1], self.controller.FreqData[:,2], self.controller.FreqData[:,3], "myFile"))
        btn_saveFileFreq.grid(row = 1, column = 4,padx=ImageAnalysis.PAD_X, pady=ImageAnalysis.PAD_Y, sticky = 'w')
        
        #self.lbl_averaging = ttk.Label(frm_interact, style = "Red.TLabel")
        #self.lbl_averaging.grid(row = 2, column = 2, sticky = 'ew')
        
        lbl_focalLength = ttk.Label(frm_interact, text = "Focal length of lens:")
        lbl_focalLength.grid(row = 1, column = 0, sticky = 'nw',padx=ImageAnalysis.PAD_X, pady=ImageAnalysis.PAD_Y)
        self.ent_focalLength = ttk.Entry(frm_interact, width = 7)
        self.ent_focalLength.grid(row = 1, column = 1, sticky = 'e', pady=ImageAnalysis.PAD_Y)
        lbl_mm = ttk.Label(frm_interact, text = "mm")
        lbl_mm.grid(row = 1, column = 2, sticky = 'w')
        
    def transformToFSpace(self):
        Radius = self.controller.spatialX #metres
        Radius_err = self.controller.spatialXerr
        Data = self.controller.intensityY #intensity arb units
        Data_err = self.controller.intensityYerr
        
        #constants
        SATURATION = 65536  #only true for 16 bit TIFs
        T = 4         #mm, true for current etalons
        T_err = 0.01
        
        F = float(self.ent_focalLength.get())
        F_err = 0.5
        
        #r_first_half = position[0:limit]
        #r_centre = position[limit]
        #r_second_half = position[limit+1:(limit*2)+1]

        #transform data into frequency space, save and display it
        self.controller.FreqData = self.Transform(Radius, Radius_err, Data, Data_err, T, T_err, F, F_err)
        
    
        #plotting data
        f = mpl.Figure(figsize = ImageAnalysis.FIG_SIZE)
        a = f.add_subplot(111)
        a.plot(self.controller.FreqData[:,0], self.controller.FreqData[:,2], linewidth = 0.5, color = 'black')
        a.scatter(self.controller.FreqData[:,0], self.controller.FreqData[:,2], s=4, marker='x', color = 'red')
        a.set_xlabel('Frequency (GHz)')
        a.set_ylabel('Intensity (Arbitrary Units)')
        title = ImageAnalysis.FIG_TITLES[4]
        self.controller.displayFig(fig = f, figTitle = title, figDescription = self.controller.currentImage.file_name)
        
        
    def Transform(self, Radius, Radius_err, Data, Data_err, T, T_err, F, F_err):
        #returns MHz freq and arb units intensity
        C = 299792458
        n = 14646
        FreqData = np.empty((0,4))
       
        for i in range(Radius.size):
            temp1 = Radius[i] /F
            temp = (n*C / (2*T*np.cos(temp1))) / 10**6
            
            d_dT = (-C*n / (2 * np.cos(Radius[i]/F) * T**2))
            d_dR = (C*n * np.sin(Radius[i]/F) / (2*F*T* np.cos(Radius[i]/F)**2))
            d_dF = (-C*n*Radius[i] * np.sin(Radius[i]/F) / (2*T*(F**2) * (np.cos(Radius[i]/F))**2))
            
            temp_err = np.sqrt(d_dT**2 * T_err**2 + d_dR**2 * Radius_err[i]**2 + d_dF**2 * F_err**2) * 10**-6
           
            FreqData = np.append(FreqData, np.array([[temp, temp_err, Data[i], Data_err[i]]]), axis=0)
             
        return FreqData
    
    
    def performAveraging(self):
        
        if (self.controller.imageLoaded == True) and (self.controller.centreFound == True):
            #self.controller.errorMessage['text'] = ImageAnalysis.NO_ERR
            self.controller.dataAveraged = False
            
            
            if self.controller.backgroundLoaded:
                #crop image to 1:1 ratio based on shortest distance from centre to edge
                cropped_image, limit = self.cropImage(self.controller.currentImage.img16, self.controller.centreCoordinates)
                cropped_bg, dump = self.cropImage(self.controller.currentBackground.img16, self.controller.centreCoordinates)
                
                #unaveraged sum pointwise radially over specified angles
                angles = np.arange(0,360,1)
                slice_1 = np.zeros(self.height)
                slice_1_bg = np.zeros(self.height)
                iterator = 0
                for theta in angles:
                    M = cv2.getRotationMatrix2D((limit,limit),theta,1)
                    dst = cv2.warpAffine(cropped_image,M,((limit*2)+1,(limit*2)+1))
                    dst_bg = cv2.warpAffine(cropped_bg,M,((limit*2)+1,(limit*2)+1))
                    for a in range(self.height):
                        slice_1[a] = slice_1[a] + intensity(dst[limit, a])
                        slice_1_bg[a] = slice_1_bg[a]+ intensity(dst_bg[limit, a])
                    iterator += 1
                
                #averaged sum pointwise radially over specified angles
                self.controller.intensityY = slice_1 / iterator
                self.controller.intensityYerr = slice_1_bg / iterator
                
                #conversion from pixel number to spatial domain (metres)
                position1 = np.arange(-limit, limit+1, 1)
                self.controller.spatialX = position1 * ImageAnalysis.PIXEL_SIZE
                
                self.controller.errorMessage['text'] = ImageAnalysis.NO_ERR
                
            else:
                self.controller.errorMessage['text'] = ImageAnalysis.NOBG_WARNING
                
                #crop image to 1:1 ratio based on shortest distance from centre to edge
                cropped_image, limit = self.cropImage(self.controller.currentImage.img16, self.controller.centreCoordinates)
                
                #unaveraged sum pointwise radially over specified angles
                angles = np.arange(0,360,1)
                slice_1 = np.zeros(self.height)
                iterator = 0
                for theta in angles:
                    M = cv2.getRotationMatrix2D((limit,limit),theta,1)
                    dst = cv2.warpAffine(cropped_image,M,((limit*2)+1,(limit*2)+1))
                    for a in range(self.height):
                        slice_1[a] = slice_1[a] + intensity(dst[limit, a])
                    iterator += 1
                
                #averaged sum pointwise radially over specified angles
                self.controller.intensityY = slice_1 / iterator
                
                #conversion from pixel number to spatial domain (metres)
                position1 = np.arange(-limit, limit+1, 1)
                self.controller.spatialX = position1 * ImageAnalysis.PIXEL_SIZE
                
                self.controller.intensityYerr = np.full(shape=len(self.controller.intensityY), fill_value=(0))
                
            
            self.controller.spatialXerr = np.full(shape=len(self.controller.spatialX), fill_value=(ImageAnalysis.PIXEL_SIZE / 2))
            
            #plotting data
            f = mpl.Figure(figsize = ImageAnalysis.FIG_SIZE)
            a = f.add_subplot(111)
            a.plot(self.controller.spatialX, self.controller.intensityY, linewidth = 0.5, color = 'black')
            a.scatter(self.controller.spatialX, self.controller.intensityY, s=4, marker='x', color = 'red')
            a.set_xlabel('Radius (mm)')
            a.set_ylabel('Intensity (Arbitrary Units)')
            title = ImageAnalysis.FIG_TITLES[3]
            self.controller.displayFig(fig = f, figTitle = title, figDescription = self.controller.currentImage.file_name)
            
            self.controller.dataAveraged = True
            self.controller.errorMessage['text']= ImageAnalysis.NO_ERR
            
        elif (self.controller.centreFound == False) and (self.controller.imageLoaded == True):
            self.controller.errorMessage['text'] = ImageAnalysis.CENTRE_ERR
        else:
            self.controller.errorMessage['text'] = ImageAnalysis.IMAGE_ERR
        
        
    def cropImage(self, original_img, centre_coords):
        #crop image to a square around the centre for analysis
        shape = original_img.shape
        rows = shape[0]
        columns = shape[1]
    
        
        x_left = centre_coords[0]
        x_right = columns - centre_coords[0] - 1
        y_top = centre_coords[1]
        y_bot = rows - centre_coords[1] - 1
        
        if x_left <= x_right and x_left <= y_top and x_left <= y_bot:
            limit = x_left
        elif x_right <= x_left and x_right <= y_top and x_right <= y_bot:
            limit = x_right
        elif y_top <= x_right and y_top <= x_left and y_top <= y_bot:
            limit = y_top
        elif y_bot <= x_right and y_bot <= x_left and y_bot <= y_top:
            limit = y_bot
        
        y = centre_coords[1] - limit
        x = centre_coords[0] - limit
        global height 
        self.height = (limit * 2) +1
        global width
        self.width = (limit * 2) +1
        
        crop_img = original_img[y:y+self.height+1, x:x+self.width+1]
        
        self.controller.dataAveraged = True
        
        return crop_img, limit  

    def saveFile(self, X, X_err, Y, Y_err, FileName):
        #save a csv file
        if self.controller.dataAveraged:
            self.controller.errorMessage['text'] = ImageAnalysis.NO_ERR
            
            filepath = tk.filedialog.asksaveasfilename(defaultextension='.csv', filetypes = (('.csv','*.csv'),))
            file = open(filepath,'w', newline = '')
            datawriter = csv.writer(file, delimiter=',')
            for i in range(len(X)):
                datawriter.writerow([X[i], X_err[i], Y[i], Y_err[i]])
               
            file.close()
        else:
            self.controller.errorMessage['text'] = ImageAnalysis.DATA_ERR

class ImageImporter:
    #class that imports and holds an image in both 16 and 8-bit
    def __init__(self, controller):
        self.controller = controller
        
    def importImage(self, filepath):
        file_name_temp = os.path.basename(filepath)
        self.file_name = os.path.splitext(file_name_temp)[0]
        
        #imports image as (r,g,b) with 16-bit depth (max value = 65535)
        img16 = cv2.imread(filepath, -1)
        self.img16 = img16
        
        #converts image to (r,g,b) with 8-bit depth (max value = 255)
        img8 = (img16 >> 8).astype('uint8')
        self.img8 = img8
        
        #gets x and y dimensions of image (in pixels)
        self.height = self.img16.shape[0]
        self.width = self.img16.shape[1]

def intensity(rgb):
    #calculates the intensity value of a pixel, given rgb data
    I = np.sum(rgb) / 3
    return I

def doThread(work, messageBox):
    #creates a second thread so that the GUI and the processing can both be active
    messageBox['text'] = 'Processing...'
    t1=threading.Thread(target=work)
    t1.start()

#tkinter mainloop
if __name__ == "__main__":
    app = ImageAnalysis()
    app.mainloop()
