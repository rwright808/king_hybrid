###NOTE: THIS IS BAD! should have neglected mixing of helium and GOX!!!
###NOTE: I forgot about moving boundary work --> ^extra bad :(

from rocketcea.cea_obj_w_units import CEA_Obj #how to access this as a non us citizen?
import CoolProp.CoolProp as CP #I love coolprop! ~ units: http://www.coolprop.org/v4/apidoc/CoolProp.html
import matplotlib.pyplot as plt
import numpy as np

#TODO: DOUBLE CHECK PropsSI units

R_UNIV = 8.314 #J/mol

def secant(func, x1):
    x_eps = x1 * 0.0005  # Set the tolerance to be 0.5% of init guess
    x2 = x1 - x1 * 0.05  # Set a second point 1% away from the original guess
    #print("x1 and x2: ", x1,x2)
    F1 = func(x1)  # Evaluate function at x1
    F2 = func(x2)  # Evaluate function at x2
    #print(F1,F2)
    kk = 1  # Set up counter
    kk_max = 1000

    while np.abs(x2 - x1) >= (x_eps) and kk < kk_max:  # While error is too large and counter is less than max
        x3 = x2 - (F2 * (x2 - x1) / (F2 - F1)) #TODO: divide by zero error
        x1 = x2  # Move everything forward
        x2 = x3
        F1 = F2
        F2 = func(x2) 
        kk = kk + 1
    x = x2
    return x



def perror(Mach_guess, y, pratio):
    #print("input mach: ",Mach_guess)
    pratio_est = (1+ ((y-1)/2)*Mach_guess**2)**(y/(y-1))
    pratio_diff = pratio - pratio_est
    #print(pratio_diff)
    return pratio_diff



class simpleAdiabaticExtPressurantTank():
    def __init__(self, pressurant, P_prestank, m_pres, P_proptank, V_PRESTANK, OUTLET_DIAM, TIMESTEP):

        ###setup initial conditions###
        self.pressurant = pressurant #string name for coolprop

        #upstream
        self.P_prestank = P_prestank #Pa
        self.m_prev = m_pres #kg
        self.m_pres = m_pres #kg
        self.V_PRESTANK = V_PRESTANK #m^3

        #downstream
        self.P_proptank = P_proptank #Pa
        self.outlet_diam = OUTLET_DIAM #m #TODO: make this an input
        self.A_outlet = 0.5*np.pi*self.outlet_diam**2 #m^2

        #setup calcs
        self.pratio = self.P_prestank/self.P_proptank #-
        self.pratio_error = 0.005

        self.rho_pres = self.m_pres / self.V_PRESTANK #kg/m^3

        self.u_pres = CP.PropsSI('U', 'D', self.rho_pres, 'P', self.P_prestank, pressurant) /1000 #kJ/kg
        self.T_prestank = CP.PropsSI('T', 'D', self.rho_pres, 'P', self.P_prestank, pressurant)  #K

        self.M_outlet = 1 #first guess for mach number

        # Get the specific heat capacities at constant pressure and volume
        #TODO: units
        Cp = CP.PropsSI('C', 'T', self.T_prestank, 'P', self.P_prestank, pressurant)  # Cp at specified T and P
        Cv = CP.PropsSI('O', 'T', self.T_prestank, 'P', self.P_prestank, pressurant)  # Cv at specified T and P
        self.y = Cp/Cv #-
        self.R = Cp-Cv #can probably just call coolprop to get this too

        self.TIMESTEP = TIMESTEP
        self.m_dot = 0 #kg/s
        self.T_outlet = self.T_prestank #K

        self.s_prestank = CP.PropsSI('S', 'T', self.T_prestank, 'D', self.rho_pres, pressurant) / 1000 #kJ/kg




    def inst(self, P_downstream):
        self.P_proptank = P_downstream
        self.pratio = self.P_prestank/self.P_proptank

        #step 1: find the mach number from the pressure drop using the secant method
        while np.abs(perror(self.M_outlet, self.y, self.pratio)) > self.pratio_error:
            self.M_outlet = secant((lambda M: perror(M, self.y, self.pratio)), self.M_outlet)

        #TODO: if mach number is above critical, flow reached limitting condition of choked flow
        if(self.M_outlet > 1):
            self.M_outlet = 1 #flow is choked 

        #print(self.T_prestank) 
        #print(self.M_outlet)

        #step 2: solve velocity of outlet 
        self.T_outlet = self.T_prestank*(self.P_proptank/self.P_prestank)**((self.y-1)/self.y)
        velo_outlet = self.M_outlet*np.sqrt(self.y*self.R*self.T_outlet)
        #print(velo_outlet)

        #step 3: solve mass flow rate, need density
        rho_outlet = self.rho_pres * (self.T_prestank/self.T_outlet)**((self.y-1)) #NOTE: triple check this when not hungry
        
        self.m_dot = rho_outlet*velo_outlet*self.A_outlet

        #step 4: update conservation of mass and recalculate tank properties for next step and update
        self.m_pres -= self.m_dot*self.TIMESTEP

        #print(self.m_pres, self.m_dot, rho_outlet, velo_outlet)

        self.rho_pres = self.m_pres / self.V_PRESTANK #kg/m^3
        
        #NOTE: using previous R and y to solve new conditions, just be aware
        self.T_prestank = self.T_prestank*(self.m_pres/self.m_prev)**(self.y-1)
        self.P_prestank = (self.m_pres*self.R*self.T_prestank)/self.V_PRESTANK
        #BUG: P_prestank increases on second timestep for certain??? see note above for potential fix!

        self.m_prev = self.m_pres
        #TODO: check units!
        self.s_prestank = CP.PropsSI('S', 'P', self.P_prestank, 'D', self.rho_pres, self.pressurant) / 1000 #kJ/kg

        #print("P: ", self.P_prestank, "v: ", (1/self.rho_pres), "T: ", self.T_prestank, "s: ", self.s_prestank)











