# -*- coding: utf-8 -*-
"""
V1.0 Created on Fri Aug 26 13:01:31 2022
V1.1 updated on Fri Jan 27 15:30:00 2023
V1.2 updated on Thurs Apr 11 15:28 2024
@author: v13927rb

Hg Green Line: Gaussian Fitting v1.2

Changelog:
    1. Fixed issues with failed fitting when errors are 0.
    2. Tweaked baseline minima locating to be less susceptible to noise.
    
"""

#import required modules
import csv
import os
import tkinter as tk
from tkinter import ttk
import numpy as np
import  matplotlib.figure as mpl
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
import scipy.signal as scp
from scipy.optimize import curve_fit
from scipy.optimize import OptimizeWarning

#use warnings as exceptions
import warnings
warnings.filterwarnings("error")

warnings.simplefilter("error", OptimizeWarning)

#set window resolution
import ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(2)

class Fitting(tk.Tk):
    #visual style attributes 
    INSTRUCTION_FONT = ("TkDefaultFont", 10,"normal", "italic")
    TITLE_FONT = ("Bahnschrift", 14, "bold")
    ERROR_FONT = ("TkDefaultFont", 10,"normal", "italic")
    ERROR_FONT = ("Arial", 11,"bold")
    INSTRUCTION_WIDTH = 150
    PAD_X = (10,10)
    PAD_YS = (5,5)
    PAD_Y = (10,10)
    FIG_SIZE = (8,6)
    FULL_WIDTH = 1000
    FULL_HEIGHT = 850
    
    COLORS = np.array(['r', '#2a6e00', '#ff8519', '#00c9cc', '#e82389','#ffdd00','#636363'])
    
    #list of output figures, ordered by superiority
    FIG_TITLES = np.array(['Imported Data: ', 'Fitted Baseline: ', 'Data Corrected with Baseline: ', 'Gauss Guesses: ', 'Gauss Fits: '])
    
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        container = ttk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        
        #style
        style = ttk.Style()
        style.configure("Red.TButton", foreground="red")
        style.configure("Red.TLabel", foreground = "red")
        style.configure("RedWhite.TLabel", foreground = "red", background = "white")
        style.configure("Title.TLabel", forground = "black", background = "white")
        style.configure("White.TFrame", background = "white")
        style.configure("Error.TFrame", background = "white", highlightbackground="red", highlightthickness=10)
        
        #geometry
        self.width = Fitting.FULL_WIDTH
        self.height = Fitting.FULL_HEIGHT
        self.minsize(self.width,self.height)
        self.title('Multiple Gaussian Fitting')
        self.resizable(0, 0)
        
        #object attributes
        self.dataLoaded = False
        self.baselineSubtracted = False
        self.guessesInput = False
        self.gaussiansFitted = False
        
        self.windows = {}
        
        #self.data: four column array of X, Xerr, Y, Yerr
        #self.dataLoaded: boolean
        #self.file_name: name of loaded data
        #self.ROI_data: four column array of ROI X, Xerr, Y, Yerr
        
        
        #contained objects
        #title
        frm_title = ttk.Frame(container, relief = "ridge", width = self.width/2, height = 50, style = "White.TFrame")
        frm_title.grid(row = 0, column = 0, padx = Fitting.PAD_X, pady = Fitting.PAD_Y, sticky = 'new')
        frm_title.pack_propagate(0)
        lbl_title = ttk.Label(frm_title, font = Fitting.TITLE_FONT, text = "Hg Green Line: Gaussian Fitting", style = "Title.TLabel")
        lbl_title.pack(padx = Fitting.PAD_X, pady = Fitting.PAD_Y)
        
        #errorbox
        frm_error = ttk.Frame(container, relief = tk.SUNKEN, width = self.width/2, height = 70)
        frm_error.grid(row = 0, column = 1, padx = Fitting.PAD_X, pady = Fitting.PAD_Y)
        frm_error.pack_propagate(0)
        
        frm_innerError = ttk.Frame(frm_error, relief = tk.GROOVE, width = 380, height = 50, style = "White.TFrame")
        frm_innerError.pack(padx = Fitting.PAD_X, pady = Fitting.PAD_Y)
        frm_innerError.pack_propagate(0)
        
        self.errorMessage = ttk.Label(frm_innerError, font = Fitting.ERROR_FONT, style = "RedWhite.TLabel", wraplength='380')
        self.errorMessage.pack(padx=Fitting.PAD_X, pady = Fitting.PAD_Y, fill = "both")
        
        #interactibles
        self.frames = {}
        for F in (DataImport, BaselineFitting, GaussianFitting):
            frame = F(container, self)
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
        #check if window already exists, destroy all inferior windows
        if windowName in self.windows:
            start = np.where(Fitting.FIG_TITLES==windowName)[0][0]
            for x in range(start, len(Fitting.FIG_TITLES)):
                if Fitting.FIG_TITLES[x] in self.windows:
                    self.windows[Fitting.FIG_TITLES[x]].destroy()
                    
        #create new, desired window
        newwindow = tk.Toplevel(self)
        #newwindow.geometry('800x800')
        self.windows[windowName] = newwindow
        return newwindow

