from enum import Enum
from queue import PriorityQueue
import numpy as np
import matplotlib.pyplot as plt
from bresenham import bresenham

def create_grid(data, drone_altitude, safety_distance):
    """
    Returns a grid representation of a 2D configuration space
    based on given obstacle data, drone altitude and safety distance
    arguments.
    """

    # minimum and maximum north coordinates
    north_min = np.floor(np.min(data[:, 0] - data[:, 3]))
    north_max = np.ceil(np.max(data[:, 0] + data[:, 3]))

    # minimum and maximum east coordinates
    east_min = np.floor(np.min(data[:, 1] - data[:, 4]))
    east_max = np.ceil(np.max(data[:, 1] + data[:, 4]))

    # given the minimum and maximum coordinates we can
    # calculate the size of the grid.
    north_size = int(np.ceil(north_max - north_min))
    east_size = int(np.ceil(east_max - east_min))

    # Initialize an empty grid
    grid = np.zeros((north_size, east_size))

    # Populate the grid with obstacles
    for i in range(data.shape[0]):
        north, east, alt, d_north, d_east, d_alt = data[i, :]
        if alt + d_alt + safety_distance > drone_altitude:
            obstacle = [
                int(np.clip(north - d_north - safety_distance - north_min, 0, north_size-1)),
                int(np.clip(north + d_north + safety_distance - north_min, 0, north_size-1)),
                int(np.clip(east - d_east - safety_distance - east_min, 0, east_size-1)),
                int(np.clip(east + d_east + safety_distance - east_min, 0, east_size-1)),
            ]
            grid[obstacle[0]:obstacle[1]+1, obstacle[2]:obstacle[3]+1] = 1

    return grid, int(north_min), int(east_min)


def ned_to_grid(ned_position,north_min,east_min,grid_shape):

    north_size,east_size = grid_shape
    
    return (int(np.clip(ned_position[0]-north_min,0,north_size-1)),
            int(np.clip(ned_position[1]-east_min,0,east_size-1))
            )


def grid_to_ned(grid_position,altitude,north_min,east_min):

    return (grid_position[0]+north_min,
            grid_position[1]+east_min,
            -altitude)


def grid_to_on_grid(grid,off_grid_pt):
    """"
    returns the indices of the closest grid point with no obstacle.
    off_grid_pt is a tuple containing the indices of a grid point. 
    """

    free_points_n,free_points_e = np.nonzero(np.logical_not(grid))
    dist_to_free_points = np.sqrt( (off_grid_pt[0]-free_points_n)**2 + (off_grid_pt[1]-free_points_e)**2 )
    ind_closest_among_free_points = np.argmin(dist_to_free_points)

    return (int(free_points_n[ind_closest_among_free_points]),
            int(free_points_e[ind_closest_among_free_points])
            )



class Action(Enum):
    """
    An action is represented by a 3 element tuple.
    
    The first 2 values are the delta of the action relative
    to the current grid position. The third and final value
    is the cost of performing the action.
    """
    LEFT = (0, -1, 1)
    RIGHT = (0, 1, 1)
    UP = (-1, 0, 1)
    DOWN = (1, 0, 1)
    UPRIGHT = (-1,1,1.41)
    DOWNRIGHT = (1,1,1.41)
    DOWNLEFT = (1,-1,1.41)
    UPLEFT = (-1,-1,1.41)
    
    @property
    def cost(self):
        return self.value[2]
    
    @property
    def delta(self):
        return (self.value[0], self.value[1])
            
    
def valid_actions(grid, current_node):
    """
    Returns a list of valid actions given a grid and current node.
    """
    valid = [Action.UP, Action.LEFT, Action.RIGHT, Action.DOWN , 
             Action.UPRIGHT, Action.DOWNRIGHT, Action.DOWNLEFT, 
             Action.UPLEFT
            ]
   
    for action in valid[:]:
        next_node = (current_node[0] + action.delta[0],current_node[1] + action.delta[1])
        if next_node[0]<0 or next_node[0]>grid.shape[0]-1 \
                or next_node[1]<0 or next_node[1]>grid.shape[1]-1:
            valid.remove(action)
            continue
        if grid[next_node[0],next_node[1]] == 1:
            valid.remove(action)
            
    return valid



