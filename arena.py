"""Reproducible in-process duplicate matches for strategy development.

Unlike verify_solution.py this measures strategy CPU time without HTTP.
Official HTTP validation is still required for the eight-second bank.
"""
import argparse
import json
from pathlib import Path
import random
import statistics
import time

import strategy
import fallback_strategy
from game import Action, AgentConfig, Game, make_deal

ROOT = Path(__file__).resolve().parent


def legacy():
    return fallback_strategy


class Opponent:
    def __init__(self, style):
        self.style=style

    def new_half(self,config,memory):
        strategy.new_half(config,memory)
        memory['rng']=random.Random(917)

    def on_hand_end(self,result,memory):
        strategy.on_hand_end(result,memory)

    def choose_action(self,obs,memory):
        if self.style=='random':
            return memory['rng'].choice(obs.legal_actions)
        if self.style=='station':
            return Action.CHECK_CALL
        if self.style=='pot':
            return Action.RAISE_POT if Action.RAISE_POT in obs.legal_actions else Action.CHECK_CALL
        if not obs.board:
            eq=strategy.preflop_strength(obs.hole_cards)
        else:
            eq=strategy.distribution(obs,memory)['uniform']
        odds=obs.to_call/max(1,obs.pot+obs.to_call)
        threshold={'equity':0.62,'tight':0.72,'pressure':0.52}[self.style]
        call_floor={'equity':0.02,'tight':0.12,'pressure':0.0}[self.style]
        if obs.to_call and eq<odds+call_floor:
            return Action.FOLD
        if eq>threshold and Action.RAISE_POT in obs.legal_actions:
            return Action.RAISE_POT
        if self.style=='pressure' and not obs.to_call and memory['rng'].random()<0.15 and Action.RAISE_HALF in obs.legal_actions:
            return Action.RAISE_HALF
        return Action.CHECK_CALL


def match(opponent, seed, deals):
    config=AgentConfig(num_hands=deals)
    modules=[strategy,legacy() if opponent=='v1' else Opponent(opponent)]
    paired=[0.0]*deals
    timing=[0.0,0.0]
    counts=[0,0]
    for half in (0,1):
        memories=[{},{}]
        for module,memory in zip(modules,memories):
            module.new_half(config,memory)
        for i in range(deals):
            game=Game(make_deal(seed,i),button_seat=i%2,hand_index=i)
            while not game.is_terminal:
                seat=game.to_act
                player=seat^half
                obs=game.observation(seat)
                start=time.perf_counter()
                action=modules[player].choose_action(obs,memories[player])
                timing[player]+=time.perf_counter()-start
                counts[player]+=1
                if action not in obs.legal_actions:
                    raise AssertionError((opponent,i,action,obs.legal_actions))
                game.apply(action)
            paired[i]+=game.hand_result(half).my_net/config.big_blind
            for player in (0,1):
                modules[player].on_hand_end(game.hand_result(player^half),memories[player])
    mean=statistics.mean(paired)
    se=statistics.stdev(paired)/(deals**0.5)
    return dict(opponent=opponent,seed=seed,deals=deals,mean_bb_per_deal=mean,
                ci95=[mean-1.96*se,mean+1.96*se],compute_seconds=timing,decisions=counts)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--opponents',nargs='+',default=['v1','equity','tight','pressure'])
    parser.add_argument('--seeds',nargs='+',default=['1009','2027'])
    parser.add_argument('--deals',type=int,default=1000)
    parser.add_argument('--output',default='optimization-results/arena.json')
    args=parser.parse_args()
    results=[]
    path=ROOT/args.output
    path.parent.mkdir(exist_ok=True,parents=True)
    for opponent in args.opponents:
        for seed in args.seeds:
            result=match(opponent,seed,args.deals)
            results.append(result)
            path.write_text(json.dumps(results,indent=2)+'\n')
            print(json.dumps(result),flush=True)


if __name__=='__main__':
    main()