class Interactible(ttk.Frame):
    def __init__(self, parent, controller, height, width):
        ttk.Frame.__init__(self, parent, width = width, height = height, relief='ridge', borderwidth = 3,style = "White.TFrame") 
        
        #geometry
        self.grid_propagate(0)
        
        #object attributes
        self.parent = parent
        self.width = width
        self.height = height     
        self.controller = controller
        self.instructionText = tk.StringVar()
        
    def populate(self, row, column): 
        self.grid(row = row, column = column, columnspan = 2, padx=Fitting.PAD_X, pady=(5,5))
        
        #contained objects
        #Instruction box
        frm_fileInstruction = ttk.Frame(self, relief = tk.GROOVE, borderwidth=1, width = Fitting.INSTRUCTION_WIDTH + 20, height = self.height - 24)
        frm_fileInstruction.grid_propagate(0)
        frm_fileInstruction.grid(row = 0, column = 0, sticky = 'n', pady= (10,10), padx = (10,5))
        
        lbl_fileInstruction = ttk.Label(frm_fileInstruction,wraplength=Fitting.INSTRUCTION_WIDTH,justify=tk.LEFT, textvariable = self.instructionText, font= Fitting.INSTRUCTION_FONT, foreground='red')
        lbl_fileInstruction.grid(pady= (10,10), padx = (10,10))
        
        #interactable box
        self.frm_interact = ttk.Frame(self, relief = tk.GROOVE, borderwidth = 1, width = self.width - Fitting.INSTRUCTION_WIDTH - 54, height = self.height - 24)
        self.frm_interact.grid_propagate(0)
        self.frm_interact.grid(row = 0, column = 1, pady= (10,10), padx = (5,10))
        

class DataImport(Interactible):
    def __init__(self, parent, controller):
        
        #object attributes
        self.width = controller.width
        self.height = 100
        
        Interactible.__init__(self, parent, controller, width = controller.width, height = self.height)
        self.instructionText.set('1. Import your data as a .csv file.')
        
        #populate generic widgets
        self.configure(width = self.width)
        self.configure(height = self.height)   
        self.populate(row = 1, column = 0)
        
        #unique widgets
        #filepath
        lbl_filePath = ttk.Label(self.frm_interact, text = 'File path:',justify=tk.LEFT)
        lbl_filePath.grid(row=0,column=0,padx=Fitting.PAD_X, pady=Fitting.PAD_Y)
        
        self.ent_filePath = ttk.Entry(self.frm_interact, width = 70)
        self.ent_filePath.grid(row=0,column=1, columnspan = 1,padx=Fitting.PAD_X, pady=Fitting.PAD_Y, sticky ='ew')
        
        #import button
        btn_import = ttk.Button(self.frm_interact, text = 'Browse Files', command = self.importData)
        btn_import.grid(row=1,column=2, sticky = 'ne',padx=Fitting.PAD_X)
        
        #datatype checkbox
        self.controller.radiobutton_variable = tk.IntVar()
        btn_freq = ttk.Radiobutton(self.frm_interact, text="Frequency",  variable = self.controller.radiobutton_variable, value = 1)
        btn_freq.grid(row = 0, column = 2,padx=Fitting.PAD_X)
        btn_spatial = ttk.Radiobutton(self.frm_interact, text="Spatial", variable = self.controller.radiobutton_variable, value = 2)
        btn_spatial.grid(row = 0, column = 3,padx=Fitting.PAD_X)
        
    def importData(self):
        #get image filepath
        filepath = tk.filedialog.askopenfilename(title='Import .csv data',filetypes=((".csv",".csv"),))
        
        if filepath != '':
            
            self.controller.dataLoaded = False
            self.controller.baselineSubtracted = False
            
            data_file = open(filepath,'r', newline="")
            datareader = csv.reader(data_file, delimiter=',')
            
            #file name
            file_name_temp = os.path.basename(filepath)
            self.controller.file_name = os.path.splitext(file_name_temp)[0]
            
            #import data
            XY = np.empty((0,4))
            #try:
            for row in datareader:
                XY = np.append(XY, np.array([[float(row[0]), float(row[1]), float(row[2]), float(row[3])]]), axis=0)
            
            columnIndex = 0
            sortedXY = XY[XY[:,columnIndex].argsort()]
            
            Yerr = sortedXY[:,3]
            Yerr[Yerr==0] = 0.0000000001
            sortedXY[:,3] = Yerr
            #update controller attributes
            self.controller.data = sortedXY
            
    
            #display figure
            
            sortedX = sortedXY[:,0]
            sortedXerr = sortedXY[:,1]
            sortedY= sortedXY[:,2]
            sortedYerr= sortedXY[:,3]
            
            f = mpl.Figure(figsize = Fitting.FIG_SIZE)
            a = f.add_subplot(111)
            a.scatter(sortedX, sortedY, s=6, marker='x')
            
            if self.controller.radiobutton_variable.get() == 1:
                a.set_xlabel('Frequency (GHz)')
            elif self.controller.radiobutton_variable.get() == 2:
                a.set_xlabel('Radius (mm)')
            else:
                self.controller.errorMessage['text'] = "Warning: Please select whether data is frequency or spatial."
                
            a.set_ylabel('Intensity (Arbitrary Units)')
            a.plot(sortedX, sortedY, color = 'black')
            a.errorbar(sortedX, sortedY, yerr = sortedYerr, ls = 'None', capsize = 1.5, color = '#880000')
            
            self.controller.displayFig(fig = f, figTitle = Fitting.FIG_TITLES[0], figDescription = self.controller.file_name)
            
            self.controller.errorMessage['text'] = ""
            self.controller.dataLoaded = True
                    
            #except ValueError:
            #    self.controller.errorMessage['text'] = "Error: Incorrect file format."
            #except IndexError:
            #    self.controller.errorMessage['text'] = "Error: Incorrect file format."
                
            data_file.close()
            
            #display image filepath
            self.ent_filePath.delete(0, tk.END) 
            self.ent_filePath.insert(0, str(filepath))
            
            
