"""Frozen original PocketEdge policy behind the official HTTP interface."""
import os
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import agent
import fallback_strategy
import uvicorn

agent.PARTICIPANT='PocketEdge reference'
agent.AGENT_NAME='PocketEdge v1'
agent.new_half=fallback_strategy.new_half
agent.choose_action=fallback_strategy.choose_action
agent.on_hand_end=fallback_strategy.on_hand_end

if __name__=='__main__':
    uvicorn.run(agent.app,host='0.0.0.0',port=int(os.environ.get('PORT','5009')),
                log_level='info',access_log=False)
