from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket
import math
import time


class ThunderBot(BaseAgent):
    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.controller = SimpleControllerState()

        # Game values
        self.bot_pos = None
        self.bot_yaw = None
        self.boost = 0
        self.should_dodge = False
        self.on_second_jump = False
        self.next_dodge_time = 0
        self.initialized = False
        self.kickoff_type = 0
        self.target_loc = {"x": 0,"y": 0,"z": 0}

    def initialize(self):
        self.goal_own = {"x": 0,"y": 5120,"z": 642}
        self.goal_opponent = {"x": 0,"y": 5120,"z": 642}
        if (self.team==0):
            self.goal_own["y"]*=-1
            self.target_loc_kickoff = {"x": 0,"y": -2816,"z": 70}
        elif (self.team==1):
            self.goal_opponent["y"]*=-1
            self.target_loc_kickoff = {"x": 0,"y": 2816,"z": 70}
        self.initialized = True
        
    def calculate_angle(self,target_x, target_y):
        angle_between_bot_and_target = math.atan2(target_y - self.bot_pos.y, target_x - self.bot_pos.x)
        angle_front_to_target = math.degrees(angle_between_bot_and_target - self.bot_yaw)
        if angle_front_to_target < -180:    
            angle_front_to_target += 360
        if angle_front_to_target > 180:
            angle_front_to_target -= 360
        return angle_front_to_target

    def calculate_distance(self,x1,y1,x2,y2):
        return math.sqrt((x2-x1)**2+(y2-y1)**2)
    
    def calculate_velocity(self,x,y):
        return math.sqrt(x**2+y**2)

    def calculate_time_to_impact(self,distance,speed_a_x,speed_a_y,speed_b_x,speed_b_y):
        return distance/(self.calculate_velocity(speed_a_x+speed_b_x,speed_a_y+speed_b_y))

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
            multiplier = math.sin(abs(angle_bot_to_boost/2))
            boost_distance = self.calculate_distance(self.bot_pos.x,self.bot_pos.y,boost_loc[i].location.x,boost_loc[i].location.y)
            boost_distance*=abs(multiplier**3)
            if (boost_distance<min_value):
                min_value=boost_distance
                min_loc=i
        return boost_loc[min_loc].location

    def aim(self, target_x, target_y):
        angle_bot_to_target = self.calculate_angle(target_x,target_y)
        if abs(angle_bot_to_target) > 120:
            self.controller.handbrake = True
        else:
            self.controller.handbrake = False
        if angle_bot_to_target < -10:
            # If the target is more than 5 degrees right from the center, steer left
            self.controller.steer = -1
            self.controller.boost = False
        elif angle_bot_to_target > 10:
            # If the target is more than 5 degrees left from the center, steer right
            self.controller.steer = 1
            self.controller.boost = False
        else:
            # If the target is less than 5 degrees from the center, steer straight
            if (abs(self.bot_pitch)<0.1 and self.bot_roll==0 and self.bot_wheel_contact):                
                if (self.distance_to_target>7000 and 1500<self.bot_velocity<1800) or (self.boost==0 and self.bot_velocity>1000):
                    self.should_dodge = True
                elif (self.boost > 0) and self.bot_velocity<2250:
                    self.controller.boost = True
            self.controller.steer = angle_bot_to_target/10

    def check_for_dodge(self, target_x, target_y):
        if self.should_dodge:
            if time.time() > self.next_dodge_time:
                self.aim(target_x, target_y)
                self.controller.jump = True
                self.controller.pitch = -1
                if self.on_second_jump:
                    self.on_second_jump = False
                    self.should_dodge = False
                else:
                    self.on_second_jump = True
                    self.next_dodge_time = time.time() + 0.10
            elif time.time() < self.next_dodge_time-0.05:
                self.controller.jump = True

    def wheel_recover(self):
        if (self.bot_pitch>1):
            self.controller.pitch = -1
        elif (self.bot_pitch<-1):
            self.controller.pitch = 1
        else:
            self.controller.pitch = self.bot_pitch*-1
        if (self.bot_roll>1):
            self.controller.roll = -1
        elif (self.bot_roll<-1):
            self.controller.roll = 1
        else:
            self.controller.roll = self.bot_roll*-1

    def kickoff(self,pos):
        if (pos==1 or pos==2):
            self.target_loc = {"x": self.ball_pos.x, "y": self.ball_pos.y, "z": self.ball_pos.z}
        elif (pos==3 or pos==4):
            if (self.bot_pos.x-20<self.target_loc_kickoff["x"]<self.bot_pos.x+20 and self.bot_pos.y-20<self.target_loc_kickoff["y"]<self.bot_pos.y+20):
                self.target_loc_kickoff_acquired = True
            if (self.target_loc_kickoff_acquired):
                self.target_loc = {"x": self.ball_pos.x, "y": self.ball_pos.y, "z": self.ball_pos.z}
            else:
                self.target_loc = {"x": self.target_loc_kickoff["x"], "y": self.target_loc_kickoff["y"], "z": self.target_loc_kickoff["z"]}
        elif (pos==5):
            self.target_loc = {"x": self.ball_pos.x, "y": self.ball_pos.y, "z": self.ball_pos.z}
            if self.distance_to_ball > 2000:
                self.should_dodge = True
        if self.distance_to_ball < 250:
            self.should_dodge = True
        self.check_for_dodge(self.ball_pos.x, self.ball_pos.y)  

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        if (self.initialized==False):
            self.initialize()
        # Update game data variables
        self.game_info = packet.game_info
        my_car = packet.game_cars[self.index]
        human_car = packet.game_cars[self.index+1]
        # print (human_car.physics.rotation.roll,"  ",human_car.physics.rotation.pitch)
        self.bot_yaw = my_car.physics.rotation.yaw
        self.bot_yaw2 = human_car.physics.rotation.yaw
        self.bot_pos = my_car.physics.location
        self.bot_pos2 = human_car.physics.location
        self.bot_pitch= my_car.physics.rotation.pitch
        self.bot_roll= my_car.physics.rotation.roll
        self.bot_wheel_contact = my_car.has_wheel_contact
        self.bot_velocity = self.calculate_velocity(my_car.physics.velocity.x,my_car.physics.velocity.y)
        self.bot_velocity2 = self.calculate_velocity(human_car.physics.velocity.x,human_car.physics.velocity.y)
        the_ball = packet.game_ball
        self.ball_pos = the_ball.physics.location
        self.boost = my_car.boost
        self.boost2 = human_car.boost
        target = "none"
        bot_loc = {"x": self.bot_pos.x,"y": self.bot_pos.y,"z": self.bot_pos.z}
        self.angle_bot_to_ball = self.calculate_angle(self.ball_pos.x,self.ball_pos.y)
        self.distance_to_ball = self.calculate_distance(self.bot_pos.x,self.bot_pos.y,self.ball_pos.x,self.ball_pos.y)
        self.controller.jump = False
        self.controller.pitch = 0
        self.controller.roll = 0
        self.controller.throttle = 1
        if (self.game_info.is_kickoff_pause):
            if (self.bot_pos.x==-2048 and self.bot_pos.y==-2560) or (self.bot_pos.x==2048 and self.bot_pos.y==2560):
                self.kickoff_type = 1
            elif (self.bot_pos.x==2048 and self.bot_pos.y==-2560) or (self.bot_pos.x==-2048 and self.bot_pos.y==2560):
                self.kickoff_type = 2
            elif (self.bot_pos.x==-256 and self.bot_pos.y==-3840) or (self.bot_pos.x==256 and self.bot_pos.y==3840):
                self.kickoff_type = 3
            elif (self.bot_pos.x==256 and self.bot_pos.y==-3840) or (self.bot_pos.x==-256 and self.bot_pos.y==3840):
                self.kickoff_type = 4
            elif (self.bot_pos.x==0 and self.bot_pos.y==-4608) or (self.bot_pos.x==0 and self.bot_pos.y==4608):
                self.kickoff_type = 5
            self.kickoff(self.kickoff_type)
        else:
            self.target_loc_kickoff_acquired = False
            # if (self.boost < 20 and (self.angle_bot_to_ball > 30 or (self.distance_to_ball > 1000 and self.ball_pos.x!=0 and self.ball_pos.y!=0))) :
            #     target = "boost"
            #     boost_target = self.find_boost()
            #     target_loc = {"x": boost_target.x,"y": boost_target.y,"z": boost_target.z}
            if (self.team==0 and self.bot_pos.y>self.ball_pos.y) or (self.team==1 and self.bot_pos.y<self.ball_pos.y):
                target = "own goal"
                self.target_loc = {"x": self.goal_own["x"], "y": self.goal_own["y"],"z": self.goal_own["z"]}
            else:
                target = "ball"
                self.target_loc = {"x": self.ball_pos.x, "y": self.ball_pos.y, "z": self.ball_pos.z}
            self.distance_to_target = self.calculate_distance(self.bot_pos.x,self.bot_pos.y,self.target_loc["x"],self.target_loc["y"])
            if self.distance_to_ball < 500 and self.bot_pos.z<200:
                self.should_dodge = True
            self.check_for_dodge(self.ball_pos.x, self.ball_pos.y)      
            if (self.bot_pos.z>200):
                self.wheel_recover()
        self.aim(self.target_loc["x"],self.target_loc["y"])
        self.renderer.begin_rendering()
        # self.renderer.draw_string_2d(2, 0, 2, 2, str(self.bot_velocity), self.renderer.white())
        self.renderer.draw_string_2d(2, 40, 2, 2, str(self.bot_pos2), self.renderer.white())
        # self.renderer.draw_string_2d(2, 80, 2, 2, str(self.bot_boost), self.renderer.white())
        self.renderer.draw_line_3d((bot_loc["x"],bot_loc["y"],bot_loc["z"]),(self.target_loc["x"],self.target_loc["y"],self.target_loc["z"]),self.renderer.create_color(255, 200,200, 0))
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