class BaselineFitting(Interactible):
    
    FUNCTION_SHAPES = {
        " y = a " : [1,['a']],
        " y = ax + b " : [2, ['a','b']],
        " y = ax² + bx + c " : [3,['a','b','c']]
        }
    
    def __init__(self, parent, controller):
        #object attributes
        self.width = controller.width
        self.height = 240
        
        Interactible.__init__(self, parent, controller, width = self.width, height = self.height)
        self.instructionText.set('2. Fit a baseline to the troughs of the data, and subtract that baseline in order for the data to sit on zero.')
        #populate generic widgets
        self.configure(width = self.width)
        self.configure(height = self.height)   
        self.populate(row = 2, column = 0)
        
        #unique widgets
        #drop down list of functional shapes
        lbl_function = ttk.Label(self.frm_interact, text = "Functional shape:", wraplength = 130)
        lbl_function.grid(row = 1, column = 0, padx = Fitting.PAD_X, pady = Fitting.PAD_Y, sticky = 'w')
        
        shapes = list(BaselineFitting.FUNCTION_SHAPES.keys())
        
        self.cmb_function = ttk.Combobox(self.frm_interact, state="readonly",values=shapes)
        self.cmb_function.grid(row = 1, column = 1, padx = Fitting.PAD_X, pady = Fitting.PAD_Y, sticky = 'ew')
        
        #maximum height of acceptable minima
        lbl_maxh = ttk.Label(self.frm_interact, text = "Maximum y-value of minima:", wraplength = 130)
        lbl_maxh.grid(row = 0, column = 0, padx = Fitting.PAD_X, pady = Fitting.PAD_Y, sticky = 'w')
        
        self.ent_maxh = ttk.Entry(self.frm_interact, width = 15)
        self.ent_maxh.grid(row = 0, column = 1, padx = Fitting.PAD_X, pady = Fitting.PAD_Y, sticky = 'w')
    
        #fit button
        btn_fit = ttk.Button(self.frm_interact, text = 'Fit', command = self.doFitting)
        btn_fit.grid(row=1,column=2,padx=Fitting.PAD_X, pady=Fitting.PAD_Y, sticky = 'w')
        
        #subtract button
        btn_sub = ttk.Button(self.frm_interact, text = 'Subtract', command = self.subtractBaseline)
        btn_sub.grid(row = 2, column = 2)  
        
        #undo button
        btn_reset = ttk.Button(self.frm_interact, text = 'Reset', command = self.resetBaseline, state = tk.DISABLED)
        btn_reset.grid(row = 3, column = 2)
           
        #output
        self.frm_output = ScrollableFrame(self.frm_interact, width =300, height = 70)
        self.frm_output.grid(row = 2, column = 0,rowspan = 2, columnspan = 2, padx = Fitting.PAD_X, pady = Fitting.PAD_Y)
        
        self.lbl_fittedBase = ttk.Label(self.frm_output.scrollable_frame, text = '')
        self.lbl_fittedBase.grid(row = 0, column = 0, padx=Fitting.PAD_X, pady=Fitting.PAD_Y)
           
        
    def doFitting(self):
        #get data
        Xdata = self.controller.data[:,0]
        Xerr = self.controller.data[:,1]    #neglected in this fitting
        Ydata = self.controller.data[:,2]
        Yerr = self.controller.data[:,3]
        
        if not(self.controller.baselineSubtracted):
            #set uncorrected data
            self.uncorrectedY = self.controller.data[:, 2]
        
        try:
            maxDepth = float(self.ent_maxh.get())
            
            function = self.cmb_function.get()
            
            fitOrder = BaselineFitting.FUNCTION_SHAPES.get(function)[0]
            params = BaselineFitting.FUNCTION_SHAPES.get(function)[1]
            
            #fit baseline
            baselineY, fitParams,fitErrs, peaks, rchisq = self.fitBaseline(Xdata, Ydata, Yerr, maxDepth, fitOrder)
            
            #output fitted params
            fittedOutput = ""
            for x in range(0,len(fitParams)):
                fittedOutput = fittedOutput + str(params[x]) + ': '+"{0:.3f}".format(-fitParams[x]) +' ± ' + "{0:.3f}".format(fitErrs[x]) +'\n'
            #fittedOutput = fittedOutput + "Reduced Chi-Sq of Fit: " + str(rchisq)
            
            self.lbl_fittedBase['text'] = fittedOutput
            
            self.correctedY = np.array([[]])
            for i in np.arange(len(Xdata)):
                self.correctedY = np.append(self.correctedY, Ydata[i] - baselineY[i])
                
            #output baseline and data
            f = mpl.Figure(figsize = Fitting.FIG_SIZE)
            a = f.add_subplot(111)
            a.plot(Xdata, Ydata, color = 'black')
            a.scatter(Xdata[peaks], Ydata[peaks], s = 50, color = 'red', marker = 'x')
            a.plot(Xdata, baselineY, color = 'blue')
            
            if self.controller.radiobutton_variable.get() == 1:
                a.set_xlabel('Frequency (GHz)')
            elif self.controller.radiobutton_variable.get() == 2:
                a.set_xlabel('Radius (mm)')
            a.set_ylabel('Intensity (Arbitrary Units)')
            self.controller.displayFig(fig = f, figTitle = Fitting.FIG_TITLES[1], figDescription = self.controller.file_name)
            
            self.controller.errorMessage['text'] = ""
            
        except ValueError:
            self.controller.errorMessage['text'] = "Error: Invalid value for maximum Y."
        except TypeError:
            self.controller.errorMessage['text'] = "Error: Select a baseline functional shape."
        except RuntimeError:
            self.controller.errorMessage['text'] = "Error: Baseline fitting unsuccessful."
            
        
    def subtractBaseline(self):
        #correct data by baseline
        self.controller.data[:, 2] = self.correctedY
        self.controller.baselineSubtracted = True
        
        #output subtracted baseline
        f = mpl.Figure(figsize = Fitting.FIG_SIZE)
        a = f.add_subplot(111)
        a.plot(self.controller.data[:,0], self.controller.data[:,2], color = 'black')
        a.scatter(self.controller.data[:,0], self.controller.data[:,2], s = 10, color = 'red', marker = 'x')
        self.controller.displayFig(fig = f, figTitle = Fitting.FIG_TITLES[2], figDescription = self.controller.file_name)
        
    def resetBaseline(self):
        self.controller.data[:, 2] = self.uncorrectedY
        
        if  Fitting.FIG_TITLES[1] in self.controller.windows:
            start = np.where(Fitting.FIG_TITLES== Fitting.FIG_TITLES[1])[0][0]
            for x in range(start, len(Fitting.FIG_TITLES)):
                if Fitting.FIG_TITLES[x] in self.controller.windows:
                    self.controller.windows[Fitting.FIG_TITLES[x]].destroy()
        
        return 
        
    def Polynomial(self, x, *params):
        y = np.polyval(params, x)
        return y

    def fitBaseline(self, Xdata, Ydata, Yerr, maxDepth, polyOrder):
        #flip data in Y so find_peaks may be used to find the base
        flippedY = -Ydata
        
        #find base points
        minHeight = -maxDepth
        peaks,heights = scp.find_peaks(flippedY, height = minHeight, prominence = 0.8)
        
        #select just the base points
        basePoints = np.array([Xdata[peaks],flippedY[peaks]])
        baseErrs =  np.array(Yerr[peaks])
        
        #fit the base points as a polynomial
        n = polyOrder
        p0 = np.ones(n)
        
        try:
            popt, pcov = curve_fit(self.Polynomial, basePoints[0,:], basePoints[1,:], p0=p0)
        
            perr = np.sqrt(np.diag(pcov))
            baselineY = self.Polynomial(Xdata, *popt)
            
            #calculate chi square
            chi_square = sum(((-flippedY[peaks]) - baselineY[peaks])**2/baseErrs**2)
            dof = len(peaks) - n
            reduced_chi_square = chi_square / dof
        
        except:
            raise RuntimeError
        
        #return fitted baselines and errors (diagonals of covariances)
        return -baselineY, popt, perr, peaks, reduced_chi_square
    
