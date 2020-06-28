import numpy as np
import logging
from collections import OrderedDict
from py4j.java_gateway import get_field


class GymAI(object):
    def __init__(self, gateway, pipe, frameskip=True):
        self.gateway = gateway
        self.pipe = pipe
        self.width = 96  # The width of the display to obtain
        self.height = 64  # The height of the display to obtain
        self.grayscale = True  # The display's color to obtain true for grayscale, false for RGB

        self.obs = None
        self.dic = dict()
        self.just_inited = True
        self.attack_type_str = {1: "high", 2: "middle", 3: "low", 4: "throw"}
        self.state_strs = {0: "STAND", 1: "CROUCH", 2: "AIR", 3: "DOWN", }
        self.action_strs = {0: 'AIR', 1: 'AIR_A', 2: 'AIR_B', 3: 'AIR_D_DB_BA', 4: 'AIR_D_DB_BB', 5: 'AIR_D_DF_FA',
                            6: 'AIR_D_DF_FB', 7: 'AIR_DA', 8: 'AIR_DB', 9: 'AIR_F_D_DFA', 10: 'AIR_F_D_DFB',
                            11: 'AIR_FA', 12: 'AIR_FB', 13: 'AIR_GUARD', 14: 'AIR_GUARD_RECOV', 15: 'AIR_RECOV',
                            16: 'AIR_UA', 17: 'AIR_UB', 18: 'BACK_JUMP', 19: 'BACK_STEP', 20: 'CHANGE_DOWN',
                            21: 'CROUCH', 22: 'CROUCH_A', 23: 'CROUCH_B', 24: 'CROUCH_FA', 25: 'CROUCH_FB',
                            26: 'CROUCH_GUARD', 27: 'CROUCH_GUARD_RECOV', 28: 'CROUCH_RECOV', 29: 'DASH', 30: 'DOWN',
                            31: 'FOR_JUMP', 32: 'FORWARD_WALK', 33: 'JUMP', 34: 'LANDING', 35: 'NEUTRAL', 36: 'RISE',
                            37: 'STAND', 38: 'STAND_A', 39: 'STAND_B', 40: 'STAND_D_DB_BA', 41: 'STAND_D_DB_BB',
                            42: 'STAND_D_DF_FA', 43: 'STAND_D_DF_FB', 44: 'STAND_D_DF_FC', 45: 'STAND_F_D_DFA',
                            46: 'STAND_F_D_DFB', 47: 'STAND_FA', 48: 'STAND_FB', 49: 'STAND_GUARD',
                            50: 'STAND_GUARD_RECOV', 51: 'STAND_RECOV', 52: 'THROW_A', 53: 'THROW_B', 54: 'THROW_HIT',
                            55: 'THROW_SUFFER'}
        self.actions_air = {1: 'AIR_A', 2: 'AIR_B', 3: 'AIR_D_DB_BA', 4: 'AIR_D_DB_BB', 5: 'AIR_D_DF_FA',
                            6: 'AIR_D_DF_FB', 7: 'AIR_DA', 8: 'AIR_DB', 9: 'AIR_F_D_DFA', 10: 'AIR_F_D_DFB',
                            11: 'AIR_FA', 12: 'AIR_FB', 13: 'AIR_GUARD', 16: 'AIR_UA', 17: 'AIR_UB'}

        self.actions_ground = {18: 'BACK_JUMP', 19: 'BACK_STEP', 22: 'CROUCH_A', 23: 'CROUCH_B', 24: 'CROUCH_FA',
                               25: 'CROUCH_FB', 26: 'CROUCH_GUARD', 29: 'DASH', 31: 'FOR_JUMP', 32: 'FORWARD_WALK',
                               33: 'JUMP', 37: 'STAND', 38: 'STAND_A', 39: 'STAND_B', 40: 'STAND_D_DB_BA',
                               41: 'STAND_D_DB_BB', 42: 'STAND_D_DF_FA', 43: 'STAND_D_DF_FB', 44: 'STAND_D_DF_FC',
                               45: 'STAND_F_D_DFA', 46: 'STAND_F_D_DFB', 47: 'STAND_FA', 48: 'STAND_FB',
                               49: 'STAND_GUARD', 52: 'THROW_A', 53: 'THROW_B'}
        self.forward_walk = False
        self.forward_walk_timer = 0
        self.pre_framedata = None
        self.frameskip = frameskip

    def close(self):
        pass

    def initialize(self, gameData, player):
        self.inputKey = self.gateway.jvm.struct.Key()
        self.frameData = self.gateway.jvm.struct.FrameData()
        self.cc = self.gateway.jvm.aiinterface.CommandCenter()

        self.player = player
        self.gameData = gameData
        self.simulator = gameData.getSimulator()

        return 0

    # please define this method when you use FightingICE version 3.20 or later
    def roundEnd(self, p1hp,p2hp, frames):
        self.get_enough_energy_actions()
        self.dic['my_action_enough'] = self.my_actions_enough
        if p1hp <= p2hp:
            self.reward -= 1
            print("Lost, p1hp:{}, p2hp:{}, frame used: {}".format(p1hp,  p2hp,frames))
        elif p1hp > p2hp:
            self.reward += 1
            print("Win!, p1hp:{}, p2hp:{}, frame used: {}".format(p1hp,  p2hp,frames))
        self.pipe.send([self.obs, self.reward, True, self.dic])
        print("send obs for round End")
        self.just_inited = True
        # request = self.pipe.recv()
        # if request == "close":
        #     return
        self.pre_framedata = None
        self.obs = None

    # Please define this method when you use FightingICE version 4.00 or later
    def getScreenData(self, sd):
        self.screenData = sd

    def getInformation(self, frameData, isControl):
        # self.pre_framedata = frameData if self.pre_framedata is None else self.frameData
        self.frameData = frameData
        # if frameData.getFramesNumber() < 14:
        #     self.frameData = frameData
        # else:
        #     self.frameData = self.simulator.simulate(frameData, self.player, None, None, 14)
        self.isControl = isControl
        self.cc.setFrameData(self.frameData, self.player)
        if frameData.getEmptyFlag():
            return

    def input(self):
        return self.inputKey

    def gameEnd(self):
        pass

    def processing(self):
        if self.frameData.getEmptyFlag() or self.frameData.getRemainingTime() <= 0:
            self.isGameJustStarted = True
            return

        if self.frameskip:
            if self.cc.getSkillFlag():
                self.inputKey = self.cc.getSkillKey()
                return
            if not self.isControl:
                return

        # make forward walk continuous until 1s or force changed by opponent
        if self.forward_walk and self.frameData.getFramesNumber() - self.forward_walk_timer <= 60 and self.frameData.getCharacter(
                self.player).getAction().name() == "FORWARD_WALK":
            print("Continue forward walk, remaining frames: {}".format(self.frameData.getFramesNumber() - self.forward_walk_timer))
            self.cc.commandCall(self.action_strs[32])
            self.inputKey = self.cc.getSkillKey()
            return

        self.inputKey.empty()
        self.cc.skillCancel()

        # if just inited, should wait for first reset()
        if self.just_inited:
            if self.pipe.poll(5):
                request = self.pipe.recv()
                print("Client Receive request: {}".format(request))
            else:
                # print("Client receive time out")
                return
            if request == "reset":
                self.just_inited = False
                self.obs = self.get_obs()
                # print("Just reset")
                self.pipe.send(self.obs)
                # print("Client send obs for new game")
            else:
                raise ValueError
        # if not just inited but self.obs is none, it means second/thrid round just started
        # should return only obs for reset()
        elif self.obs is None:
            self.obs = self.get_obs()
            self.pipe.send(self.obs)
            # print("Client send obs for new round")
        # if there is self.obs, do step() and return [obs, reward, done, info]
        else:
            self.get_enough_energy_actions()
            self.reward = self.get_reward()
            self.obs = self.get_obs()
            self.dic = dict()
            self.dic['my_action_enough'] = self.my_actions_enough
            self.dic['currentFrameNumber'] = self.frameData.getFramesNumber()
            self.dic['currentRound'] = self.frameData.getRound()
            self.dic['remainingTime'] = self.frameData.getRemainingTime()
            self.dic['distance'] = self.frameData.getDistanceX()
            self.dic['myHp'], self.dic['oppHp'] = self.obs_dict['myHp'],self.obs_dict['oppHp'],
            self.dic['oppAction']= self.obs_dict['myHp'],
            self.pipe.send([self.obs, self.reward, False, self.dic])
            # print("Client send obs for step")

        # print("Client waiting for step from Server")
        if self.pipe.poll(5):
            request = self.pipe.recv()
            # print("Client get step in {}".format(self.pipe))
        else:
            # print("Client receive time out")
            return
        if len(request) == 2 and request[0] == "step":
            action = request[1]
            self.cc.commandCall(self.action_strs[action])

            # make forward moving
            if action == 32:
                self.forward_walk = True
                self.forward_walk_timer = self.frameData.getFramesNumber()
            else:
                self.forward_walk = False
                self.forward_walk_timer = 0
            # print("Step Action: {}".format(self.action_strs[action]))
            # if not self.frameskip:
            self.inputKey = self.cc.getSkillKey()
        self.pre_framedata = self.frameData

    def get_reward(self):
        try:
            if self.pre_framedata.getEmptyFlag() or self.frameData.getEmptyFlag():
                # print("pre_framedata or frameData Empty")
                reward = 0
            else:
                p2_hp_pre = self.pre_framedata.getCharacter(False).getHp()
                p1_hp_pre = self.pre_framedata.getCharacter(True).getHp()
                p2_hp_now = self.frameData.getCharacter(False).getHp()
                p1_hp_now = self.frameData.getCharacter(True).getHp()
                frame_num_pre = self.pre_framedata.getFramesNumber()
                frame_num_now = self.frameData.getFramesNumber()
                p1_hit_count_now = self.frameData.getCharacter(True).getHitCount()
                p2_hit_count_now = self.frameData.getCharacter(False).getHitCount()
                if self.player:
                    reward = (p2_hp_pre-p2_hp_now)/400 - (p1_hp_pre-p1_hp_now)/400
                             # + (p1_hit_count_now - p2_hit_count_now) - (frame_num_now - frame_num_pre) / 60
                else:
                    reward = (p1_hp_pre-p1_hp_now)/400 - (p2_hp_pre-p2_hp_now)/400
                             # + (p2_hit_count_now - p1_hit_count_now) - (frame_num_now - frame_num_pre) / 60
        except Exception:
            # print(Exception)
            reward = 0
        # print("Step reward:{}".format(reward))
        return reward

    def get_obs(self, player=True):
        my = self.frameData.getCharacter(self.player if player else not self.player)
        opp = self.frameData.getCharacter(not self.player if player else self.player)
        self.obs_dict = OrderedDict()
        obs_dict = OrderedDict()
        # my information
        obs_dict['myHp'] = abs(my.getHp() / 400)
        obs_dict['myEnergy'] = my.getEnergy() / 300
        obs_dict['myLeft'] = my.getLeft() / 960
        obs_dict['myRight'] = my.getRight() / 960
        obs_dict['myBottom'] = my.getBottom() / 640
        obs_dict['myTop'] = my.getTop() / 640
        obs_dict['mySpeedXAbs'] = abs(my.getSpeedX() / 15)
        obs_dict['mySpeedXDirection'] = 0 if my.getSpeedX() < 0 else 1
        obs_dict['mySpeedYAbs'] = abs(my.getSpeedY() / 28)
        obs_dict['mySpeedYDirection'] = 0 if my.getSpeedY() < 0 else 1
        obs_dict['myHitCount'] = my.getHitCount() / 20
        obs_dict['myisHitConfirm'] = 1 if my.isHitConfirm() else 0
        obs_dict['myisControl'] = 1 if my.isControl() else 0
        obs_dict['myRemainingFrame'] = my.getRemainingFrame() / 70
        for key, act_name in self.action_strs.items():
            obs_dict["myAction_"+act_name] = 1 if str(my.getAction().name()) == act_name else 0
        for key, state_name in self.state_strs.items():
            obs_dict["myState_" + state_name] = 1 if str(my.getState().name()) == state_name else 0

        # opp information
        obs_dict['oppHp'] = abs(opp.getHp() / 400)
        obs_dict['oppEnergy'] = opp.getEnergy() / 300
        obs_dict['oppLeft'] = opp.getLeft() / 960
        obs_dict['oppRight'] = opp.getRight() / 960
        obs_dict['oppBottom'] = opp.getBottom() / 640
        obs_dict['oppTop'] = opp.getTop() / 640
        obs_dict['oppSpeedXAbs'] = abs(opp.getSpeedX() / 15)
        obs_dict['oppSpeedXDirection'] = 0 if opp.getSpeedX() < 0 else 1
        obs_dict['oppSpeedYAbs'] = abs(opp.getSpeedY() / 28)
        obs_dict['oppSpeedYDirection'] = 0 if opp.getSpeedY() < 0 else 1
        obs_dict['oppHitCount'] = opp.getHitCount() / 20
        obs_dict['oppisHitConfirm'] = 1 if opp.isHitConfirm() else 0
        obs_dict['oppisControl'] = 1 if opp.isControl() else 0
        obs_dict['oppRemainingFrame'] = opp.getRemainingFrame() / 70
        for key, act_name in self.action_strs.items():
            obs_dict["oppAction_"+act_name] = 1 if str(opp.getAction().name()) == act_name else 0
        for key, state_name in self.state_strs.items():
            obs_dict["oppState_" + state_name] = 1 if str(opp.getState().name()) == state_name else 0

        # time information
        obs_dict['game_frame_num'] = self.frameData.getFramesNumber() / 3600

        myProjectiles = self.frameData.getProjectilesByP1()
        oppProjectiles = self.frameData.getProjectilesByP2()

        # should be the maximum projectile a character can own at same time, not sure is 2, originally is 2
        for i in range(2):
            if i < len(myProjectiles):
                obs_dict['myHitDamage_'+str(i)] = myProjectiles[i].getHitDamage() / 400.0
                obs_dict['myGuardDamage_'+str(i)] = myProjectiles[i].getGuardDamage() / 400.0
                obs_dict['myStartAddEnergy_'+str(i)] = myProjectiles[i].getStartAddEnergy() / 300.0
                obs_dict['myHitAddEnergy_'+str(i)] = myProjectiles[i].getHitAddEnergy() / 300.0
                obs_dict['myGuardAddEnergy_'+str(i)] = myProjectiles[i].getGuardAddEnergy() / 300.0
                obs_dict['myGiveEnergy_'+str(i)] = myProjectiles[i].getGiveEnergy() / 300.0
                obs_dict['myDownProp_'+str(i)] = 1 if myProjectiles[i].isDownProp() else 0
                obs_dict['myIsProjectile_'+str(i)] = 1 if myProjectiles[i].isProjectile() else 0
                obs_dict['myHitSpeedXAbs_'+str(i)] = abs(myProjectiles[i].getSpeedX() / 15.0)
                obs_dict['myHitSpeedXDirection_'+str(i)] = 0 if myProjectiles[i].getSpeedX() < 0 else 1
                obs_dict['myHitSpeedYAbs_'+str(i)] = abs(myProjectiles[i].getSpeedY() / 28.0)
                obs_dict['myHitSpeedYDirection_'+str(i)] = 0 if myProjectiles[i].getSpeedY() < 0 else 1
                obs_dict['myHitAreaNowLeft_'+str(i)] = myProjectiles[i].getCurrentHitArea().getLeft() / 960.0
                obs_dict['myHitAreaNowRight_'+str(i)] = myProjectiles[i].getCurrentHitArea().getRight() / 960.0
                obs_dict['myHitAreaNowTop_'+str(i)] = myProjectiles[i].getCurrentHitArea().getTop() / 640.0
                obs_dict['myHitAreaNowBottom_'+str(i)] = myProjectiles[i].getCurrentHitArea().getBottom() / 640.0
                obs_dict['myImpactX_'+str(i)] = myProjectiles[i].getImpactX() / 960.0
                obs_dict['myImpactY_'+str(i)] = myProjectiles[i].getImpactY() / 640.0
                obs_dict['myStartUp_'+str(i)] = myProjectiles[i].getGiveEnergy() / 70
                obs_dict['myActive_'+str(i)] = myProjectiles[i].getGiveEnergy() / 70
                obs_dict['myGiveGuardRecov_'+str(i)] = myProjectiles[i].getGiveGuardRecov() / 70
                for key, value in self.attack_type_str.items():
                    obs_dict['myAttackType_' + str(i)+'_'+value] = 1 if myProjectiles[i].getAttackType() == key else 0
            else:
                obs_dict['myHitDamage_'+str(i)] = 0
                obs_dict['myGuardDamage_'+str(i)] = 0
                obs_dict['myStartAddEnergy_'+str(i)] = 0
                obs_dict['myHitAddEnergy_'+str(i)] = 0
                obs_dict['myGuardAddEnergy_'+str(i)] = 0
                obs_dict['myGiveEnergy_'+str(i)] = 0
                obs_dict['myDownProp_'+str(i)] = 0
                obs_dict['myIsProjectile_'+str(i)] = 0
                obs_dict['myHitSpeedXAbs_'+str(i)] = 0
                obs_dict['myHitSpeedXDirection_'+str(i)] = 0
                obs_dict['myHitSpeedYAbs_'+str(i)] = 0
                obs_dict['myHitSpeedYDirection_'+str(i)] = 0
                obs_dict['myHitAreaNowLeft_'+str(i)] = 0
                obs_dict['myHitAreaNowRight_'+str(i)] = 0
                obs_dict['myHitAreaNowTop_'+str(i)] = 0
                obs_dict['myHitAreaNowBottom_'+str(i)] = 0
                obs_dict['myImpactX_'+str(i)] = 0
                obs_dict['myImpactY_'+str(i)] = 0
                obs_dict['myStartUp_'+str(i)] = 0
                obs_dict['myActive_'+str(i)] = 0
                obs_dict['myGiveGuardRecov_'+str(i)] = 0
                for key, value in self.attack_type_str.items():
                    obs_dict['myAttackType_' + str(i)+'_'+value] = 0

            if i < len(oppProjectiles):
                obs_dict['oppHitDamage_' + str(i)] = oppProjectiles[i].getHitDamage() / 400.0
                obs_dict['oppGuardDamage_' + str(i)] = oppProjectiles[i].getGuardDamage() / 400.0
                obs_dict['oppStartAddEnergy_' + str(i)] = oppProjectiles[i].getStartAddEnergy() / 300.0
                obs_dict['oppHitAddEnergy_' + str(i)] = oppProjectiles[i].getHitAddEnergy() / 300.0
                obs_dict['oppGuardAddEnergy_' + str(i)] = oppProjectiles[i].getGuardAddEnergy() / 300.0
                obs_dict['oppGiveEnergy_' + str(i)] = oppProjectiles[i].getGiveEnergy() / 300.0
                obs_dict['oppDownProp_' + str(i)] = 1 if oppProjectiles[i].isDownProp() else 0
                obs_dict['oppIsProjectile_' + str(i)] = 1 if oppProjectiles[i].isProjectile() else 0
                obs_dict['oppHitSpeedXAbs_' + str(i)] = abs(oppProjectiles[i].getSpeedX() / 15.0)
                obs_dict['oppHitSpeedXDirection_' + str(i)] = 0 if oppProjectiles[i].getSpeedX() < 0 else 1
                obs_dict['oppHitSpeedYAbs_' + str(i)] = abs(oppProjectiles[i].getSpeedY() / 28.0)
                obs_dict['oppHitSpeedYDirection_' + str(i)] = 0 if oppProjectiles[i].getSpeedY() < 0 else 1
                obs_dict['oppHitAreaNowLeft_' + str(i)] = oppProjectiles[i].getCurrentHitArea().getLeft() / 960.0
                obs_dict['oppHitAreaNowRight_' + str(i)] = oppProjectiles[i].getCurrentHitArea().getRight() / 960.0
                obs_dict['oppHitAreaNowTop_' + str(i)] = oppProjectiles[i].getCurrentHitArea().getTop() / 640.0
                obs_dict['oppHitAreaNowBottom_' + str(i)] = oppProjectiles[i].getCurrentHitArea().getBottom() / 640.0
                obs_dict['oppImpactX_' + str(i)] = oppProjectiles[i].getImpactX() / 960.0
                obs_dict['oppImpactY_' + str(i)] = oppProjectiles[i].getImpactY() / 640.0
                obs_dict['oppStartUp_' + str(i)] = oppProjectiles[i].getGiveEnergy() / 70
                obs_dict['oppActive_' + str(i)] = oppProjectiles[i].getGiveEnergy() / 70
                obs_dict['oppGiveGuardRecov_' + str(i)] = oppProjectiles[i].getGiveGuardRecov() / 70
                for key, value in self.attack_type_str.items():
                    obs_dict['oppAttackType_' + str(i) + '_' + value] = 1 if oppProjectiles[
                                                                                i].getAttackType() == key else 0
            else:
                obs_dict['oppHitDamage_' + str(i)] = 0
                obs_dict['oppGuardDamage_' + str(i)] = 0
                obs_dict['oppStartAddEnergy_' + str(i)] = 0
                obs_dict['oppHitAddEnergy_' + str(i)] = 0
                obs_dict['oppGuardAddEnergy_' + str(i)] = 0
                obs_dict['oppGiveEnergy_' + str(i)] = 0
                obs_dict['oppDownProp_' + str(i)] = 0
                obs_dict['oppIsProjectile_' + str(i)] = 0
                obs_dict['oppHitSpeedXAbs_' + str(i)] = 0
                obs_dict['oppHitSpeedXDirection_' + str(i)] = 0
                obs_dict['oppHitSpeedYAbs_' + str(i)] = 0
                obs_dict['oppHitSpeedYDirection_' + str(i)] = 0
                obs_dict['oppHitAreaNowLeft_' + str(i)] = 0
                obs_dict['oppHitAreaNowRight_' + str(i)] = 0
                obs_dict['oppHitAreaNowTop_' + str(i)] = 0
                obs_dict['oppHitAreaNowBottom_' + str(i)] = 0
                obs_dict['oppImpactX_' + str(i)] = 0
                obs_dict['oppImpactY_' + str(i)] = 0
                obs_dict['oppStartUp_' + str(i)] = 0
                obs_dict['oppActive_' + str(i)] = 0
                obs_dict['oppGiveGuardRecov_' + str(i)] = 0
                for key, value in self.attack_type_str.items():
                    obs_dict['oppAttackType_' + str(i) + '_' + value] = 0
        self.obs_dict = obs_dict
        observation = np.array([value for key,value in obs_dict.items()], dtype=np.float32)
        observation = np.clip(observation, 0, 1)
        # print("my State: {},opp State: {}".format(my.getState().name(), opp.getState().name()))
        # print("my Action: {}, opp Action: {}".format(my.getAction().name(), opp.getAction().name()))
        # # print(obs_dict)
        return observation

    def get_enough_energy_actions(self):
        self.my_actions_enough = {}
        self.opp_actions_enough = {}
        my = self.frameData.getCharacter(self.player)
        opp = self.frameData.getCharacter(not self.player)
        if str(my.getState().name()) == "AIR":
            my_actions = self.actions_air
        else:
            my_actions = self.actions_ground
        if str(opp.getState().name()) == "AIR":
            opp_actions = self.actions_air
        else:
            opp_actions = self.actions_ground

        my_motion_data = self.gameData.getMotionData(self.player)
        opp_motion_data = self.gameData.getMotionData(not self.player)
        my_motion_names = [motion.getActionName() for motion in my_motion_data]
        opp_motion_names = [motion.getActionName() for motion in opp_motion_data]
        for act in my_actions:
            if my_motion_data[my_motion_names.index(my_actions[act])].getAttackStartAddEnergy()+my.getEnergy() >= 0:
                self.my_actions_enough[act] = my_actions[act]
        for act in opp_actions:
            if my_motion_data[opp_motion_names.index(opp_actions[act])].getAttackStartAddEnergy()+opp.getEnergy() >= 0:
                self.opp_actions_enough[act] = opp_actions[act]

    # This part is mandatory
    class Java:
        implements = ["aiinterface.AIInterface"]
