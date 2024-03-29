""" Domus Continuous Action

"""

import numpy as np
import gymnasium as gym
from gymnasium import spaces  # error, spaces, utils

from .domus_env import BLOWER_ADD, BLOWER_MULT, DomusEnv
from .minmax import MinMaxTransform


class DomusContEnv(DomusEnv):
    metadata = {"render.modes": ["human"]}

    def __init__(
        self,
        **kwargs,
    ):
        """Description:
            Simulation of the thermal environment of a Fiat 500e car
            cabin.

        This modifies DomusEnv by making the action_space continuous

        """
        super().__init__(**kwargs)
        act_min = np.array(
            [
                5 * BLOWER_MULT + BLOWER_ADD,
                0,
                0,
                0,
                0,
                0,
                0,
            ],
            dtype=np.float32,
        )
        act_max = np.array(
            [
                18 * BLOWER_MULT + BLOWER_ADD,
                3000,
                6000,
                400,
                1,
                1,
                1,
            ],
            dtype=np.float32,
        )
        self.act_tr = MinMaxTransform(act_min, act_max)
        self.action_space = spaces.Box(
            high=1, low=-1, shape=act_min.shape, dtype=np.float32
        )

    def _convert_action(self, action: np.ndarray):
        """given some action, convert into SimpleHvac.Xt

        action is a ndarray

        """
        assert self.action_space.contains(
            action
        ), f"action {action} is not in the action_space {self.action_space}"

        c_x = self.act_tr.inverse_transform(action)

        return c_x
