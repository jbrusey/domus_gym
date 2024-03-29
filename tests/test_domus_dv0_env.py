import numpy as np

from numpy.testing import assert_array_almost_equal_nulp
from domus_gym.envs import DomusDv0ContEnv
from domus_mlsim import (
    KELVIN,
    SimpleHvac,
    load_dv0,
    load_hvac,
    load_scenarios,
    run_dv0_sim,
)


def test_domus_dv0_env():
    env = DomusDv0ContEnv()

    # can we sample the observation space?
    s = env.observation_space.sample()
    assert s is not None
    a = env.action_space.sample()
    assert a is not None

    ctrl = SimpleHvac()
    s, _ = env.reset()
    for _ in range(100):
        a = ctrl.step(env.hvac_action(s))

        act = env.act_tr.transform(a)

        assert env.action_space.contains(act)
        s, rew, terminated, truncated, kw = env.step(act)
        if not (terminated or truncated):
            assert env.observation_space.contains(s)
        else:
            s, _ = env.reset()


def test_domus_dv0_args():
    env = DomusDv0ContEnv(use_random_scenario=True)
    assert env.use_random_scenario
    env = DomusDv0ContEnv(use_scenario=1)
    assert env.use_scenario == 1
    env = DomusDv0ContEnv(fixed_episode_length=100)
    assert env.fixed_episode_length == 100


def test_domus_dv0_like_base():
    episode_len = 100
    scenarios = load_scenarios()
    sc30 = scenarios.loc[30]
    cabin, hvac, ctrl = run_dv0_sim(
        load_dv0(),
        load_hvac(),
        SimpleHvac(),
        setpoint=KELVIN + 22,
        n=episode_len,
        ambient_t=sc30.ambient_t,
        ambient_rh=sc30.ambient_rh,
        cabin_t=sc30.cabin_t,
        cabin_v=sc30.cabin_v,
        cabin_rh=sc30.cabin_rh,
        solar1=sc30.solar1,
        solar2=sc30.solar2,
        car_speed=sc30.car_speed,
    )
    assert ctrl.dtype == np.float32

    env = DomusDv0ContEnv(use_scenario=30, fixed_episode_length=episode_len)
    controller = SimpleHvac()
    s, _ = env.reset()
    assert env.observation_space.contains(s)
    i = 0
    while True:
        a = controller.step(env.hvac_action(s))

        act = env.act_tr.transform(a)

        assert_array_almost_equal_nulp(ctrl[i], a, nulp=100)

        i += 1

        assert env.action_space.contains(act)
        s, rew, terminated, truncated, kw = env.step(act)
        if not (terminated or truncated):
            print(i)
            assert env.observation_space.contains(s)
        else:
            break
            # s, _ = env.reset()