class GaussianFitting(Interactible):
    def __init__(self,parent,controller):
        
        #object attributes
        self.width = controller.width
        self.height = 350
        self.numberOfFitEntries = 1 #how many gaussians to fit
        #self.gaussGuesses: height,centre,sd of intial gauss guesses
        #self.gaussBounds: bounds for fitting
        #self.ROI_data
        
        
        Interactible.__init__(self, parent, controller, width = self.width, height = self.height)
        
        self.instructionText.set('3. Select a region-of-interest (ROI) and input the estimated parameters of the Gaussians you wish to fit.')
        #populate generic widgets
        self.configure(width = self.width)
        self.configure(height = self.height)   
        self.populate(row = 3, column = 0)
        
        #unique widgets
        
        self.iniGuesses = InitialGuesses(self.frm_interact, self, self.frm_interact['width']/2, self.frm_interact["height"]-20)
        self.iniGuesses.grid(row = 0, column = 0,padx=Fitting.PAD_X, pady=Fitting.PAD_Y, sticky = 'n')
        
        self.fitParams = FittedParams(self.frm_interact, self, self.frm_interact['width']/2 - 32, self.frm_interact["height"]-20)
        self.fitParams.grid(row = 0, column = 1,padx=(0,10), pady=Fitting.PAD_Y, sticky = 'n')     
        
    def saveFitData(self):
        #crop to ROI and get initial param guesses
        inputsValid = True
        
        X = self.controller.data[:,0]
        Xerr =self.controller.data[:,1]
        Y =self.controller.data[:,2]
        Yerr = self.controller.data[:,3]
        
        #crop to ROI
        if len(self.iniGuesses.ent_x1.get()) == 0 and len(self.iniGuesses.ent_x2.get()) ==0:
            ROI_X = X
            ROI_Y = Y
            ROI_Xerr = Xerr
            ROI_Yerr = Yerr
            
            self.ROI_data = np.column_stack((np.column_stack((ROI_X, ROI_Xerr)), np.column_stack((ROI_Y, ROI_Yerr))))
        else:
            try:
                ROI_lower = float(self.iniGuesses.ent_x1.get())
                ROI_upper = float(self.iniGuesses.ent_x2.get())
                
                ROI_X = np.array([])
                ROI_Y = np.array([])
                ROI_Xerr = np.array([])
                ROI_Yerr = np.array([])
                
                for i in range(len(X)):
                    if X[i] > ROI_lower and X[i] < ROI_upper:
                        ROI_X = np.append(ROI_X,X[i])
                        ROI_Y = np.append(ROI_Y,Y[i])
                        ROI_Xerr = np.append(ROI_Xerr,Xerr[i])
                        ROI_Yerr = np.append(ROI_Yerr,Yerr[i])
                
                self.ROI_data = np.column_stack((np.column_stack((ROI_X, ROI_Xerr)), np.column_stack((ROI_Y, ROI_Yerr))))
                
                self.controller.errorMessage['text'] = ""
            except ValueError:
                self.controller.errorMessage['text'] = "Error: Input valid values."
                inputsValid = False
        
        if inputsValid:
            #get params for guesses and test for empty ones
            try:
                self.gaussGuesses = np.array([])
                for iy in np.ndindex(self.iniGuesses.guesses.shape[0]):
                    guessEntries = self.iniGuesses.guesses[iy]
                    centre = guessEntries[0].get()
                    height = guessEntries[1].get()
                    fwhm = guessEntries[2].get()
                    if not((len(centre) == 0) or (len(height) ==0) or (len(fwhm)==0)):
                        sd = float(fwhm) * (1/(2*np.sqrt(2*np.log(2))))
                        self.gaussGuesses = np.append(self.gaussGuesses, [float(height), float(centre), sd])
                        
                self.controller.errorMessage['text'] = ""
            except ValueError:
                self.controller.errorMessage['text'] = "Error: Input valid values."
                inputsValid = False
        
        return inputsValid

