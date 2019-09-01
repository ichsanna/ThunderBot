from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket
import math
import time


class ThunderBot(BaseAgent):
    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.controller = SimpleControllerState()

        # Game values
        self.goal_own = {"x": 0,"y": 5120,"z": 642}
        self.goal_opponent = self.goal_own
        if (self.team==0):
            self.goal_own["y"]*=-1
        elif (self.team==1):
            self.goal_opponent["y"]*=-1
        self.bot_pos = None
        self.bot_yaw = None
        self.boost = 0
        
    # belum dipanggil
    def find_boost(self):
        field_info = self.get_field_info()
        self.boost_locations = field_info.boost_pads
        self.big_boost_locations = [self.boost_locations[3],self.boost_locations[4],self.boost_locations[15],self.boost_locations[18],self.boost_locations[29],self.boost_locations[30]]
        go_for_boost = "any"
        if (self.boost < 10):
            go_for_boost = "big"
        return self.find_nearest_boost(go_for_boost)
        
    def find_nearest_boost(self,boost_type):
        min_value = 100000
        min_loc=-1
        if (boost_type=="any"):
            boost_loc=self.boost_locations
        else:
            boost_loc=self.big_boost_locations
        for i in range(len(boost_loc)):
                boost_range = math.sqrt((boost_loc[i].location.x-self.bot_pos.x)**2+(boost_loc[i].location.y-self.bot_pos.y)**2)
                if (boost_range<min_value):
                    min_value=boost_range
                    min_loc=i
        return boost_loc[min_loc].location

    #Doesnt work
    def aim_goal(self):
        angle_between_ball_and_goal = math.atan2(self.ball_pos.y - self.goal_opponent["y"], self.ball_pos.x - self.goal_opponent["x"])
        ratio_of_angle_between_ball_and_goal = (self.ball_pos.x - self.goal_opponent["x"]) / (self.ball_pos.y - self.goal_opponent["y"])
        # 4096
        longer_ball_to_goal_line_point = {"x": 4000, "y": ratio_of_angle_between_ball_and_goal*4000}
        # print (longer_ball_to_goal_line_point)
        self.renderer.begin_rendering()
        # draw a point aim goal
        self.renderer.draw_rect_3d([longer_ball_to_goal_line_point["x"],longer_ball_to_goal_line_point["y"],80], 5, 5, True, self.renderer.purple())
        self.renderer.end_rendering()
        return longer_ball_to_goal_line_point

    def aim(self, target_x, target_y):
        
        angle_between_bot_and_target = math.atan2(target_y - self.bot_pos.y, target_x - self.bot_pos.x)

        angle_front_to_target = math.degrees(angle_between_bot_and_target - self.bot_yaw)

        # Correct the values
        if angle_front_to_target < -180:    
            angle_front_to_target += 360
        if angle_front_to_target > 180:
            angle_front_to_target -= 360
        if angle_front_to_target < -10:
            # If the target is more than 10 degrees right from the centre, steer left
            self.controller.steer = -1
            self.controller.boost = False
        elif angle_front_to_target > 10:
            # If the target is more than 10 degrees left from the centre, steer right
            self.controller.steer = 1
            self.controller.boost = False
        else:
            # If the target is less than 10 degrees from the centre, steer straight
            if (self.boost > 0):
                self.controller.boost = True
            self.controller.steer = 0

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        # Update game data variables
        my_car = packet.game_cars[self.index]
        human_car = packet.game_cars[self.index+1]
        self.bot_yaw = my_car.physics.rotation.yaw
        self.bot_pos = my_car.physics.location
        the_ball = packet.game_ball
        self.ball_pos = the_ball.physics.location
        self.boost = my_car.boost
        if (self.boost < 20):
            boost_target = self.find_boost()
            if (time.time() % 2 < 0.1):
                #print ("X",boost_target.x)
                #print ("Y",boost_target.y)
                print (self.boost)
            self.aim(boost_target.x,boost_target.y)
        else:
            if (self.bot_pos.y>self.ball_pos.y):
                self.aim(self.goal_own["x"],self.goal_own["y"])
            else:
                self.aim(self.ball_pos.x, self.ball_pos.y)
        self.controller.throttle = 1
        # print (human_car.physics.rotation.yaw)
        # print (human_car.physics.location)
        return self.controller
