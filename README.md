# Mercury-hyperfine-splitting-experimental-analysis
A series of programs and examples that are used to determine the hyperfine frequency shifts in naturally occurring mercury as a part of a second year lab experiment at the University of Manchester.

All examples and code are provided as-is, but you are welcome to contact the authors for further information upon reasonable request. Some documents are password-protected - please contact the authors directly for the password. This is to avoid students, who may be studying this lab, having direct access to materials such as demonstrators notes. 

The authors can be contacted on the following emails:

Professor Andrew Murray: andrew.murray@manchester.ac.uk

Rosie Barnes: rosie.barnes@manchester.ac.uk

Edward Wilson: edward.edwardwilson@gmail.com

## What is included on this repository?

### Demonstrator_notes_for_Hg_green_line_expt.pdf
This document contains lots of information for demonstrators of the experiment, including worked examples for calculating the hyperfine energy shifts from known values and for calculating the a and b coefficients from experimental data. Details are also given on the function of the camera used in our experimental setups at the University of Manchester teaching laboratory. This document is password-protected. Please get in contact with the authors to request the password.

### Example_Data_for_fitting.pdf
This file is a TAB deliminated set of example data which has been taken from the experiment and manipulated to show intensity against radial position across the detector. Intensities are normalised to 1000 and given for radius = -12.000 -> +12.000mm. This data is given to allow the analysis portion of the experiment to be performed without needing to carry out the experimental data collection. Gaussian fitting may be performed on radius^2 data as described in the paper. Further information on this data is given in the header of the file. This document is password-protected. Please get in contact with the authors to request the password.

To extract the data from the pdf file, you should be able to copy it in the usual way and then paste it into a text file for plotting and fitting. Alternatively some pdf readers allow the file to be extracted as a text 
file, word file or RTF file. To be compatible with the Gaussian Fitting v1.2 program, additional columns must be inserted for the missing errors. These columns can be padded with 0s. The format of the columns should be as follows:
    
    Radius  Radius_Err  Intensity  Intensity_Err

### Peak_identification_from_Maple.pdf
This document shows models of the green line hyperfine fringes under varying experimental conditions.

The modelled etalon reflectance is varied from 0.93 (as in our experimental set-up) to 0.99. Increasing the reflectance increases the etalon finesse and thus sharpens the produced fringes by reducing the etalon-associated full-width-at-half-maximum. The length of the air gap in the etalon, t, is kept constant throughout the models ( = 4mm) and thus the FSR of the modelled etalons is consistently 37.5GHz, as in our set-up. This means that the fringe orders are equally spaced by 37.5GHz. 

The Doppler width, which is associated with the temperature in the lamp, is varied from 600 -> 100MHz. The top model, with high reflectance and low Doppler width, clearly shows almost every transition individually. The transitions are thus identified by comparison with <sup>198</sup>Hg and labelled. The labels correspond with those given in Figure 2 in the paper. The final figure in the document shows real experimental data, scaled to align with the models. 

The models were produced by Professor Andrew Murray at the University of Manchester.

### Hg_Green_Line_Image_Analysis_v1.1.py
This file contains the code for the Image Analysis program created for use in this teaching lab. The program is in Python and runs a GUI, as described in the paper. The program allows students to import .TIFF images of circular fringes, find the centre of the pattern by interacting with a simple algorithm, and calculate intensity vs radius and intensity vs relative frequency datasets, which may then be exported as .csv files and analysed in Hg_Green_Line_Gaussian_Fitting_v1.2.py.

### Hg_Green_Line_Gaussian_Fitting_v1.2.py
This file contains the code for the Gaussian Fitting program created for use in this teaching lab. The program is in Python and runs a GUI. The program allows students to import relative frequency, radius squared, or radius data, fit and subtract a polynomial baseline, and then fit multiple Gaussians to their data to extract the hyperfine shifts. The fit parameters can be exported and saved as a .csv file.