class InitialGuesses(ttk.Frame):
    def __init__(self, parent, controller, width, height):
        ttk.Frame.__init__(self, parent, width = width, height = height, relief='groove', borderwidth = 3)  
        
        #object attributes
        self.controller = controller
        #self.columnconfigure(index = [0,1,2,3,4], weight = 1)
        self.grid_propagate(0)
        
        #region of interest
        lbl_ROI = ttk.Label(self, text = "ROI:")
        lbl_ROI.grid(row=0,column=0, pady=(15,15), padx = (10,10), sticky = 'nw')
        
        lbl_x1 = ttk.Label(self, text = "x₁")
        lbl_x1.grid(row=0,column = 1, sticky = 'sw', pady = (20,0))
        self.ent_x1 = ttk.Entry(self, width = 10)
        self.ent_x1.grid(row=0,column = 1, sticky = 'nw', pady=(15,15))
        
        lbl_x2 = ttk.Label(self, text = "x₂")
        lbl_x2.grid(row=0,column = 2, sticky = 'sw', pady = (20 ,0))
        self.ent_x2 = ttk.Entry(self, width = 10)
        self.ent_x2.grid(row=0,column = 2, sticky = 'nw', pady=(15,15))
        
        #bounds settings
        btn_settings = ttk.Button(self, text = 'Advanced Settings', command = self.openSettings)
        btn_settings.grid(row = 2, column = 3, sticky = 'e') 
        
        btn_display = ttk.Button(self, text = 'Display', command = self.displayGuesses)
        btn_display.grid(row = 3, column = 3, sticky = 'e')
        
        #scrollable frame
        self.frm_guesses = ScrollableFrame(self, width = 300, height = 150)
        self.frm_guesses.grid(row = 1, column = 0, columnspan = 4, sticky = 'w', padx = Fitting.PAD_X, pady = Fitting.PAD_Y)
        
        #labels
        lbl_centre = ttk.Label(self.frm_guesses.scrollable_frame, text = "Centre:")
        lbl_centre.grid(row = 0, column = 1, padx=(5,5), pady=Fitting.PAD_Y)
        
        lbl_height = ttk.Label(self.frm_guesses.scrollable_frame, text = "Height:")
        lbl_height.grid(row = 0, column = 2, padx=(5,5), pady=Fitting.PAD_Y)
        
        lbl_fwhm = ttk.Label(self.frm_guesses.scrollable_frame, text = "FWHM:")
        lbl_fwhm.grid(row=0, column = 3, padx=(5,5), pady=Fitting.PAD_Y)
        
        #add button
        self.btn_add = ttk.Button(self.frm_guesses.scrollable_frame, text="Add", command = self.add_new_data)
        
        #guesses
        self.guesses = np.empty((0,3))
        self.guesses = np.append(self.guesses, [[ttk.Entry(self.frm_guesses.scrollable_frame, width = 5), ttk.Entry(self.frm_guesses.scrollable_frame, width = 5), ttk.Entry(self.frm_guesses.scrollable_frame, width = 5)]], axis = 0)
        
        for iy, ix in np.ndindex(self.guesses.shape):
            #ttk.Label(frm_interact, text = str(ix) + str(iy)).grid(row = iy+1, column = ix+1)
            ttk.Label(self.frm_guesses.scrollable_frame, text = 'Fit {0}:'.format(self.controller.numberOfFitEntries)).grid(row = iy+1, column = 0, sticky = 'e')
            current_line = self.guesses[iy, ix]
            current_line.grid(row = iy+1, column = ix+1, padx = (5,5), pady = (5,5))
            self.btn_add.grid(row = iy+1, column = 5)
    
    def openSettings(self):
        settings = FitSettings(self.controller, 300, 700)        
    
    def add_new_data(self):
        self.guesses = np.append(self.guesses, [[ttk.Entry(self.frm_guesses.scrollable_frame, width = 5), ttk.Entry(self.frm_guesses.scrollable_frame, width = 5), ttk.Entry(self.frm_guesses.scrollable_frame, width = 5)]], axis=0)
        
        self.controller.numberOfFitEntries = self.controller.numberOfFitEntries + 1
        
        self.btn_add.grid_forget()
        self.btn_add.grid(row = self.guesses.shape[0]+1, column = 5)
        
        for x in range(self.guesses.shape[1]):
            ttk.Label(self.frm_guesses.scrollable_frame, text ='Fit {0}:'.format(self.controller.numberOfFitEntries)).grid(row =self.guesses.shape[0]+1, column = 0, sticky = 'e')
            self.guesses[self.guesses.shape[0]-1, x].grid(row = self.guesses.shape[0]+1,column = x+1, padx = (5,5), pady = (5,5))
        
    def displayGuesses(self):
        if self.controller.saveFitData():
            
            ROI_X = self.controller.ROI_data[:,0]
            ROI_Xerr =self.controller.ROI_data[:,1]
            ROI_Y =self.controller.ROI_data[:,2]
            ROI_Yerr = self.controller.ROI_data[:,3]
            
            #display guesses
            f = mpl.Figure(figsize = Fitting.FIG_SIZE)
            a = f.add_subplot(111)
            #line of data
            a.plot(ROI_X, ROI_Y, color = 'black')
            #datapoint errors
            a.errorbar(ROI_X, ROI_Y, yerr = ROI_Yerr, ls = 'None', capsize = 1.5, color = '#880000')
            #data as points
            a.scatter(ROI_X, ROI_Y, s = 10, color = 'red', marker = 'x')
            
            if self.controller.controller.radiobutton_variable.get() == 1:
                a.set_xlabel('Frequency (GHz)')
            elif self.controller.controller.radiobutton_variable.get() == 2:
                a.set_xlabel('Radius (mm)')
            a.set_ylabel('Intensity (Arbitrary Units)')
            
            for x in range(0, len(self.controller.gaussGuesses), 3):
                height = self.controller.gaussGuesses[x]
                centre = self.controller.gaussGuesses[x+1]
                sd = self.controller.gaussGuesses[x+2]
                a.plot(ROI_X, Gauss(ROI_X, height,centre,sd), color = Fitting.COLORS[x%len(Fitting.COLORS)])
            
            self.controller.controller.displayFig(fig = f, figTitle = Fitting.FIG_TITLES[3], figDescription = self.controller.controller.file_name)