class std_state_property_vector():
    def __init__(self):
        self.m = 0 #kg
        self.T = 0 #K
        self.P = 0 #Pa
        self.v = 0 #m^3/kg
        self.M = 0 #kg/mol
        self.cv = 0 #kJ/(Kg K)
        self.R = 0 #TODO: units
        self.u = 0 #kJ/kg

class mixture_state_property_vector():
    def __init__(self):
        #std properties
        self.m = 0 #kg
        self.T = 0 #K
        self.P = 0 #Pa
        self.v = 0 #m^3/kg
        self.M = 0 #kg/mol
        self.cv = 0 #KJ/(Kg K)
        self.R = 0 #TODO: units
        self.u = 0 #kJ/kg

        #NOTE: mixture properties are molar
        self.X_pres = 0
        self.X_prop = 0
        self.P_pres = 0
        self.P_prop = 0
        self.n_pres = 0
        self.n_prop = 0
        self.M_pres = 0
        self.M_prop = 0
        self.s_pres_M = 0
        self.s_prop_M = 0
        self.cv_pres_M = 0
        self.cv_prop_M = 0
        self.u_pres_M = 0
        self.u_prop_M = 0

class sat_liq_vap_property_vector():
    def __init__(self):
        #std properties
        self.m = 0 #kg
        self.T = 0 #K
        self.P = 0 #Pa
        self.v = 0 #m^3/kg
        self.M = 0 #kg/mol
        self.cv = 0 #KJ/(Kg K)
        self.R = 0 #TODO: units
        self.u = 0 #kJ/kg

        #sat liq vap properties
        self.x = 0
        self.hfg = 0

class heat_transfer_property_vector():
    def __init__(self,propellant):
        #std properties
        self.m = 0 #kg
        self.T = 0 #K
        self.P = 0 #Pa
        self.v = 0 #m^3/kg
        self.M = 0 #kg/mol
        self.cv = 0 #KJ/(Kg K)
        self.R = 0 #TODO: units
        self.u = 0 #kJ/kg

        #heat transfer properties
        self.propellant = propellant
        self.cp = 0 #KJ/(Kg K)
        self.k = 0 #TODO: units
        self.visc = 0 #TODO: units
        self.beta = 0

    def update_beta(self):
        ###solve coeff of thermal expansion
        delta_T = 1e-3  # Small temperature change for finite difference
        # Get specific volume (V) in m^3/kg
        v1 = CP.PropsSI('V', 'T', self.T, 'P', self.P, self.propellant)
        v2 = CP.PropsSI('V', 'T', self.T, 'P', self.P, self.propellant) #BUG: this is wrong did i forget to add/subtract delta T?
        # Calculate the partial derivative of V with respect to T at constant P
        dVdT_P = (v2 - v1) / delta_T
        # Calculate the coefficient of thermal expansion (beta)
        self.beta = dVdT_P / v1

