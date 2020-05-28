import numpy as np
from py4j.java_gateway import get_field


class GymAI(object):
    def __init__(self, gateway, pipe, frameskip=True):
        self.gateway = gateway
        self.pipe = pipe

        self.width = 96  # The width of the display to obtain
        self.height = 64  # The height of the display to obtain
        self.grayscale = True  # The display's color to obtain true for grayscale, false for RGB

        self.obs = None
        self.just_inited = True

        self._actions = "AIR AIR_A AIR_B AIR_D_DB_BA AIR_D_DB_BB AIR_D_DF_FA AIR_D_DF_FB AIR_DA AIR_DB AIR_F_D_DFA AIR_F_D_DFB AIR_FA AIR_FB AIR_GUARD AIR_GUARD_RECOV AIR_RECOV AIR_UA AIR_UB BACK_JUMP BACK_STEP CHANGE_DOWN CROUCH CROUCH_A CROUCH_B CROUCH_FA CROUCH_FB CROUCH_GUARD CROUCH_GUARD_RECOV CROUCH_RECOV DASH DOWN FOR_JUMP FORWARD_WALK JUMP LANDING NEUTRAL RISE STAND STAND_A STAND_B STAND_D_DB_BA STAND_D_DB_BB STAND_D_DF_FA STAND_D_DF_FB STAND_D_DF_FC STAND_F_D_DFA STAND_F_D_DFB STAND_FA STAND_FB STAND_GUARD STAND_GUARD_RECOV STAND_RECOV THROW_A THROW_B THROW_HIT THROW_SUFFER"
        self.action_strs = self._actions.split(" ")

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

        return 0

    # please define this method when you use FightingICE version 3.20 or later
    def roundEnd(self, x, y, z):
        print("send round end to {}".format(self.pipe))
        self.pipe.send([self.obs, 0, True, None])
        self.just_inited = True
        # request = self.pipe.recv()
        # if request == "close":
        #     return
        self.obs = None

    # Please define this method when you use FightingICE version 4.00 or later
    def getScreenData(self, sd):
        self.screenData = sd

    def getInformation(self, frameData, isControl):
        self.pre_framedata = frameData if self.pre_framedata is None else self.frameData
        self.frameData = frameData
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

            self.inputKey.empty()
            self.cc.skillCancel()

        # if just inited, should wait for first reset()
        if self.just_inited:
            request = self.pipe.recv()
            if request == "reset":
                self.just_inited = False
                self.obs = self.get_obs()
                self.pipe.send(self.obs)
            else:
                raise ValueError
        # if not just inited but self.obs is none, it means second/thrid round just started
        # should return only obs for reset()
        elif self.obs is None:
            self.obs = self.get_obs()
            self.pipe.send(self.obs)
        # if there is self.obs, do step() and return [obs, reward, done, info]
        else:
            self.obs = self.get_obs()
            self.reward = self.get_reward()
            self.pipe.send([self.obs, self.reward, False, None])

        #print("waitting for step in {}".format(self.pipe))
        request = self.pipe.recv()
        #print("get step in {}".format(self.pipe))
        if len(request) == 2 and request[0] == "step":
            action = request[1]
            self.cc.commandCall(self.action_strs[action])
            if not self.frameskip:
                self.inputKey = self.cc.getSkillKey()

    def get_reward(self):
        try:
            if self.pre_framedata.getEmptyFlag() or self.frameData.getEmptyFlag():
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
                    reward = (p2_hp_pre-p2_hp_now) - (p1_hp_pre-p1_hp_now) \
                             + (p1_hit_count_now - p2_hit_count_now) - (frame_num_now - frame_num_pre) / 60
                else:
                    reward = (p1_hp_pre-p1_hp_now) - (p2_hp_pre-p2_hp_now) \
                             + (p2_hit_count_now - p1_hit_count_now) - (frame_num_now - frame_num_pre) / 60
        except:
            reward = 0
        return reward

    def get_obs(self):
        my = self.frameData.getCharacter(self.player)
        opp = self.frameData.getCharacter(not self.player)

        # my information
        myHp = abs(my.getHp() / 400)
        myEnergy = my.getEnergy() / 300
        myLeft = my.getLeft() / 960
        myRight = my.getRight() / 960
        myBottom = my.getBottom() / 640
        myTop = my.getTop() / 640
        mySpeedXAbs = abs(my.getSpeedX() / 15)
        mySpeedXDirection = 0 if my.getSpeedX() < 0 else 1
        mySpeedYAbs = abs(my.getSpeedY() / 28)
        mySpeedYDirection = 0 if my.getSpeedY() < 0 else 1
        myHitCount = my.getHitCount() / 20
        myisHitConfirm = 1 if my.isHitConfirm() else 0
        myisControl = 1 if my.isControl() else 0
        myRemainingFrame = my.getRemainingFrame() / 70
        myState = my.getState().ordinal()
        myAction = my.getAction().ordinal()

        # opp information
        oppHp = abs(opp.getHp() / 400)
        oppEnergy = opp.getEnergy() / 300
        oppLeft = opp.getLeft() / 960
        oppRight = opp.getRight() / 960
        oppBottom = opp.getBottom() / 640
        oppTop = opp.getTop() / 640
        oppSpeedXAbs = abs(opp.getSpeedX() / 15)
        oppSpeedXDirection = 0 if opp.getSpeedX() < 0 else 1
        oppSpeedYAbs = abs(opp.getSpeedY() / 28)
        oppSpeedYDirection = 0 if opp.getSpeedY() < 0 else 1
        oppHitCount = opp.getHitCount() / 20
        oppisHitConfirm = 1 if opp.isHitConfirm() else 0
        oppisControl = 1 if opp.isControl() else 0
        oppRemainingFrame = opp.getRemainingFrame() / 70
        oppState = opp.getState().ordinal()
        oppAction = opp.getAction().ordinal()

        # time information
        game_frame_num = self.frameData.getFramesNumber() / 3600

        observation = []

        # my information
        observation += [myHp,
                        myEnergy,
                        myLeft,
                        myRight,
                        myBottom,
                        myTop,
                        mySpeedXDirection,
                        mySpeedYDirection,
                        mySpeedXAbs,
                        mySpeedYAbs,
                        myHitCount,
                        myisHitConfirm,
                        myisControl,
                        myRemainingFrame,]
        for i in range(4):
            if i == myState:
                observation.append(1)
            else:
                observation.append(0)
        for i in range(56):
            if i == myAction:
                observation.append(1)
            else:
                observation.append(0)


        # opp information
        observation += [oppHp,
                        oppEnergy,
                        oppLeft,
                        oppRight,
                        oppBottom,
                        oppTop,
                        oppSpeedXDirection,
                        oppSpeedYDirection,
                        oppSpeedXAbs,
                        oppSpeedYAbs,
                        oppHitCount,
                        oppisHitConfirm,
                        oppisControl,
                        oppRemainingFrame, ]
        for i in range(4):
            if i == oppState:
                observation.append(1)
            else:
                observation.append(0)
        for i in range(56):
            if i == oppAction:
                observation.append(1)
            else:
                observation.append(0)

        # time information
        observation.append(game_frame_num)

        myProjectiles = self.frameData.getProjectilesByP1()
        oppProjectiles = self.frameData.getProjectilesByP2()

        # should be the maximum projectile a character can own at same time, not sure is 2, originally is 2
        for i in range(2):
            if i < len(myProjectiles):
                myHitDamage = myProjectiles[i].getHitDamage() / 400.0
                myGuardDamage = myProjectiles[i].getGuardDamage() / 400.0
                myStartAddEnergy = myProjectiles[i].getStartAddEnergy() / 300.0
                myHitAddEnergy = myProjectiles[i].getHitAddEnergy() / 300.0
                myGuardAddEnergy = myProjectiles[i].getGuardAddEnergy() / 300.0
                myGiveEnergy = myProjectiles[i].getGiveEnergy() / 300.0
                myDownProp = 1 if myProjectiles[i].isDownProp() else 0
                myIsProjectile = 1 if myProjectiles[i].isProjectile() else 0
                myHitSpeedXAbs = abs(myProjectiles[i].getSpeedX() / 15.0)
                myHitSpeedXDirection = 0 if myProjectiles[i].getSpeedX() < 0 else 1
                myHitSpeedYAbs = abs(myProjectiles[i].getSpeedY() / 28.0)
                myHitSpeedYDirection = 0 if myProjectiles[i].getSpeedY() < 0 else 1
                myHitAreaNowLeft = myProjectiles[i].getCurrentHitArea().getLeft() / 960.0
                myHitAreaNowRight = myProjectiles[i].getCurrentHitArea().getRight() / 960.0
                myHitAreaNowTop = myProjectiles[i].getCurrentHitArea().getTop() / 640.0
                myHitAreaNowBottom = myProjectiles[i].getCurrentHitArea().getBottom() / 640.0
                myImpactX = myProjectiles[i].getImpactX() / 960.0
                myImpactY = myProjectiles[i].getImpactY() / 640.0
                myStartUp = myProjectiles[i].getGiveEnergy() / 70
                myActive = myProjectiles[i].getGiveEnergy() / 70
                myGiveGuardRecov = myProjectiles[i].getGiveGuardRecov / 70
                myAttackType = myProjectiles[i].getAttackType()
                observation += [myHitDamage,
                                myGuardDamage,
                                myStartAddEnergy,
                                myHitAddEnergy,
                                myGuardAddEnergy,
                                myGiveEnergy,
                                myDownProp,
                                myIsProjectile,
                                myHitSpeedXAbs,
                                myHitSpeedXDirection,
                                myHitSpeedYAbs,
                                myHitSpeedYDirection,
                                myHitAreaNowLeft,
                                myHitAreaNowRight,
                                myHitAreaNowTop,
                                myHitAreaNowBottom,
                                myImpactX,
                                myImpactY,
                                myStartUp,
                                myActive,
                                myGiveGuardRecov, ]
                for j in range(4):
                    if j == myAttackType:
                        observation.append(1)
                    else:
                        observation.append(0)
            else:
                for t in range(25):
                    observation.append(0.0)

            if i < len(oppProjectiles):
                oppHitDamage = oppProjectiles[i].getHitDamage() / 400.0
                oppGuardDamage = oppProjectiles[i].getGuardDamage() / 400.0
                oppStartAddEnergy = oppProjectiles[i].getStartAddEnergy() / 300.0
                oppHitAddEnergy = oppProjectiles[i].getHitAddEnergy() / 300.0
                oppGuardAddEnergy = oppProjectiles[i].getGuardAddEnergy() / 300.0
                oppGiveEnergy = oppProjectiles[i].getGiveEnergy() / 300.0
                oppDownProp = 1 if oppProjectiles[i].isDownProp() else 0
                oppIsProjectile = 1 if oppProjectiles[i].isProjectile() else 0
                oppHitSpeedXAbs = abs(oppProjectiles[i].getSpeedX() / 15.0)
                oppHitSpeedXDirection = 0 if oppProjectiles[i].getSpeedX() < 0 else 1
                oppHitSpeedYAbs = abs(oppProjectiles[i].getSpeedY() / 28.0)
                oppHitSpeedYDirection = 0 if oppProjectiles[i].getSpeedY() < 0 else 1
                oppHitAreaNowLeft = oppProjectiles[i].getCurrentHitArea().getLeft() / 960.0
                oppHitAreaNowRight = oppProjectiles[i].getCurrentHitArea().getRight() / 960.0
                oppHitAreaNowTop = oppProjectiles[i].getCurrentHitArea().getTop() / 640.0
                oppHitAreaNowBottom = oppProjectiles[i].getCurrentHitArea().getBottom() / 640.0
                oppImpactX = oppProjectiles[i].getImpactX() / 960.0
                oppImpactY = oppProjectiles[i].getImpactY() / 640.0
                oppStartUp = oppProjectiles[i].getGiveEnergy() / 70
                oppActive = oppProjectiles[i].getGiveEnergy() / 70
                oppGiveGuardRecov = oppProjectiles[i].getGiveGuardRecov / 70
                oppAttackType = oppProjectiles[i].getAttackType()
                observation += [oppHitDamage,
                                oppGuardDamage,
                                oppStartAddEnergy,
                                oppHitAddEnergy,
                                oppGuardAddEnergy,
                                oppGiveEnergy,
                                oppDownProp,
                                oppIsProjectile,
                                oppHitSpeedXAbs,
                                oppHitSpeedXDirection,
                                oppHitSpeedYAbs,
                                oppHitSpeedYDirection,
                                oppHitAreaNowLeft,
                                oppHitAreaNowRight,
                                oppHitAreaNowTop,
                                oppHitAreaNowBottom,
                                oppImpactX,
                                oppImpactY,
                                oppStartUp,
                                oppActive,
                                oppGiveGuardRecov, ]
                for j in range(4):
                    if j == oppAttackType:
                        observation.append(1)
                    else:
                        observation.append(0)
            else:
                for t in range(25):
                    observation.append(0.0)

        observation = np.array(observation, dtype=np.float32)
        observation = np.clip(observation, 0, 1)
        return observation

    # This part is mandatory
    class Java:
        implements = ["aiinterface.AIInterface"]
