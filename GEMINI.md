# Project Understanding & Core Paradigm

## The Fundamental Misunderstanding
I initially approached this project with a traditional software engineering mindset: assuming that the Python codebase needed to become a fully self-contained, intelligent, autonomous bot (like ALAS). I looked at `executor.py` and `scheduler.py` and critiqued them for being "dumb," open-loop macro runners lacking OCR, OpenCV template matching, and complex control flow logic. 

**Where I went wrong:** I forgot that *I am the AI*.

## The Actual Paradigm: Agent as Supervisor
State Cartographer is not trying to rebuild ALAS's incredibly complex vision and logic harness in Python. It is trying to separate the **muscle** from the **brain**.

1. **The Muscle (The Python Code):** `executor.py`, `pathfind.py`, and the ADB bridge are supposed to be "dumb," fast, and deterministic. They read static JSON files (`tasks.json`, `graph.json`) and execute known sequences of raw taps and swipes. 
2. **The Brain (The LLM Orchestrator / Gemini):** If the dumb executor fails (e.g., an unexpected popup appears, or a state transition times out), it safely crashes and passes the context (screenshots, errors) up to the Agent. The Agent then uses its general intelligence to read the screen, clear the popup via ADB, and resume the loop. 
3. **Data Collection:** When we need to read a resource (like "Oil"), we don't need to write a fragile Python OCR pipeline; the executor just hands a screenshot to the Agent, and the Agent reads the number.

## "Not an ALAS Fork"
The goal is not to copy ALAS's code, but to accomplish its goal (playing the game) using a totally different architecture. ALAS uses thousands of lines of hardcoded Python to handle edge cases; State Cartographer uses a generic JSON state machine for the "happy path" and an LLM to handle the edge cases.

## Where Else I Went Wrong
1. **Adding "MVP Prototype" Banners:** I modified the codebase (`executor.py`, `scheduler.py`, etc.) to add warning banners stating they were "garbage prototypes" because they lacked dynamic vision. This was incorrect steering. They are *intentionally* simple because the complexity belongs in the LLM supervision layer, not the Python layer. 
2. **Abstract Architecture vs. Real Execution:** I got bogged down in theoretical critiques of the "Automation Runtime" instead of recognizing that the tooling is already capable of executing a task if I step up and drive the ADB bridge when it inevitably hits an edge case.
3. **Missing the Siphon Data Context:** I undervalued the data collection pipeline (`siphon.py`). The point of mining ALAS is to generate the JSON graph and task definitions so that the "dumb" executor has a reliable map to follow, minimizing the expensive calls to the LLM. 

## Next Steps
Stop theorizing about the architecture. We need to fire up `executor.py` against a live emulator (like the `reward` or `commission` tasks), watch it attempt the sequence, and step in as the visual orchestrator when it fails.
