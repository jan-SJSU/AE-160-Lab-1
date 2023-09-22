import math
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.signal import savgol_filter as sf

# Create global variables
global psf2pa
psf2pa = 0.020885 # Conversion factor for psf --> Pa

# ------------------------------------------------------------------------------
# ---------------------------- Classes & Functions -----------------------------
# ------------------------------------------------------------------------------

# Create object in order to call specific property of data rather than use messy
# and confusing list formatting
class Data:
    def __init__(self, alphaVel, normalForce, axialForce, pitchingMoment,
                 coefficientLift, coefficientDrag):
        self.X = alphaVel # Either AoA or v_inf
        self.NF = normalForce
        self.AF = axialForce
        self.PM = pitchingMoment
        self.CL = coefficientLift
        self.CD = coefficientDrag

def read_files(files: list[str]):
    '''This function reads .csv a list of files and turns it into a list of 
    pandas dataframes'''
    
    n = len(files)
    new_files = [0]*n
    rows = [0,1,2,3,4,5,6,8] # Skips these rows when reading csv files

    # Iterate through list of strings to read .csv files
    for i in range(0,n):
        new_files[i] = pd.read_csv(files[i], skiprows=rows)

    return new_files

def q2v(q: list):
    '''This function uses the ideal gas law and the dynamic pressure equation
    in order to convert dynamic pressure into wind velocity'''
    T = 296.15        # K (Found from National Weather Service website)
    p = 100914        # Pa (Also found from NWS site)
    R = 287           # J*kg^-1*K^-1 (Specific gas constant for air)
    
    vel = [0]*len(q)
    for i in range(0,len(q)):
        # use absolute value of q so as not to get a domain error w/ sqrt
        vel[i] = math.sqrt((2*abs(q[i]/psf2pa)*R*T)/p)
    
    return vel

def force2coeff(force: list, q: list):
    '''This function converts force into coefficients (i.e, lift force --> 
    coefficient of lift)'''
    n = len(force)
    S = 0.01 # m (Length of object)
    
    coefficient = [0]*n # Initialize list

    # Iterate through force & q in order to find coefficients.
    for i in range(0,n):
        if q[i] == 0: # Skips when q = 0, so as not to divide by 0.
            coefficient[i] = None
        else:
            coefficient[i] = force[i]/(q[i]*S)
        
    return coefficient

def NA2LD(N:list, A:list, alphaDeg: list):
    '''This function takes normal/axial force and angle of attack and converts
    it into lift/drag force'''
    
    n = len(N)

    # Initialize lists
    liftForce = [0]*n
    dragForce = liftForce
    alphaRad = liftForce

    # Iterate through list to convert to lift force for corresponding
    # normal/axial forces + AoA.
    for i in range(0,n):
        alphaRad[i] = math.radians(alphaDeg[i]) # Convert AoA into radians
        liftForce[i] = N[i]*math.cos(alphaRad[i]) - A[i]*math.sin(alphaRad[i])
        dragForce[i] = N[i]*math.sin(alphaRad[i]) + A[i]*math.cos(alphaRad[i])

    return liftForce, dragForce

def momentTransfer(moment, normal, b):
    A = 28.829/1000 # m
    D = 71.04/1000 # m
    n = len(moment)
    C = D-(b/1000)    

    new_moment = [0]*n
    
    for i in range(0,n):
        new_moment[i] = moment[i] - (A + C)*normal[i]
        
    return new_moment

def datasplit(data: list):
    '''This function splits dataframe into: Alpha/Velocity, Normal Force,
    Axial Force, and Pitching Moment. Also converts forces into metric.'''
    
    diameters = [
        74.82, # Flat Plate
        74.82, # Flat Plate
        75.48, # Half Sphere
        75.40, # Inverted Cup
        76.21  # Sphere
    ]

    B = [
        98.42,  # Flat Plate
        98.42,  # Flat Plate
        99.27,  # Half Sphere
        127.00, # Inverted Cup
        146.92, # Sphere
    ]

    lbf2N = 4.44822         # Conversion for lbf to N
    inlbs2Nm = 0.1129848333 # Conversion for in*lbf to N*m
    n = len(data)

    # Find lifting force and drag force based on AoA and normal/axial forces.
    # Only for flat plate angle
    lF, dF = NA2LD(data[0]['NF/SF']*lbf2N, data[0]['AF/AF2']*lbf2N,
                   data[0]['Alpha'])
    
    # Separate Flat Plate Angle from other data, since x axis will be AoA
    # rather than wind velocity.
    
    list = [0]*n
    list[0] = Data(
        data[0]['Alpha'],
        data[0]['NF/SF']*lbf2N,
        data[0]['AF/AF2']*lbf2N,
        data[0]['PM/YM']*inlbs2Nm,
        force2coeff(lF, data[0]['q']/psf2pa),
        force2coeff(dF, data[0]['q']/psf2pa)
    )
    
    list[0].PM = momentTransfer(list[0].PM, list[0].NF, B[0])
    
    # Iterate through data to split for each shape and assign different types of
    # data to object properties.
    for i in range(1,n):
        list[i] = Data( # Assume NF/AF == LF/DF since AoA = 0
            q2v(data[i]['q']),         # convert 'q' column into v_inf
            data[i]['NF/SF']*lbf2N,    # Normal Force
            data[i]['AF/AF2']*lbf2N,   # Axial Force
            data[i]['PM/YM']*inlbs2Nm, # Pitching Moment
            force2coeff(data[i]['NF/SF']*lbf2N, data[i]['q']/psf2pa),
            force2coeff(data[i]['AF/AF2']*lbf2N, data[i]['q']/psf2pa)
        )   
        list[i].PM = momentTransfer(list[i].PM, list[i].NF, B[i])

    return list