class FitSettings(tk.Toplevel):
    def __init__(self, controller, height, width):
        super().__init__(width=width, height=height)
        self.title("Advanced Settings")
        self.resizable(0, 0)
        self.focus()
        self.grab_set()
        
        #object attributes
        self.controller = controller
        self.width = width
        self.height = height
        self.container = Interactible(self, self, height, width)
        self.container.populate(0, 0)
        
        self.container.instructionText.set("Set the bounds for each fit parameter. This dictates the maximum and minimum values these parameters may take.")
        self.frame = ScrollableFrame(self.container.frm_interact, width = 400, height = 240)
        self.frame.grid(padx = Fitting.PAD_X, pady = Fitting.PAD_Y)
        
        #contained objects
        #labels
        lbl_centre = ttk.Label(self.frame.scrollable_frame, text = "Centre:")
        lbl_centre.grid(row = 0, column = 1)
        frm_boundlabelsc = ttk.Frame(self.frame.scrollable_frame)
        frm_boundlabelsc.grid(row = 1, column = 1)
        ttk.Label(frm_boundlabelsc, text = "Lower").grid(row=0,column = 0)
        ttk.Label(frm_boundlabelsc, text = "Upper").grid(row=0,column = 1)
        
        lbl_height = ttk.Label(self.frame.scrollable_frame, text = "Height:")
        lbl_height.grid(row = 0, column = 2)
        frm_boundlabelsh = ttk.Frame(self.frame.scrollable_frame)
        frm_boundlabelsh.grid(row = 1, column = 2)
        ttk.Label(frm_boundlabelsh, text = "Lower").grid(row=0,column = 0)
        ttk.Label(frm_boundlabelsh, text = "Upper").grid(row=0,column = 1)
        
        lbl_fwhm = ttk.Label(self.frame.scrollable_frame, text = "FWHM:")
        lbl_fwhm.grid(row=0, column = 3)
        frm_boundlabelsf = ttk.Frame(self.frame.scrollable_frame)
        frm_boundlabelsf.grid(row = 1, column = 3)
        ttk.Label(frm_boundlabelsf, text = "Lower").grid(row=0,column = 0)
        ttk.Label(frm_boundlabelsf, text = "Upper").grid(row=0,column = 1)
        
        #bounds
        self.bounds = np.empty((self.controller.numberOfFitEntries,3), dtype = BoundPair)
        for y in range(self.controller.numberOfFitEntries):
            for x in range(3):
                ttk.Label(self.frame.scrollable_frame, text = 'Fit {0}:'.format(y+1)).grid(row = y+2, column = 0, sticky = 'e')
                pair = BoundPair(self.frame.scrollable_frame)
                self.bounds[y,x] = pair
                self.bounds[y,x].grid(row = y+2, column = x+1, padx = (5,5), pady = (5,5))
        
        #save button
        btn_save = ttk.Button(self.frame.scrollable_frame, text = 'Save', command = self.saveBounds, width = 7)
        btn_save.grid(row=y+2, column =4, padx = (10,5))
        
        #populate bounds
        for y in range(self.controller.numberOfFitEntries):
            for x in range(3):
                pair = self.bounds[y,x]
                pair.lower.delete(0, tk.END) 
                pair.lower.insert(0, "-inf")
                pair.upper.delete(0, tk.END) 
                pair.upper.insert(0, "inf")
        if (hasattr(self.controller, "gaussBounds")):
            for i in range(0, len(self.controller.gaussBounds[0])):
                #i // 3 is y
                #i % 3 is x
                pair =self.bounds[i//3,i%3] 
                pair.lower.delete(0, tk.END) 
                pair.lower.insert(0, str(self.controller.gaussBounds[0][i]))
                pair.upper.delete(0, tk.END) 
                pair.upper.insert(0, str(self.controller.gaussBounds[1][i]))
            
        
    def saveBounds(self):
        #default bounds are -np.inf -> np.inf
        
        shape = self.bounds.shape
        
        boundsUpper = ()
        boundsLower = ()
        for y in range(self.bounds.shape[0]):
            for x in range(self.bounds.shape[1]):
                currentPair = self.bounds[y,x]
                boundsLower = boundsLower + (float(currentPair.lower.get()),)
                boundsUpper = boundsUpper + (float(currentPair.upper.get()),)
        
        self.controller.gaussBounds = (boundsLower, boundsUpper)            
        
class FittedParams(ttk.Frame):
    def __init__(self, parent, controller, width, height):
        ttk.Frame.__init__(self, parent, width = width, height = height, relief='groove', borderwidth = 3)  
        
        #object attributes
        self.controller = controller
        self.grid_propagate(0)
        
        self.heights = np.array([])
        self.heights_err = np.array([])
        self.centres = np.array([])
        self.centres_err = np.array([])
        self.fwhms = np.array([])
        self.fwhms_err = np.array([])
        
        #contained objects
        btn_fit = ttk.Button(self, text = 'Fit', command = self.doFitting)
        btn_fit.grid(row= 0, column = 0, padx = Fitting.PAD_X, pady = Fitting.PAD_Y, sticky = 'w')
        
        #frame output
        
        self.frm_output = ScrollableFrame(self, width = 300, height = 200)
        self.frm_output.grid(row = 1, column = 0,padx = Fitting.PAD_X, pady = Fitting.PAD_Y)
        
        self.lbl_fittedBase = ttk.Label(self.frm_output.scrollable_frame, text = '')
        self.lbl_fittedBase.grid(row = 0, column = 0, padx=Fitting.PAD_X, pady=Fitting.PAD_Y)
        
        btn_saveFile = ttk.Button(master = self, text = 'Save Fits as .csv', command = lambda: self.saveCsvFile(self.heights, self.heights_err, self.centres, self.centres_err, self.fwhms, self.fwhms_err))
        btn_saveFile.grid(row =0, column = 0,padx=Fitting.PAD_X, pady=Fitting.PAD_Y)
        
         
    def doFitting(self):
        self.controller.controller.gaussiansFitted = False
        
        self.heights = np.array([])
        self.heights_err = np.array([])
        self.centres = np.array([])
        self.centres_err = np.array([])
        self.fwhms = np.array([])
        self.fwhms_err = np.array([])
        
        if self.controller.saveFitData():
            
            ROI_X = self.controller.ROI_data[:,0].astype(float)
            ROI_Xerr =self.controller.ROI_data[:,1].astype(float)
            ROI_Y =self.controller.ROI_data[:,2].astype(float)
            ROI_Yerr = self.controller.ROI_data[:,3].astype(float)
            
            #import guesses and bounds
            guesses = self.controller.gaussGuesses
            try:
                mybounds = (self.controller.gaussBounds[0][0:len(guesses)], self.controller.gaussBounds[1][0:len(guesses)])
            except AttributeError:
                lower = (-np.inf,)*len(guesses)
                upper = (np.inf,)*len(guesses)
                mybounds = (lower,upper)
            
            try:
                #do fitting
                popt,pcov = curve_fit(Multi_Gauss,ROI_X,ROI_Y,p0=guesses,bounds=mybounds, sigma =ROI_Yerr, absolute_sigma=True)
                try:
                    perr = np.sqrt(np.diag(pcov))
                except:
                    perr = np.diag(pcov)
                    
                fittedGaussians = Multi_Gauss(ROI_X,*popt)
                
                #output baseline and data
                f = mpl.Figure(figsize = Fitting.FIG_SIZE)
                axes = f.add_subplot(111)
                axes.scatter(ROI_X, ROI_Y, s=6, marker='x')
                
                if self.controller.controller.radiobutton_variable.get() == 1:
                    axes.set_xlabel('Frequency (GHz)')
                elif self.controller.controller.radiobutton_variable.get() == 2:
                    axes.set_xlabel('Radius (mm)')
                axes.set_ylabel('Intensity (Arbitrary Units)')
                output = ""
                
                for i in range(0, len(popt), 3):
                    
                    a = popt[i]
                    b = popt[i+1]
                    c = popt[i+2]
                    aerr = perr[i]
                    berr = perr[i+1]
                    cerr = perr[i+2]
                    
                    self.heights = np.append(self.heights, a)
                    self.heights_err = np.append(self.heights_err, aerr)
                    self.centres = np.append(self.centres, b)
                    self.centres_err = np.append(self.centres_err, berr)
                    
                    axes.plot(ROI_X, Gauss(ROI_X,a,b,c), color=Fitting.COLORS[i%len(Fitting.COLORS)])
                    axes.fill_between(ROI_X, Gauss(ROI_X,a,b,c), facecolor=Fitting.COLORS[i%len(Fitting.COLORS)], alpha=0.5)  
                    
                    fwhm = 2*np.sqrt(2*np.log(2)) * c
                    fwhmerr = 2*np.sqrt(2*np.log(2)) * cerr
                    
                    self.fwhms = np.append(self.fwhms, fwhm)
                    self.fwhms_err = np.append(self.fwhms_err, fwhmerr)
                    
                    output = output + '---------------- Fit Number ' + str((i//3)+1) + ' ----------------\n'
                    output = output +'Height: '+"{0:.3g}".format(a) +' +/- ' + "{0:.3g}".format(aerr)+'\n'
                    output = output +'Centre: '+"{0:.9g}".format(b) +' +/- ' + "{0:.3g}".format(berr)+'\n'
                    output = output + 'FWHM: '+"{0:.3}".format(fwhm) +' +/- ' + "{0:.3g}".format(fwhmerr)+'\n'+'\n'
        
                axes.plot(ROI_X, fittedGaussians, color='r', linestyle='--')
                
                self.controller.controller.displayFig(fig = f, figTitle = Fitting.FIG_TITLES[4], figDescription = self.controller.controller.file_name)
                self.lbl_fittedBase['text'] = output
                self.controller.controller.errorMessage['text'] = ""
                
                self.controller.controller.gaussiansFitted = True
                    
            except RuntimeError:
                self.controller.controller.errorMessage['text'] = "Error: Gaussian fitting unsuccessful."
            except OptimizeWarning:
                self.controller.controller.errorMessage['text'] = "Warning: Could not estimate covariance of the parameters."
           # except RuntimeWarning:
            #    self.controller.controller.errorMessage['text'] = "Warning: Divide by zero encountered."
    
    def saveCsvFile(self, Heights, HeightsErrs, Centres, CentresErrs, FWHMs, FWHMsErrs):
        #save a text file of results and csv file
        if self.controller.controller.gaussiansFitted:
            self.controller.controller.errorMessage['text'] = ""
            
            filepath = tk.filedialog.asksaveasfilename(defaultextension='.csv', filetypes = (('.csv','*.csv'),))
            file = open(filepath,'w', newline = '')
            datawriter = csv.writer(file, delimiter=',')
            for i in range(len(Heights)):
                datawriter.writerow([Heights[i], HeightsErrs[i], Centres[i], CentresErrs[i], FWHMs[i], FWHMsErrs[i]])
               
            file.close()
        else:
            self.controller.controller.errorMessage['text'] = "Error: No fit values generated."
        
class BoundPair(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.lower = ttk.Entry(self, width = 5)
        self.lower.grid(row=0,column = 0, sticky = 'nw', pady = (5,5))
        
        self.upper = ttk.Entry(self, width = 5)
        self.upper.grid(row=0,column = 1, sticky = 'nw', pady = (5,5))
        

def Gauss(x, height, centre, sd):
    temp = (height * np.exp(-((x - centre)**2 / (2 * sd**2))))
    return temp

def Multi_Gauss(x, *params):
    y = np.zeros_like(x)
    for i in range(0, len(params), 3):
        a = params[i]
        b = params[i+1]
        c = params[i+2]
        for p in range(len(x)):
            pos = x[p]
            #g = Gauss(pos,a,b,c)
            y[p] += Gauss(pos,a,b,c)
    return y

class ScrollableFrame(ttk.Frame):
    def __init__(self, container, width, height):
        super().__init__(container, relief = 'groove')
        canvas = tk.Canvas(self, width = width, height = height)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx = (5,5), pady = (5,5))
        scrollbar.pack(side="right", fill="y", padx = (5,5), pady = (5,5))


if __name__ == "__main__":
    app = Fitting()
    app.mainloop()