#TODO: properly pass in fluid names
def serror(T_2_guess, s_1_M, ullage_vec):
    #calculate p2
    ullage_vec.P_pres = ullage_vec.n_pres/ullage_vec.V * R_UNIV * T_2_guess 
    ullage_vec.P_prop = ullage_vec.n_prop/ullage_vec.V * R_UNIV * T_2_guess 
    ullage_vec.P = ullage_vec.P_pres + ullage_vec.P_prop
    
    #call COOLPROP #NOTE: use partial pressures #TODO: think of a better way to pass in fluid types
    ullage_vec.s_pres_M = ullage_vec.M_pres * CP.PropsSI('S', 'T', ullage_vec.T, 'P', ullage_vec.P_pres, 'He')
    ullage_vec.s_prop_M = ullage_vec.M_prop * CP.PropsSI('S', 'T', ullage_vec.T, 'P', ullage_vec.P_prop, 'O2')

    s_2_M = ullage_vec.X_pres * ullage_vec.s_pres_M + ullage_vec.X_prop * ullage_vec.s_prop_M
    s_diff_M = s_1_M - s_2_M
    return s_diff_M



#NOTE: assuming mixing under constant volume adiabatic
def solve_final_mixture(vec_1, vec_2, mode):


    final_mixture = mixture_state_property_vector()
    final_mixture.m = vec_1.m +vec_2.m

    #solve mols of added pressurant!

    n_1 = vec_1.m/vec_1.M

    #update mixture ratios:
    n_total = vec_2.n_pres + vec_2.n_prop + n_1

    vec_2.X_pres = vec_2.n_pres / n_total
    vec_2.X_prop = vec_2.n_prop / n_total
    X_1 = n_1/ n_total

    #solve final temp, pres:
    #converting cv in vec 1 to molar
    final_mixture.T = ( (vec_1.m*vec_1.cv*vec_1.M*vec_1.T) + (vec_2.X_pres*vec_2.M_pres*vec_2.cv_pres*vec_2.T) + (vec_2.X_prop*vec_2.M_prop*vec_2.cv_prop*vec_2.T) ) / ( (X_1*vec_1.M*vec_1.cv) + (vec_2.X_pres*vec_2.cv_pres) + (vec_2.X_prop*vec_2.cv_prop) )

    final_mixture.P = 1 / ( (vec_1.X*vec_1.T)/(vec_1.P*final_mixture.T) + (vec_2.X_pres*vec_2.T)/(vec_2.P*final_mixture.T) + (vec_2.X_prop*vec_2.T)/(vec_2.P*final_mixture.T) )

    final_mixture.v = (vec_1.V*vec_1.m +vec_2.V*vec_2.m) / final_mixture.m  #isochoric

    #TODO: now that we know P and V we can calculate all the remaining properties of the mixture


    ###if pressurant, add vec2Xpres and X_1, else add X_1 to propellant
    if(mode == 1):
        final_mixture.n_pres = vec_2.n_pres + n_1
        final_mixture.n_prop = vec_2.n_prop
        
        final_mixture.X_pres = vec_2.X_pres+ X_1
        final_mixture.X_prop = vec_2.X_prop

    else:
        final_mixture.n_pres = vec_2.n_pres
        final_mixture.n_prop = vec_2.n_prop + n_1

        final_mixture.X_pres = vec_2.X_pres
        final_mixture.X_prop = vec_2.X_prop+ X_1

    #now that we know mixture ratios solve remaining properties
    final_mixture.P_pres = final_mixture.P * final_mixture.X_pres
    final_mixture.P_prop = final_mixture.P * final_mixture.X_prop

    #TODO: think of a better way to pass in fluid names
    final_mixture.s_pres_M = final_mixture.M_pres * CP.PropsSI('S', 'T', final_mixture.T, 'P', final_mixture.P_pres, 'He')
    final_mixture.s_prop_M = final_mixture.M_prop * CP.PropsSI('S', 'T', final_mixture.T, 'P', final_mixture.P_prop, 'O2')

    final_mixture.M = final_mixture.m / (final_mixture.n_pres + final_mixture.n_prop)

    final_mixture.u = (final_mixture.X_pres * final_mixture.M_pres * CP.PropsSI('U', 'T', final_mixture.T, 'P', final_mixture.P_pres, 'He') + final_mixture.X_prop * final_mixture.M_prop * CP.PropsSI('U', 'T', final_mixture.T, 'P', final_mixture.P_prop, 'He') ) / final_mixture.m

    return final_mixture 
    






