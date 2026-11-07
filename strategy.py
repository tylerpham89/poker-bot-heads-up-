"""PocketEdge v2: native equity, learned preflop strength and action ranges."""
from bisect import bisect_left, bisect_right
import time
import numpy as np

from game import Action, Street
from native_engine import samples, LIB
from preflop import strength as preflop_strength
from fallback_strategy import BITS, board_masks, score_masks
from fallback_strategy import estimate as fallback_estimate


def new_half(config, memory):
    memory.update(hands_played=0, opp_actions=0, opp_raises=0, opp_folds=0,
        hand=-1, seen_history=0, compute_used=0.0, num_hands=config.num_hands,
        compute_budget=min(1.5, config.time_bank_seconds*0.20),
        actions=[0]*4, raises=[0]*4, faced=0, called=0, folded=0,
        showdown_bets=0, showdown_bluffs=0, decisions=0)


def percentile(values):
    # Midranks assign identical hands identical likelihoods.
    ordered=np.sort(values)
    return (np.searchsorted(ordered, values, side="left") +
            np.searchsorted(ordered, values, side="right")) / (2*len(values))


def distribution(obs, memory):
    key = (obs.hand_index, obs.hole_cards, obs.board)
    if memory.get("equity_key_v2") == key:
        return memory["distribution"]
    seed = sum(BITS[c] for c in obs.hole_cards + obs.board) ^ (obs.hand_index*1000003)
    n = (320, 448, 1024)[len(obs.board)-3]
    allowance = memory.get("compute_budget", 1.5)*(obs.hand_index+25)/max(1,memory.get("num_hands",1000))
    if memory.get("compute_used",0) > allowance:
        n = max(96,n//2)
    raw = samples(obs.hole_cards, obs.board, n, seed)
    if raw is None:
        a,b = fallback_estimate(obs,memory)
        record = dict(uniform=a,tight=b,raw=None)
    else:
        data = np.ctypeslib.as_array(raw).reshape(n,4).copy()
        q = percentile(data[:,1])
        fq = q if len(obs.board)==3 else percentile(data[:,2])
        uniform = float(np.mean(data[:,0]))
        w = 0.1 + q**3
        tight = float(np.dot(data[:,0],w)/w.sum())
        record = dict(uniform=uniform,tight=tight,raw=data,q=q,fq=fq)
    memory["equity_key_v2"], memory["distribution"] = key,record
    return record


def estimate(obs,memory):
    d = distribution(obs,memory)
    return d["uniform"],d["tight"]


def _observe(obs,memory):
    if memory.get("hand") != obs.hand_index:
        memory["hand"],memory["seen_history"] = obs.hand_index,0
    for i,event in enumerate(obs.action_history[memory.get("seen_history",0):],memory.get("seen_history",0)):
        if event.is_me:
            continue
        s = int(event.street)
        memory["opp_actions"] += 1
        memory["actions"][s] += 1
        if event.action in (Action.RAISE_HALF,Action.RAISE_POT):
            memory["opp_raises"] += 1
            memory["raises"][s] += 1
        if i:
            prev=obs.action_history[i-1]
            if prev.is_me and prev.street==event.street and prev.action in (Action.RAISE_HALF,Action.RAISE_POT):
                memory["faced"] += 1
                if event.action==Action.CHECK_CALL:
                    memory["called"] += 1
    memory["seen_history"] = len(obs.action_history)
    memory["last_obs"] = obs


def bet_frequency(memory,street):
    return (memory["raises"][int(street)]+3)/(memory["actions"][int(street)]+9)


def _range_equities(obs,memory,record):
    if record["raw"] is None:
        f=bet_frequency(memory,obs.street)
        mix=max(0.0,0.85-1.5*f) if obs.to_call else 0.0
        eq=record["uniform"]*(1-mix)+record["tight"]*mix
        return eq,record["tight"],0.35
    data=record["raw"]
    w=np.ones(len(data))
    # Infer ranges from the whole visible betting history, including earlier
    # streets. A turn/river bet does not erase evidence from the flop.
    for s in range(int(obs.street)+1):
        events=[e for e in obs.action_history if not e.is_me and int(e.street)==s
                and e.action in (Action.RAISE_HALF,Action.RAISE_POT)]
        if not events:
            continue
        freq=bet_frequency(memory,s)
        if s==0:
            q=percentile(data[:,3])
        elif s==int(obs.street):
            q=record["q"]
        elif s==1:
            q=record["fq"]
        else:
            continue  # no invented strength for an unavailable earlier turn
        # Wide raisers remain wide. The bluff floor prevents interpreting every
        # bet as a made hand, even before enough showdowns have been observed.
        value=np.clip((q-(1-freq-0.18))/0.36,0,1)
        bluff=(memory["showdown_bluffs"]+2)/(memory["showdown_bets"]+18)
        bluff=min(0.30,max(0.05,bluff))
        likelihood=bluff+(1-bluff)*value
        if freq>0.75:
            likelihood=0.75+0.25*value
        w*=likelihood**min(2,len(events))
    equity=float(np.dot(w,data[:,0])/w.sum())
    fold_rate=(memory["folded"]+4)/(memory["folded"]+memory["faced"]+12)
    # Approximate how the range is selected when facing our next value bet.
    continuation=np.clip((record["q"]-(fold_rate-0.15))/0.30,0.06,1)
    cw=w*continuation
    calling=float(np.dot(cw,data[:,0])/cw.sum())
    return equity,calling,fold_rate


def choose_action(obs,memory):
    start=time.perf_counter()
    try:
        _observe(obs,memory)
        action=_choose(obs,memory)
        if action not in obs.legal_actions:
            action=Action.CHECK_CALL if Action.CHECK_CALL in obs.legal_actions else obs.legal_actions[0]
        memory["last_action"]=action
        memory["decisions"] += 1
        return action
    finally:
        memory["compute_used"]=memory.get("compute_used",0)+time.perf_counter()-start


def _choose(obs,memory):
    legal=obs.legal_actions
    call=Action.CHECK_CALL
    fold=Action.FOLD if Action.FOLD in legal else call
    odds=min(obs.to_call,obs.my_stack)/max(1,obs.pot+min(obs.to_call,obs.my_stack))
    freq=bet_frequency(memory,obs.street)
    if obs.street==Street.PREFLOP:
        if memory.get("preflop_hole")!=obs.hole_cards:
            memory["preflop_hole"]=obs.hole_cards
            memory["preflop_equity"]=preflop_strength(obs.hole_cards)
        eq=memory["preflop_equity"]
        # Equities are trained against random PLO5 hands, not arbitrary scores.
        # Position and the size of the commitment determine how much to defend.
        pressure=obs.raises_this_street
        if obs.to_call<=obs.big_blind and pressure==0:
            threshold=0.49 if obs.is_button else 0.54
            if eq>threshold and Action.RAISE_POT in legal:
                return Action.RAISE_POT
            return call
        penalty=max(0,0.50-freq)*0.13+max(0,pressure-1)*0.015
        # Once most of a stack is committed, use actual pot odds, rather than
        # folding due only to the number of previous raises.
        threshold=max(odds+0.035,0.425+penalty)
        if eq<threshold:
            return fold
        if eq>0.575+penalty and Action.RAISE_POT in legal:
            return Action.RAISE_POT
        return call
    record=distribution(obs,memory)
    eq,calling,fold_rate=_range_equities(obs,memory,record)
    margin=(0.035,0.015,0.0)[int(obs.street)-1]
    if obs.opp_stack==0:
        margin=0.0
    if obs.to_call and eq<odds+margin:
        return fold
    # Avoid thin raises into a range that only continues with better hands.
    threshold=0.57 if obs.to_call else 0.53
    if calling>threshold and eq>0.53:
        desired=Action.RAISE_POT if calling>0.68 or obs.street!=Street.RIVER else Action.RAISE_HALF
        if desired in legal:
            return desired
    # Balanced small river bluffs against opponents who actually fold bets.
    if not obs.to_call and obs.street==Street.RIVER and eq<0.35 and fold_rate>0.43:
        token=(sum(BITS[c] for c in obs.hole_cards)*2654435761+obs.hand_index)%100
        if token<18 and Action.RAISE_HALF in legal:
            return Action.RAISE_HALF
    return call


def on_hand_end(result,memory):
    memory["hands_played"]=memory.get("hands_played",0)+1
    obs=memory.get("last_obs")
    if not result.went_to_showdown and result.winner=="me":
        memory["opp_folds"] += 1
        if obs is not None and obs.hand_index==result.hand_index and memory.get("last_action") in (Action.RAISE_HALF,Action.RAISE_POT):
            memory["folded"] += 1
    if result.opp_hole and obs is not None and obs.hand_index==result.hand_index and len(obs.board)>=3:
        record=memory.get("distribution")
        if record and record["raw"] is not None and any(not e.is_me and e.street==obs.street and e.action in (Action.RAISE_HALF,Action.RAISE_POT) for e in obs.action_history):
            from native_engine import evaluate
            score=evaluate(result.opp_hole,obs.board)
            percentile=float(np.mean(record["raw"][:,1]<score))
            memory["showdown_bets"] += 1
            memory["showdown_bluffs"] += percentile<0.5
