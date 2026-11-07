"""Offline Monte Carlo calibration; not run by the server or judge."""
import argparse
import json
from pathlib import Path
import random
import numpy as np

from native_engine import LIB, samples
from preflop import features


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--hands',type=int,default=5000)
    parser.add_argument('--samples',type=int,default=1024)
    args=parser.parse_args()
    if LIB is None:
        raise RuntimeError('Build the native engine first')
    rng=random.Random(148901)
    x,y=[],[]
    for i in range(args.hands):
        hand=tuple(sorted(rng.sample(range(36),5)))
        data=np.ctypeslib.as_array(samples(hand,(),args.samples,7919*i+1)).reshape(-1,4)
        x.append(features(hand))
        y.append(float(np.mean(data[:,0])))
        if i%500==0:
            print(f'Calibrated {i}/{args.hands}',flush=True)
    x,y=np.asarray(x),np.asarray(y)
    split=int(len(x)*0.8)
    ridge=np.eye(x.shape[1])*0.02
    ridge[0,0]=0
    coef=np.linalg.solve(x[:split].T@x[:split]+ridge,x[:split].T@y[:split])
    error=x[split:]@coef-y[split:]
    report={'training_hands':split,'heldout_hands':len(x)-split,'samples_per_hand':args.samples,
            'heldout_rmse':float(np.sqrt(np.mean(error**2))),
            'heldout_correlation':float(np.corrcoef(x[split:]@coef,y[split:])[0,1]),
            'seed':148901}
    # Refit all available training labels after the independent holdout audit.
    coef=np.linalg.solve(x.T@x+ridge,x.T@y)
    model=dict(coefficients=coef.tolist(),validation=report)
    Path('preflop-model.json').write_text(json.dumps(model,indent=2)+'\n')
    np.savez_compressed('optimization-results/preflop-training.npz',x=x,y=y)
    print(json.dumps(report),flush=True)


if __name__=='__main__':
    Path('optimization-results').mkdir(exist_ok=True)
    main()