def uerror(T_guess, u2, ullage_vec):

    ###input T_guess into COOLPROP to solve u_pres and u_prop

    #NOTE: WHAT WOULD SECOND INPUT BE????
    ullage_vec.u_pres =  CP.PropsSI('U', 'T', T_guess, 'P', ullage_vec.P_pres, 'He')
    ullage_vec.u_prop = CP.PropsSI('U', 'T', T_guess, 'P', ullage_vec.P_prop, 'O2')

    u_est = ullage_vec.X_pres * ullage_vec.M_pres * ullage_vec.u_pres + ullage_vec.X_prop * ullage_vec.M_prop * ullage_vec.u_prop

    u_diff = u2 - u_est
    return u_diff

#https://www.nasa.gov/wp-content/uploads/2024/04/gfssp-tankpressurization-jpp2001.pdf?emrc=66201987b6c8c
class simpleAdiabaticCryoOxidizerTank(): #it is not simple
    def __init__(self, propellant, pressurant, id_PROPTANK, P_proptank, m_prop, V_PROPTANK, TIMESTEP, pressurant_name, P_prestank, m_pres, P_oxtank, V_PRESTANK, OUTLET_DIAM):
        
        self.pressurant = pressurant
        self.propellant = propellant

        self.P_proptank = P_proptank

        ###setup state vectors for fluids

        #fluid: added pressurant NOTE: PURE SUBSTANCE
        self.added_pressurant_vec = std_state_property_vector()

        self.added_pressurant_vec.M = CP.PropsSI('M', 'T', 300, 'P', 101325, pressurant) #kg/mol - propsi requires dummy inputs (T, P)
        self.added_pressurant_vec.P = P_proptank


        #fluid: ullage mixture NOTE: MIXTURE
        self.ullage_vec = mixture_state_property_vector() #on startup no ullage mixture!!!!!

        #TODO: THIS inputting in wrong variable!!!!!
        self.ullage_vec.s_pres_M = CP.PropsSI('M', 'T', 300, 'P', 101325, pressurant) #kg/mol - propsi requires dummy inputs (T, P)
        self.ullage_vec.s_prop_M = CP.PropsSI('M', 'T', 300, 'P', 101325, propellant) #kg/mol - propsi requires dummy inputs (T, P)
        

        #fluid: liquid propellant NOTE: PURE SUBSTANCE
        self.propellant_liq_vec = heat_transfer_property_vector(propellant)

        self.propellant_liq_vec.M = CP.PropsSI('M', 'T', 300, 'P', 101325, propellant) #kg/mol - propsi requires dummy inputs (T, P)
        self.propellant_liq_vec.m = m_prop
        self.propellant_liq_vec.v = V_PROPTANK/m_prop
        self.propellant_liq_vec.P = P_proptank
        self.propellant_liq_vec.R = None

        self.propellant_liq_vec.T = CP.PropsSI('T', 'V', self.propellant_liq_vec.v, 'P', self.P_proptank, self.propellant)
        # ^ValueError: Input pair variable is invalid and output(s) are non-trivial; cannot do state update : PropsSI("T","V",5.148147988e-06,"P",200000,"O2")
        #NOTE: might be input error the inputs might be garbage
        self.propellant_liq_vec.cp = CP.PropsSI('C', 'V', self.propellant_liq_vec.v, 'P', self.P_proptank, self.propellant)
        self.propellant_liq_vec.u = CP.PropsSI('U', 'V', self.propellant_liq_vec.v, 'P', self.P_proptank, self.propellant)


        #fluid: sat liq vapor NOTE: SATURATED LIQUID VAPOR PURE SUBSTANCE
        self.sat_liq_vap_propellant = sat_liq_vap_property_vector()
        self.sat_liq_vap_propellant.R = None

        #fluid: pure propellant vapor vec NOTE: PURE SUBSTANCE
        self.propellant_vapor_vec = std_state_property_vector()

        self.propellant_vapor_vec.M = CP.PropsSI('M', 'T', 300, 'P', 101325, propellant) #kg/mol - propsi requires dummy inputs (T, P)
        self.propellant_vapor_vec.R = R_UNIV / self.propellant_vapor_vec.M



        ###coefficients and setup for heat transfer analysis
        self.C = 0.27 #NOTE: DOUBLE CHECK THIS APPLIES TO SPECIFIC FLUIDS OR IF ITS GENERAL
        self.n = 0.25
        self.K_H = 1 #this is a heat transfer corrective factor that is set to 1 from paper

        self.id_PROPTANK = id_PROPTANK #in metric
        self.A_proptank = 0.25*np.pi*id_PROPTANK**2 #NOTE: passing in metric tank diam!!!!!

        #TODO: oxygen starts as saturated liquid vapor!!!!!!
        self.V_ullage = 0 #m^3
        self.V_prop = V_PROPTANK #m^3

        self.sratio_error = 0.01
        self.uratio_error = 0.01
        self.TIMESTEP = TIMESTEP

        self.pressurantTank = simpleAdiabaticExtPressurantTank(pressurant_name, P_prestank, m_pres, P_oxtank, V_PRESTANK, OUTLET_DIAM, TIMESTEP)


        