# ------------------------------------------------------------------------------
# ---------------------------------Main Program---------------------------------
# ------------------------------------------------------------------------------

# Read Files
path = str(Path(__file__).parent)+'/Data' # Finds current path and Data folder
files = [
    path+'/Flat Plate Angle.csv',
    path+'/Flat Plate Velocity.csv',
    path+'/Half Sphere.csv',
    path+'/Inverted Cup.csv',
    path+'/Sphere.csv'
]

data = read_files(files)

flatPlateAng, flatPlateVel, halfSphere, invertedCup, sphere = datasplit(data)

# Set up window
fig1, ax1 = plt.subplots() # Normal Force v Velocity
fig2, ax2 = plt.subplots() # Axial Force v Velocity
fig3, [ax3, ax3_2] = plt.subplots(2) # Normal/Axial Force v Angle of Attack
fig4, [ax4, ax4_2] = plt.subplots(2) # Coefficient of Lift/Drag
fig5, ax5 = plt.subplots() # Pitching Moment v Velocity


# Savitsky-Golay filter coefficients
wl = 151 # Window Length
po = 2   # Polynomial Order

# Normal Force v Velocity
ax1.set_xlabel('V_inf [m/s]')
ax1.set_ylabel('Normal Force [N]')
ax1.plot(
    sf(flatPlateVel.X, wl, po),
    flatPlateVel.NF,
    'r-',
    label='Flat Plate',
    zorder=10
)
ax1.plot(
    sf(halfSphere.X, wl, po),    
    halfSphere.NF,
    'b-',
    label='Half Sphere',
    zorder=15 
)
ax1.plot(
    sf(invertedCup.X, wl, po),
    invertedCup.NF,
    'k-',
    label='Inverted Cup',
    zorder=5
)
ax1.plot(
    sf(sphere.X, wl, po),
    sphere.NF,
    'g-',
    label='Sphere',
    zorder=0
)

# Axial Force v Velocity
ax2.set_xlabel('V_inf [m/s]')
ax2.set_ylabel('Axial Force [N]')
ax2.plot(
    sf(flatPlateVel.X, wl, po),
    sf(flatPlateVel.AF, wl, po),
    'r-',
    label='Flat Plate',
    zorder=5
)
ax2.plot(
    sf(halfSphere.X, wl, po),
    sf(halfSphere.AF, wl, po),
    'b-',
    label='Half Sphere',
    zorder=10
)
ax2.plot(
    sf(invertedCup.X, wl, po),
    sf(invertedCup.AF, wl, po),
    'k-',
    label='Inverted Cup',
    zorder=15
)
ax2.plot(
    sf(sphere.X, wl, po),
    sf(sphere.AF, wl, po),
    'g-',
    label='Sphere',
    zorder=0
)

# Normal/Axial Force v Angle of Attack
ax3.set_xlabel('Alpha [deg]')
ax3.set_ylabel('Normal Force [N]')
ax3.plot(
    flatPlateAng.X,
    flatPlateAng.NF,
    'r-',
    label='Normal Force'
)
ax3_2.set_xlabel('Alpha [deg]')
ax3_2.set_ylabel('Axial Force [N]')
ax3_2.plot(
    flatPlateAng.X,
    flatPlateAng.AF,
    'b-',
    label='Axial Force'
)

ax4.set_xlabel('Alpha [deg]')
ax4.set_ylabel('Lift Coefficient')
ax4.plot(
    sf(flatPlateAng.X, wl, po),
    sf(flatPlateAng.CL, wl, 1),
    'r-',
    label='Coefficient of Lift'
)
ax4_2.set_xlabel('Alpha [deg]')
ax4_2.set_ylabel('Drag Coefficient')
ax4_2.plot(
    sf(flatPlateAng.X, wl, po),
    sf(flatPlateAng.CD, wl, 1),
    'b-',
    label='Coefficient of Drag'
)

# Pitching Moment v Wind Velocity
ax5.set_xlabel('V_inf [m/s]')
ax5.set_ylabel('Pitching Moment [N*m]')
ax5.plot(
    flatPlateVel.X,
    flatPlateVel.PM,
    'r-',
    label='Flat Plate',
    zorder=10
)
ax5.plot(
    halfSphere.X,
    halfSphere.PM,
    'b-',
    label='Half Sphere',
    zorder=15
)
ax5.plot(
    invertedCup.X,
    invertedCup.PM,
    'k-',
    label='Inverted Cup',
    zorder=5
)
ax5.plot(
    sphere.X,
    sphere.PM,
    'g-',
    label='Sphere',
    zorder=0
)

# Graph formating
ax1.set_title('Normal Force vs Free Stream Velocity')
ax1.set_xlim(xmin=0)
ax1.legend()
ax2.set_title('Axial Force vs Free Stream Velocity')
ax2.set_xlim(xmin=0)
ax2.legend()
ax3.set_title('Normal/Axial Force vs Angle of Attack')
ax3.set_xlim(xmin=0)
ax3_2.set_xlim(xmin=0)
ax4.set_title('Coefficient of Lift vs Angle of Attack')
ax4.set_xlim(xmin=0)
ax4_2.set_xlim(xmin=0)
ax5.set_title('Pitching Moment vs Free Stream Velocity')
ax5.set_xlim(xmin=0)
ax5.legend()
plt.show()