def a_star(grid, h, start, goal):

    path = []
    path_cost = 0
    queue = PriorityQueue()
    queue.put((0, start))
    visited = set(start)

    branch = {}
    found = False
    
    while not queue.empty():
        item = queue.get()
        current_node = item[1]
        if current_node == start:
            current_cost = 0.0
        else:              
            current_cost = branch[current_node][0]
            
        if current_node == goal:        
            print('Found a path.')
            found = True
            break
        else:
            for action in valid_actions(grid, current_node):
                # get the tuple representation
                da = action.delta
                next_node = (current_node[0] + da[0], current_node[1] + da[1])
                branch_cost = current_cost + action.cost
                queue_cost = branch_cost + h(next_node, goal)
                
                if next_node not in visited:                
                    visited.add(next_node)               
                    branch[next_node] = (branch_cost, current_node, action)
                    queue.put((queue_cost, next_node))
             
    if found:
        # retrace steps
        n = goal
        path_cost = branch[n][0]
        path.append(goal)
        while branch[n][1] != start:
            path.append(branch[n][1])
            n = branch[n][1]
        path.append(branch[n][1])
    else:
        print('**********************')
        print('Failed to find a path!')
        print('**********************') 

    plot_results = False
    if plot_results:

        plt.imshow(grid, cmap='Greys', origin='lower')

        # For the purposes of the visual the east coordinate lay along
        # the x-axis and the north coordinates long the y-axis.
        plt.plot(start[1], start[0], 'x')
        plt.plot(goal[1], goal[0], 'x')

        if path is not None:
            pp = np.array(path)
            plt.plot(pp[:, 1], pp[:, 0], 'g')


        Plt.xlabel('EAST')
        plt.ylabel('NORTH')
        plt.show()




    return path[::-1], path_cost



def heuristic(position, goal_position):
    return np.linalg.norm(np.array(position) - np.array(goal_position))



def line_crashes(start,end,grid):
    """
    True if the line from start to end intersects an obstacle.

    start and end are coordinates inside the grid
    """
    cells = np.array(list(bresenham(start[0], start[1], end[0], end[1])))

    total_obstacles = np.sum( grid[cells[:,0],cells[:,1]] )
    
    return total_obstacles  > 0

    

def prune(path,grid):
    """ 
    This function prunes a path. The adopted algorithm invokes Bresenham's method.
    """

    if len(path) < 3:
        pruned_path = path
        return pruned_path

    start = path[0]
    goal = path[-1]

    pruned_path = [start]

    for point in path[1:]:

        if line_crashes(pruned_path[-1],point,grid):
            if previous_point:
                pruned_path = pruned_path + [previous_point]
                previous_point = []
            else:
                # if two consecutive points are found to crash by Bresenham, we have to add them anyway.
                pruned_path = pruned_path + [point]
        else:
            previous_point = point
            

    if goal not in pruned_path:
        pruned_path = pruned_path + [goal]
            
    plot_results = False
    if plot_results:

        plt.imshow(grid, cmap='Greys', origin='lower')

        
        plt.plot(start[1], start[0], 'x')
        plt.plot(goal[1], goal[0], 'x')

        if path is not None:
            pp = np.array(path)
            plt.plot(pp[:, 1], pp[:, 0], 'r')


        if pruned_path is not None:
            pp = np.array(pruned_path)
            plt.plot(pp[:, 1], pp[:, 0], 'g')
            plt.scatter(pp[:, 1], pp[:, 0])

        plt.xlabel('EAST')
        plt.ylabel('NORTH')

        plt.show()
    
    return pruned_path
