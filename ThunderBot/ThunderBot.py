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

    def calculate_angle(self,target_x, target_y):
        angle_between_bot_and_target = math.atan2(target_y - self.bot_pos.y, target_x - self.bot_pos.x)
        angle_front_to_target = math.degrees(angle_between_bot_and_target - self.bot_yaw)
        # Correct the values
        if angle_front_to_target < -180:    
            angle_front_to_target += 360
        if angle_front_to_target > 180:
            angle_front_to_target -= 360
        return angle_front_to_target

    def calculate_distance(self,x1,y1,x2,y2):
        return math.sqrt((x2-x1)**2+(y2-y1)**2)


    def find_boost(self):
        field_info = self.get_field_info()
        self.boost_locations = field_info.boost_pads
        self.big_boost_locations = [self.boost_locations[3],self.boost_locations[4],self.boost_locations[15],self.boost_locations[18],self.boost_locations[29],self.boost_locations[30]]
        go_for_boost = "any"
        if (self.boost < 10 and (abs(self.angle_bot_to_ball) > 90 or self.distance_to_ball > 1500)):
            go_for_boost = "big"
        return self.find_nearest_boost(go_for_boost)
        
    def find_nearest_boost(self,boost_type):
        min_value = 900000
        min_loc=-1
        if (boost_type=="any"):
            boost_loc=self.boost_locations
        else:
            boost_loc=self.big_boost_locations
        for i in range(len(boost_loc)):
            angle_bot_to_boost = self.calculate_angle(boost_loc[i].location.x,boost_loc[i].location.y)
            multiplier = math.sin(angle_bot_to_boost/2)
            boost_distance = self.calculate_distance(self.bot_pos.x,self.bot_pos.y,boost_loc[i].location.x,boost_loc[i].location.y)
            boost_distance*=abs(multiplier)
            if (boost_distance<min_value):
                min_value=boost_distance
                min_loc=i
        # self.boost_locked = boost_loc[min_loc].location
        return boost_loc[min_loc].location

    def aim(self, target_x, target_y):
        angle_bot_to_target = self.calculate_angle(target_x,target_y)
        if abs(angle_bot_to_target) > 120:
            self.controller.handbrake = True
        else:
            self.controller.handbrake = False
        if angle_bot_to_target < -5:
            # If the target is more than 5 degrees right from the center, steer left
            self.controller.steer = -1
            self.controller.boost = False
        elif angle_bot_to_target > 5:
            # If the target is more than 5 degrees left from the center, steer right
            self.controller.steer = 1
            self.controller.boost = False
        else:
            # If the target is less than 5 degrees from the center, steer straight
            if (self.distance_to_ball<500 and 100 < self.ball_pos.z < 250):
                self.controller.jump = True
            elif (self.boost > 0):
                self.controller.jump = False
                self.controller.boost = True
            self.controller.steer = 0       

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        # Update game data variables
        self.game_info = packet.game_info
        print (self.game_info.is_kickoff_pause)
        my_car = packet.game_cars[self.index]
        human_car = packet.game_cars[self.index+1]
        self.bot_yaw = my_car.physics.rotation.yaw
        self.bot_yaw2 = human_car.physics.rotation.yaw
        self.bot_pos = my_car.physics.location
        self.bot_pos2 = human_car.physics.location
        the_ball = packet.game_ball
        self.ball_pos = the_ball.physics.location
        self.boost = my_car.boost
        target = "none"
        bot_loc = {"x": self.bot_pos.x,"y": self.bot_pos.y,"z": self.bot_pos.z}

        self.angle_bot_to_ball = self.calculate_angle(self.ball_pos.x,self.ball_pos.y)
        # print (self.angle_bot_to_ball)
        self.distance_to_ball = self.calculate_distance(self.bot_pos.x,self.bot_pos.y,self.ball_pos.x,self.ball_pos.y)
        if (self.boost < 20 and (self.angle_bot_to_ball > 30 or (self.distance_to_ball > 1000 and self.ball_pos.x!=0 and self.ball_pos.y!=0))) :
            target = "boost"
            boost_target = self.find_boost()
            target_loc = {"x": boost_target.x,"y": boost_target.y,"z": boost_target.z}
        else:
            if (self.bot_pos.y>self.ball_pos.y):
                target = "own goal"
                target_loc = {"x": self.goal_own["x"], "y": self.goal_own["y"],"z": self.goal_own["z"]}
            else:
                target = "ball"
                target_loc = {"x": self.ball_pos.x, "y": self.ball_pos.y, "z": self.ball_pos.z}
        self.aim(target_loc["x"],target_loc["y"])
        # print (self.ball_pos.z)
        self.controller.throttle = 1
        self.renderer.begin_rendering()
        self.renderer.draw_string_2d(2, 2, 2, 2, target, self.renderer.white())
        self.renderer.draw_string_2d(2, 40, 2, 2, str(self.boost), self.renderer.white())
        self.renderer.draw_line_3d((bot_loc["x"],bot_loc["y"],bot_loc["z"]),(target_loc["x"],target_loc["y"],target_loc["z"]),self.renderer.create_color(255, 200,200, 0))
        self.renderer.end_rendering()
        
        # ball_prediction = self.get_ball_prediction_struct()
        # if (ball_prediction is not None) and (time.time() % 5 < 1):
        #     for i in range(0, ball_prediction.num_slices):
        #         prediction_slice = ball_prediction.slices[i]
        #         location = prediction_slice.physics.location
        #         print ("At time {}, the ball will be at ({}, {}, {})".format(prediction_slice.game_seconds, location.x, location.y, location.z))
        # print (human_car.physics.rotation.yaw)
        # print (human_car.physics.location)
        return self.controller
