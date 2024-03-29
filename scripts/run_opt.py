import argparse
import warnings
from pathlib import Path

import gymnasium as gym
from skopt import dump, gp_minimize, load
from skopt.callbacks import CheckpointSaver
from skopt.space import Integer
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

import domus_gym
from domus_gym.envs import ENERGY_MAX, ENERGY_MIN, ENERGY_WEIGHT, Config, consumption
from domus_mlsim import load_scenarios

N_UCS = 28

model_cache = {}


class Loss:
    def __init__(
        self, envname: str, alg: str, log_path: str, run_number: str, timesteps=10000
    ):
        self.log_path = Path(log_path)
        assert self.log_path.exists()

        ppo_path = self.log_path / alg.lower() / (envname + "_" + run_number)
        assert ppo_path.exists(), f"path {ppo_path} doesn't exist"
        self.alg = alg
        self.envname = envname
        self.model_file = ppo_path / (envname + ".zip")
        self.vecnormalize = ppo_path / envname / "vecnormalize.pkl"
        self.sc = load_scenarios()
        self.timesteps = timesteps

    def __call__(self, hyperparams):

        configset = set([cfg for cfg, p in zip(Config, hyperparams) if p == 1])
        env = DummyVecEnv(
            [
                lambda: gym.make(
                    self.envname, use_random_scenario=True, configuration=configset
                )
            ]
        )
        env = VecNormalize.load(self.vecnormalize, env)
        env.training = True
        if str(hyperparams) in model_cache:
            # use model from cache
            model = model_cache[str(hyperparams)]
        else:
            model = PPO.load(self.model_file, env=env)
        try:
            model.learn(total_timesteps=self.timesteps)
        finally:
            model.env.close()
        # need to return negative (since this is loss not reward)
        loss = -self.summarise(model)

        # calculate loss associated with configuration

        loss += self.configuration_loss(configset)
        model_cache[str(hyperparams)] = model
        return loss

    def configuration_loss(self, configset):
        mass = 0
        if Config.radiant in configset:
            mass += 1.5

        if Config.seat in configset:
            mass += 1.1

        p = sum(
            [
                consumption.power_delta(self.sc.car_speed[i], 1300, mass)
                * self.sc.time[i]
                for i in range(1, 29)
            ]
        ) / sum(self.sc.time)
        return p / (ENERGY_MAX - ENERGY_MIN) * ENERGY_WEIGHT

    def summarise(self, model):

        total_sum = 0
        env = DummyVecEnv(
            [
                lambda: gym.make(
                    self.envname,
                    use_scenario=1,
                    fixed_episode_length=self.sc.time[1] * 60,
                )
            ]
        )
        env = VecNormalize.load(self.vecnormalize, env)
        env.training = False
        env.norm_reward = False
        model.env = env
        for i in range(1, N_UCS + 1):
            env.set_attr("use_scenario", i)
            env.set_attr("fixed_episode_length", self.sc.time[i] * 60)

            obs, _ = env.reset()

            done = False
            count = 0
            total = 0

            while not done:
                action, state = model.predict(obs)
                obs, reward, done, infos = env.step(action)
                total += reward[0]
                count += 1
            total_sum += total / count

        return total_sum / N_UCS


def optimise(
    outputfile,
    checkpointfile,
    env,
    algo,
    log_path,
    run_number,
    restart=False,
    n_calls=100,
    timesteps=10000,
):
    search_space = [
        Integer(0, 1),  # radiant
        Integer(0, 1),  # seat
        Integer(0, 1),  # windowheating
        Integer(0, 1),  # newairmode
    ]
    loss_fn = Loss(
        envname=env,
        alg=algo,
        log_path=log_path,
        run_number=run_number,
        timesteps=timesteps,
    )
    checkpoint_saver = CheckpointSaver(checkpointfile, compress=9)
    if restart:
        result = load(checkpointfile)

        result = gp_minimize(
            loss_fn,
            dimensions=search_space,
            # noise=1e-10,
            acq_func="EI",
            n_calls=n_calls,
            n_jobs=-1,
            callback=[checkpoint_saver],
            verbose=True,
            x0=result.x_iters,
            y0=result.func_vals,
        )
    else:
        result = gp_minimize(
            loss_fn,
            dimensions=search_space,
            # noise=1e-10,
            acq_func="EI",
            n_calls=n_calls,
            n_jobs=-1,
            callback=[checkpoint_saver],
            verbose=True,
        )
    print(f"optimisation results: {result.x} -> {result.fun}")
    print(f"writing results to {outputfile}")
    dump(result, outputfile, compress=9)


def main():
    parser = argparse.ArgumentParser(description="run wp2.3 optimisation")

    parser.add_argument(
        "-a", "--algo", help="algorithm to use for learning controller", type=str
    )
    parser.add_argument("-e", "--env", help="Environment", type=str)
    parser.add_argument(
        "-r", "--run-number", help="Suffix on environment for run", type=str
    )
    parser.add_argument(
        "-t", "--timesteps", help="Number of timesteps to run", type=int
    )

    parser.add_argument(
        "-f", "--exp-folder", help="Folder containing learned model", type=str
    )
    parser.add_argument(
        "-c",
        "--checkpoint",
        help="where to write checkpoint to or take checkpoint from",
        type=str,
    )
    parser.add_argument("-x", "--restart", action="store_true")

    parser.add_argument(
        "outputfile",
        help="where to write results",
        type=str,
    )

    args = parser.parse_args()
    #    args.algo = args.algo.upper()

    optimise(
        args.outputfile,
        args.checkpoint,
        env=args.env,
        algo=args.algo,
        log_path=args.exp_folder,
        run_number=args.run_number,
        restart=args.restart,
        timesteps=args.timesteps,
    )


if __name__ == "__main__":
    warnings.simplefilter("ignore")
    main()
