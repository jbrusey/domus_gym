from domus_gym.envs import DomusContEnv
from domus_mlsim import SimpleHvac


def test_domus_cont_env():
    env = DomusContEnv()

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


def test_domus_cont_args():
    env = DomusContEnv(use_random_scenario=True)
    assert env.use_random_scenario
    env = DomusContEnv(use_scenario=1)
    assert env.use_scenario == 1
    env = DomusContEnv(fixed_episode_length=100)
    assert env.fixed_episode_length == 100
