import cv2
import numpy as np
from time import sleep
import argparse
import random

from environment import Environment, Parking1
from pathplanning_ZS import PathPlanning, ParkPathPlanning, interpolate_path
from control import Car_Dynamics, MPC_Controller, Linear_MPC_Controller
from utils import angle_of_line, make_square, DataLogger

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--x_start', type=int, default=0, help='X of start')
    parser.add_argument('--y_start', type=int, default=90, help='Y of start')
    parser.add_argument('--psi_start', type=int, default=0, help='psi of start')
    parser.add_argument('--x_end', type=int, default=90, help='X of end')
    parser.add_argument('--y_end', type=int, default=80, help='Y of end')
    parser.add_argument('--parking', type=int, default=1, help='park position in parking1 out of 24')

    args = parser.parse_args()
    logger = DataLogger()

    ########################## default variables ################################################
    start = np.array([args.x_start, args.y_start])
    end   = np.array([args.x_end, args.y_end])
    #############################################################################################

    # environment margin  : 5
    # pathplanning margin : 5

    ########################## defining obstacles ###############################################
    random_emptyslot = np.random.randint(0,24)
    parking1 = Parking1(random_emptyslot) # random parking slot selection ## of can be args.parking
    end, obs = parking1.generate_obstacles()

    # Adding of obstables to the environment
    # square1 = make_square(10,65,20)
    # square2 = make_square(15,30,20)
    # square3 = make_square(50,50,10)
    # obs = np.vstack([obs,square1,square2,square3])

    # new_obs = np.array([[78,78],[79,79],[78,79]])
    # obs = np.vstack([obs,new_obs])
    #############################################################################################

    ########################### initialization ##################################################
    env = Environment(obs)
    my_car = Car_Dynamics(start[0], start[1], 0, np.deg2rad(args.psi_start), length=4, dt=0.2)
    MPC_HORIZON = 5
    controller = MPC_Controller()
    # controller = Linear_MPC_Controller()

    parking_slots = parking1.get_parking_slots()  # Assuming you have such a method

    # Then, when calling render, pass parking_slots
    res = env.render(my_car.x, my_car.y, my_car.psi, 0, parking_slots)    

    cv2.imshow('environment', res)
    key = cv2.waitKey(1)
    #############################################################################################
    '''
    Need to implement a code here to replace the whole part below to make the entire path planning an iterative process and to make use of the control in this process.

    Things to update
    - Obstacles
    - Parking Slots
    - Nearest Parking Slots
    - PathPlanning
    - ParkPathPlanning
    '''

    ############################# path planning #################################################
    park_path_planner = ParkPathPlanning(obs)
    path_planner = PathPlanning(obs)

    print('planning park scenario ...')
    new_end, park_path, ensure_path1, ensure_path2 = park_path_planner.generate_park_scenario(int(start[0]),int(start[1]),int(end[0]),int(end[1]))
    
    print('routing to destination ...')
    path = path_planner.plan_path(int(start[0]),int(start[1]),int(new_end[0]),int(new_end[1]))
    path = np.vstack([path, ensure_path1])

    print('interpolating ...')
    interpolated_path = interpolate_path(path, sample_rate=5)
    interpolated_park_path = interpolate_path(park_path, sample_rate=2)
    interpolated_park_path = np.vstack([ensure_path1[::-1], interpolated_park_path, ensure_path2[::-1]])

    env.draw_path(interpolated_path)
    env.draw_path(interpolated_park_path)

    final_path = np.vstack([interpolated_path, interpolated_park_path, ensure_path2])


    #############################################################################################

    ################################## control ##################################################
    print('driving to destination ...')
    for i,point in enumerate(final_path):
        
            acc, delta = controller.optimize(my_car, final_path[i:i+MPC_HORIZON])
            my_car.update_state(my_car.move(acc,  delta))
            res = env.render(my_car.x, my_car.y, my_car.psi, delta, parking_slots)
            logger.log(point, my_car, acc, delta)
            cv2.imshow('environment', res)
            key = cv2.waitKey(1)
            if key == ord('s'):
                cv2.imwrite('res.png', res*255)

    # zeroing car steer
    res = env.render(my_car.x, my_car.y, my_car.psi, 0, parking_slots)
    logger.save_data()
    cv2.imshow('environment', res)
    key = cv2.waitKey()
    #############################################################################################

    cv2.destroyAllWindows()