###TODO: DEBUG!!!!!!
    def inst(self, t): #thermo HELL

        #run pressurant tank
        self.pressurantTank.inst(self.P_proptank)
        m_dot_pres = self.pressurant.m_dot_pres
        h_pres = self.pressurant.h_pres

        ###NOTE: step 1: ADDING PRESSURANT

        #pressurant added NOTE: assuming P_pressurant = P_proptank, know pressurant is a pure substance gas
        #solve/update new pressurant properties #NOTE: pressurant is pure substance

        self.added_pressurant_vec.m = m_dot_pres*self.TIMESTEP
        self.added_pressurant_vec.P = self.P_proptank

        self.added_pressurant_vec.T = CP.PropsSI('T', 'H', h_pres, 'P', self.P_proptank, self.pressurant)
        self.added_pressurant_vec.v =  CP.PropsSI('V', 'H', h_pres, 'P', self.P_proptank, self.pressurant)
        self.added_pressurant_vec.cv = CP.PropsSI('CVMASS', 'H', h_pres, 'P', self.P_proptank, self.pressurant)
        self.added_pressurant_vec.u = CP.PropsSI('U', 'H', h_pres, 'P', self.P_proptank, self.pressurant)


        #BUG: this is not updating everything that needs to be updated!
        #now that pressurant is added, ullage is compressed so recalc volume
        if(t != TIMESTEP):
            #coolprop gives specific, convert to molar
            #solving specific entropy before additional helium compresses
            self.ullage_vec.s_pres_M = self.ullage_vec.M_pres * CP.PropsSI('S', 'T', self.ullage_vec.T, 'P', self.ullage_vec.P_pres, self.pressurant)
            self.ullage_vec.s_prop_M = self.ullage_vec.M_prop * CP.PropsSI('S', 'T', self.ullage_vec.T, 'P', self.ullage_vec.P_prop, self.propellant)
            

            s_1_M = self.ullage_vec.X_pres * self.ullage_vec.s_pres_M + self.ullage_vec.X_prop * self.ullage_vec.s_prop_M

            #now we add helium and compress
            #normally ullage is a mixture of pressurant and propellant so we need to update the mixture properties!!!
            self.V_ullage -= self.added_pressurant_vec.v * self.added_pressurant_vec.m
            self.ullage_vec.v = self.V_ullage/self.ullage_vec.m

            #NOW SECANT METHOD TO ITERATIVELY SOLVE FOR FINAL TEMP AND PRESSURE USING ISENTROPIC PROCESS ASSUMPTION
            #def serror(T_2_guess, s_1_M, ullage_vec):
            #NOTE: is this updating everything in the ullage vector? --> yes?

            while np.abs(serror(self.ullage_vec.T, s_1_M, self.ullage_vec)) > self.sratio_error:
                self.ullage_vec.T = secant((lambda S: serror(self.ullage_vec.T, s_1_M, self.ullage_vec)), s_1_M) #changed to serror from perror i think perror was a mistake but idk

            #NOTE: need to get self.ullage_vec.P, i think since we are updating ullage_vec we are already getting the updated val!

            #TODO:update all ullage mixture properties!!! (now know temperature, pressure, mixture ratios!!!!!
            #NOTE: can do this in serror since python passes in references!
            self.ullage_vec.P_pres = self.ullage_vec.P * self.ullage_vec.X_pres
            self.ullage_vec.P_prop = self.ullage_vec.P * self.ullage_vec.X_prop

            self.ullage_vec.cv_pres_M = self.ullage_vec.M_pres * CP.PropsSI('C', 'T', self.ullage_vec.T, 'P', self.ullage_vec.P_pres, self.pressurant)
            self.ullage_vec.cv_prop_M = self.ullage_vec.M_prop * CP.PropsSI('C', 'T', self.ullage_vec.T, 'P', self.ullage_vec.P_prop, self.propellant)

            self.ullage_vec.s_pres_M = self.ullage_vec.M_pres * CP.PropsSI('S', 'T', self.ullage_vec.T, 'P', self.ullage_vec.P_pres, self.pressurant)
            self.ullage_vec.s_prop_M = self.ullage_vec.M_prop * CP.PropsSI('S', 'T', self.ullage_vec.T, 'P', self.ullage_vec.P_prop, self.propellant)


        
        else: 
            #BUG: I DONT LIKE THIS!
            #if its the first timestep, ullage is purely pressurant so update ullage vector to equal pressurant vector
            self.V_ullage = self.added_pressurant_vec.v * self.added_pressurant_vec.m
            self.ullage_vec = self.added_pressurant_vec
            #NOTE: only standard properties updated here, all mixture properties are 0 NOTE: this might not be compatible in future steps?
        


        ###NOTE: step 2 - mixing of ullage vector and pressurant vector
        #now that initial properties are updated, can solve mixture and get final ullage properties
        self.ullage_vec = solve_final_mixture(self.added_pressurant_vec, self.ullage_vec, 1)


        ###NOTE: step 3 - heat transfer from ullage into liquid propellant and update ullage

        #now we know mixture properties and should already know liquid properties can solve heat transfer from mixture ullage to liquid propellant
        Gr = (self.id_PROPTANK**3)*((1/self.propellant_liq_vec.v)**2)* 9.81 * self.propellant_liq_vec.beta * np.abs(self.ullage_vec.T - self.propellant_liq_vec.T) / (self.propellant_liq_vec.visc**2) #Grashof number
        Pr = self.propellant_liq_vec.cp * self.propellant_liq_vec.visc / self.propellant_liq_vec.k #Prandtl number

        h_conv = self.K_H * self.C * (self.propellant_liq_vec.k/self.id_PROPTANK) * (Gr/Pr)**self.n
        Q_dot_interface = h_conv * self.A_proptank * (self.ullage_vec.T - self.propellant_liq_vec.T) 
        
        Q_interface = Q_dot_interface * self.TIMESTEP #TODO: use to solve solve Temperature of saturated liquid vapor!

        #since energy is being transfered out of ullage, we need to recalculate new temperature!!!!
        self.ullage_vec.u -= Q_interface/self.ullage_vec.m

        ###secant method to find ullage temperature
        while np.abs(uerror(self.ullage_vec.T, self.ullage_vec.u, self.ullage_vec)) > self.uratio_error:
                self.ullage_vec.T = secant((lambda U: uerror(self.ullage_vec.T, self.ullage_vec.u, self.ullage_vec)), self.ullage_vec.u)
        
        #now that we know temperature, we can get all the other properties!!!!!! (know u, u_pres_M and prop, )

        self.ullage_vec.P_pres = CP.PropsSI('P', 'T', self.ullage_vec.T, 'U', (self.ullage_vec.u_pres_M/self.ullage_vec.M_pres), self.pressurant)
        self.ullage_vec.P_prop = CP.PropsSI('P', 'T', self.ullage_vec.T, 'U', (self.ullage_vec.u_prop_M/self.ullage_vec.M_prop), self.propellant)

        self.ullage_vec.P = self.ullage_vec.X_pres * self.ullage_vec.P_pres + self.ullage_vec.X_prop * self.ullage_vec.P_prop

        self.ullage_vec.R = self.ullage_vec.X_pres * self.added_pressurant_vec.R + self.ullage_vec.X_prop * self.propellant_vapor_vec.R

        #solve cv of components
        self.ullage_vec.cv_pres_M = self.ullage_vec.M_pres *CP.PropsSI('CVMASS', 'T', self.ullage_vec.T, 'U', (self.ullage_vec.u_pres_M/self.ullage_vec.M_pres), self.pressurant)
        self.ullage_vec.cv_prop_M = self.ullage_vec.M_prop *CP.PropsSI('CVMASS', 'T', self.ullage_vec.T, 'U', (self.ullage_vec.u_prop_M/self.ullage_vec.M_prop), self.propellant)

        #use mol ratios to find ullage cv
        self.ullage_vec.cv = self.ullage_vec.X_pres * self.ullage_vec.cv_pres_M + self.ullage_vec.X_prop * self.ullage_vec.cv_prop_M

        #solve entropy of components!
        self.ullage_vec.s_pres_M = self.ullage_vec.M_pres * CP.PropsSI('S', 'T', self.ullage_vec.T, 'U', (self.ullage_vec.u_pres_M/self.ullage_vec.M_pres), self.pressurant)
        self.ullage_vec.s_prop_M = self.ullage_vec.M_prop * CP.PropsSI('S', 'T', self.ullage_vec.T, 'U', (self.ullage_vec.u_prop_M/self.ullage_vec.M_prop), self.propellant)
            





        ###NOTE: step 4 - heat transfer will boil off some LOX!!!! --> isochoric heating
        
        #translate pure substance to sat liq vap vector!!!
        #know the mass and specific volume is the same between comp liquid and sat liq vap states:
        self.sat_liq_vap_propellant.m = self.propellant_liq_vec.m
        self.sat_liq_vap_propellant.v = self.propellant_liq_vec.v

        #first law!
        self.sat_liq_vap_propellant.u = self.propellant_liq_vec.u + Q_interface/self.propellant_liq_vec.m

        u_f = CP.PropsSI('U', 'X', 1, 'P', self.sat_liq_vap_propellant.P, self.propellant)
        u_g = CP.PropsSI('U', 'X', 0, 'P', self.sat_liq_vap_propellant.P, self.propellant)

        self.sat_liq_vap_propellant.x = (self.sat_liq_vap_propellant.u-u_f) / (u_g-u_f)

        #easy update T and P for sat liquid vapor because we know its on the sat liquid vapor line
        self.sat_liq_vap_propellant.T = CP.PropsSI('T', 'V', self.sat_liq_vap_propellant.v, 'U', self.sat_liq_vap_propellant.u, self.propellant)
        self.sat_liq_vap_propellant.P = CP.PropsSI('P', 'V', self.sat_liq_vap_propellant.v, 'U', self.sat_liq_vap_propellant.u, self.propellant)

        self.sat_liq_vap_propellant.cv = CP.PropsSI('CVMASS', 'X', self.sat_liq_vap_propellant.x, 'T', self.sat_liq_vap_propellant.T, self.propellant)


        #use heat transfer to solve mass transfer from propellant liquid vapor to ullage mixture for vapor vector?
        T_sat = CP.PropsSI('T', 'X', 0, 'P', self.P_proptank, self.propellant)

        h_f = CP.PropsSI('H', 'X', 1, 'P', self.sat_liq_vap_propellant.P, self.propellant)
        h_g = CP.PropsSI('H', 'X', 0, 'P', self.sat_liq_vap_propellant.P, self.propellant)

        m_dot_vap = Q_dot_interface / ( (h_g-h_f) + self.propellant_liq_vec.cp * (T_sat - self.sat_liq_vap_propellant.T) )

        
        






        ###NOTE: step 5 -  mixing ullage with vapor, first need to translate sat_liq_vap vector to vap vector
        self.propellant_vapor_vec.m = m_dot_vap*self.TIMESTEP #kg

        self.propellant_vapor_vec.T = self.sat_liq_vap_propellant.T #K
        self.propellant_vapor_vec.P = self.sat_liq_vap_propellant.P #Pa

        self.propellant_vapor_vec.v = CP.PropsSI('V', 'X', 0, 'P', self.propellant_vapor_vec.P, self.propellant) #kg/m^3
        self.propellant_vapor_vec.cv = CP.PropsSI('CVMASS', 'X', 0, 'P', self.propellant_vapor_vec.P, self.propellant) 
        self.propellant_vapor_vec.u = CP.PropsSI('U', 'X', 0, 'P', self.propellant_vapor_vec.P, self.propellant) 


        

        #another mixture
        self.ullage_vec = solve_final_mixture(self.propellant_vapor_vec, self.ullage_vec, 0)

        #TODO: update liquid vector!!!!!!
        self.propellant_liq_vec.T = self.sat_liq_vap_propellant.T #K
        self.propellant_liq_vec.P = self.sat_liq_vap_propellant.P #Pa

        self.propellant_liq_vec.m = self.sat_liq_vap_propellant.m - m_dot_vap*self.TIMESTEP #kg

        self.propellant_liq_vec.v = CP.PropsSI('V', 'X', 1, 'P', self.propellant_liq_vec.P, self.propellant)
        self.propellant_liq_vec.cv = CP.PropsSI('CVMASS', 'X', 1, 'P', self.propellant_liq_vec.P, self.propellant)
        self.propellant_liq_vec.u = CP.PropsSI('U', 'X', 1, 'P', self.propellant_liq_vec.P, self.propellant)









        ##NOTE: #step 6 - solve mass flow rate out of tank and then update properties of sat liq vap and ullage

        #NOW WE CAN FINALLY SOLVE MASS FLOW RATE OUT OF TANK:
        self.m_dot_proptank = m_dot_pres * (1/self.propellant_liq_vec.v) * self.ullage_vec.R * self.ullage_vec.T / self.P_proptank

        #update initial conditions for next iteration!!!!! less mass in tank, particularily new tank pressure
        
        #update propellant liquid properties, assuming incompressible
        self.propellant_liq_vec.m -= self.m_dot_proptank * TIMESTEP

        #update heat transfer properties for propellant (pure substance liquid)
        self.propellant_liq_vec.cp = CP.PropsSI('C', 'T', self.propellant_liq_vec.T, 'P', self.P_proptank, self.propellant)
        self.propellant_liq_vec.k = CP.PropsSI('L', 'T', self.propellant_liq_vec.T, 'P', self.P_proptank, self.propellant)
        self.propellant_liq_vec.visc = CP.PropsSI('V', 'T', self.propellant_liq_vec.T, 'P', self.P_proptank, self.propellant)
        self.propellant_liq_vec.update_beta()
        


        #update ullage properties (volume changed) recalc propellant volume
        self.V_prop = self.propellant_liq_vec.m * self.propellant_liq_vec.v

        #update ullage properties
        self.V_ullage = self.V_TANK - self.V_prop
        self.ullage_vec.v = self.V_ullage / self.ullage_vec.m

        #Now iteratively solve temperature based on first law!!!!!
        ###secant method to find ullage temperature
        while np.abs(uerror(self.ullage_vec.T, self.ullage_vec.u, self.ullage_vec)) > self.uratio_error:
                self.ullage_vec.T = secant((lambda U: uerror(self.ullage_vec.T, self.ullage_vec.u, self.ullage_vec)), self.ullage_vec.u)
        
        #now that we know temperature, we can get all the other properties!!!!!! (know u, u_pres_M and prop, )

        self.ullage_vec.P_pres = CP.PropsSI('P', 'T', self.ullage_vec.T, 'U', (self.ullage_vec.u_pres_M/self.ullage_vec.M_pres), self.pressurant)
        self.ullage_vec.P_prop = CP.PropsSI('P', 'T', self.ullage_vec.T, 'U', (self.ullage_vec.u_prop_M/self.ullage_vec.M_prop), self.propellant)

        self.ullage_vec.P = self.ullage_vec.X_pres * self.ullage_vec.P_pres + self.ullage_vec.X_prop * self.ullage_vec.P_prop

        self.ullage_vec.R = self.ullage_vec.X_pres * self.added_pressurant_vec.R + self.ullage_vec.X_prop * self.propellant_vapor_vec.R

        #solve cv of components
        self.ullage_vec.cv_pres_M = self.ullage_vec.M_pres *CP.PropsSI('CVMASS', 'T', self.ullage_vec.T, 'U', (self.ullage_vec.u_pres_M/self.ullage_vec.M_pres), self.pressurant)
        self.ullage_vec.cv_prop_M = self.ullage_vec.M_prop *CP.PropsSI('CVMASS', 'T', self.ullage_vec.T, 'U', (self.ullage_vec.u_prop_M/self.ullage_vec.M_prop), self.propellant)

        #use mol ratios to find ullage cv
        self.ullage_vec.cv = self.ullage_vec.X_pres * self.ullage_vec.cv_pres_M + self.ullage_vec.X_prop * self.ullage_vec.cv_prop_M

        #solve entropy of components!
        self.ullage_vec.s_pres_M = self.ullage_vec.M_pres * CP.PropsSI('S', 'T', self.ullage_vec.T, 'U', (self.ullage_vec.u_pres_M/self.ullage_vec.M_pres), self.pressurant)
        self.ullage_vec.s_prop_M = self.ullage_vec.M_prop * CP.PropsSI('S', 'T', self.ullage_vec.T, 'U', (self.ullage_vec.u_prop_M/self.ullage_vec.M_prop), self.propellant)
            
        self.P_proptank = self.ullage_vec.P

        #after finishing ^ it seems there is allegedly a thermo mixtures library, would have been nice...