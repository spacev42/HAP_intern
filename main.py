import time
import numpy as np
from matplotlib import pyplot as plt
from solve import buoyancy
from density import density
from params import *
from theta0_a import theta0_a
import pandas as pd
import gc


def initialize(height):
    """ 
    defining initial parameters for a and theta0 grid
    :param height: current altitude
    :return: min and max values and step of grid  
    """
    if height < 21500:
        theta0_max = 25
        theta0_min = 0
        a_max = 16
        a_min = 5
        number_of_steps_a = 50
        number_of_steps_theta0 = 250
    else:
        theta0_max = 90
        theta0_min = 20
        a_max = 5.1
        a_min = -400
        number_of_steps_a = 100
        number_of_steps_theta0 = 700

    return a_min, a_max, number_of_steps_a, theta0_min,theta0_max, number_of_steps_theta0


def main(number_of_cores, height):
    rho_atm, _, P_atm, T_gas = density(height)

    a_min, a_max, number_of_steps_a, theta0_min,theta0_max, number_of_steps_theta0 = initialize(height)
    rmax_tol = 1e-2
    mgas_tol = 1e-2
    velocity_tol = 1e-2
    
    velocity = 0  
    velocity_output = 10
    m_gas_output = 0
    m_gas = 3.491565771 # mass of the lighter-than-air (LTA) gas (kg)

    while abs(m_gas_output - m_gas) > mgas_tol:
        velocity = velocity_output
        m_gas = m_gas_output
        gc.collect()
        print("velocity = ", velocity)
        rmax = rp_max
        rmax_new = 0
        count_rmax = 0
        epsilon = np.finfo(float).eps # very small number
        
        while rmax - rmax_new > rmax_tol:
            if rmax_new != 0:
                rmax = rmax_new

            number_of_recurse = 3
            a_min, a_max, number_of_steps_a, theta0_min, theta0_max, number_of_steps_theta0 = initialize(height)

            for i in range(number_of_recurse):
                print('r_max = ', rmax, ', DEPTH: ', i)
                
                theta_tol = 3 / (1.2)**i
                if i <= 5:
                    r_tol = 2 / 2 ** i 
                else:
                    r_tol = 1 / 10**2

                theta_step = (theta0_max - theta0_min) / number_of_steps_theta0
                a_step = (a_max - a_min) / number_of_steps_a

                # theta0 in degrees
                print("*"*20,"starting theta loop", "*"*20 )
                theta0, a, theta_last, r_last, max_radius, loss, z, r, theta = theta0_a([theta0_max, theta0_min, a_max, a_min, theta_step, a_step], 
                                                                                        [theta_tol, r_tol], rmax, velocity, number_of_cores)
                print("*"*20,"end theta loop", "*"*20 )

                theta0_max, theta0_min = theta0 + theta_step + epsilon, theta0 - theta_step - epsilon

                a_max, a_min = a + a_step + epsilon, a - a_step - epsilon 
               
            rmax_new = max_radius 
            count_rmax += 1

        print("Iterations for finding optimal rmax: ", count_rmax)

        volume = np.pi / 3 * ds * np.cos(np.radians(theta0)) * (r[0] ** 2 + r[0] * r[1] + r[1] ** 2)
        m_gas_output = 0
        for i in range(2, len(r)):
            dV_i = np.pi / 3 * ds * np.cos(theta[i - 1]) * (r[i - 1] ** 2 + r[i - 1] * r[i] + r[i] ** 2)
            volume += dV_i
            dm_i = (P_atm + buoyancy(height)*(z[i] - a)) * dV_i * mu_gas / (R * T_gas) 
            m_gas_output += dm_i
            
        
        Fg = (m_payload + m_b + m_gas) * g
        Fa = rho_atm * volume * g
        
        velocity_output = np.sign(Fa - Fg) * math.sqrt((2 * abs(Fa - Fg) / (Cx * rho_atm * math.pi * rmax ** 2)))
        F_drag = -Cx * (rho_atm * velocity_output * abs(velocity_output) * math.pi * rmax ** 2) / 2 
        dF = (Fa - Fg) + F_drag    
        

    Fg = (m_payload + m_b + m_gas) * g
    Fa = rho_atm * volume * g
    
    velocity_output = np.sign(Fa - Fg) * math.sqrt((2 * abs(Fa - Fg) / (Cx * rho_atm * math.pi * rmax ** 2)))
    F_drag = -Cx * (rho_atm * velocity_output * abs(velocity_output) * math.pi * rmax ** 2) / 2 
    dF = (Fa - Fg) + F_drag

    f = open(output_filename, 'w')

    print("_______________________height = ", height, "_______________________", file=f)
    print("theta0: ", theta0, ", a: ", a, file=f)
    print("Maximum radius: ", max_radius, file=f)
    print("Last theta: ", np.degrees(theta_last), ", Last R: ", r_last, file=f)
    print("Total lost (for theta0 and a): ", loss, file=f)
    print("___________________________________________________________________", file=f)
    print("Volume of the balloon: ", volume, file=f)
    print("Difference between m_gas and calculated m_gas: ", m_gas_output - m_gas, file=f)
    print("Difference betweend Fa and Fg: ", Fa - Fg, file=f)
    print("Difference between all forces {(Fa - Fg) + F_drag}: ", dF, file=f)
    print("Input velocity of the balloon: ", velocity, file=f)
    print("Output velocity of the balloon: ", velocity_output, file=f)
    print("Difference between input and output velocities: ", velocity - velocity_output, file=f)
    
    plt.plot(z, r)
    # plt.text(0.5, 0.5, 'height: {}, velocity: {}'.format(height, round(velocity, 3)))
    # plt.text(0.5, 0.2, 'theta0: {}, a: {}, volume: {}'.format(round(theta0, 4), round(a, 3), round(volume, 3)))
    plt.savefig(plot_filename)
 
    df = pd.DataFrame(data = {'z': z, 'r': r})
    df.to_csv(z2r_csv_filename)


if __name__=="__main__":
    """
    how to use:
    python main.py --number_of_cores NUMBER_OF_CORES --height HEIGHT
    """
    start = time.time()
    main(number_of_cores, height)
    end = time.time()
    
    f = open(output_filename, 'a')
    print("Running time: ", end - start, "s", file=f)
