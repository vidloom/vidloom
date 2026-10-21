import random
from typing import Dict, List

VIRAL_FACTS = [
    {
        "id": "space_1",
        "category": "SPACE FACTS",
        "title": "3 Terrifying Facts About Deep Space",
        "narration": "Here are three terrifying facts about deep space that will give you chills. Number one: in deep space, there is absolute silence. No matter how loud you scream, sound cannot travel through a vacuum, meaning you would perish in total stillness. Number two: rogue black holes are drifting through the dark galaxy right now at three million miles per hour, completely invisible until they swallow everything in their path. Number three: the universe is expanding faster than light. Eventually, every other galaxy will vanish forever, leaving our descendants completely alone in the pitch black cosmos."
    },
    {
        "id": "ocean_1",
        "category": "OCEAN FACTS",
        "title": "3 Creepy Facts About The Deep Ocean",
        "narration": "Here are three deeply unsettling ocean facts you probably never knew. Number one: more than eighty percent of the ocean remains completely unmapped and unexplored, meaning unknown creatures are living in total darkness beneath us right now. Number two: at the bottom of the Mariana Trench, the water pressure is equal to the weight of a thousand jumbo jets pressing on your chest. Number three: Point Nemo is the most isolated place on earth. You are literally closer to astronauts in space than to any living human on land."
    },
    {
        "id": "psychology_1",
        "category": "PSYCHOLOGY FACTS",
        "title": "3 Dark Psychology Facts About Human Minds",
        "narration": "Here are three dark psychology facts about how human minds really work. Number one: when someone is staring at your lips during a conversation, they are either deeply attracted to you, or they are intensely judging what you say. Number two: people who constantly point out small grammatical errors are scientifically proven to be less agreeable and more controlling. Number three: if you want to catch someone secretly watching you, yawn. Yawning is psychologically contagious, and if they yawn right after, they were staring at you."
    }
]

def get_random_fact() -> Dict:
    return random.choice(VIRAL_FACTS)
