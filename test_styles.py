import asyncio
import os
import edge_tts
from edge_tts.communicate import Communicate
import edge_tts.communicate

# Custom mkssml that adds mstts namespace for speaking styles
def custom_mkssml(tc, text):
    if isinstance(text, bytes):
        text = text.decode('utf-8')
    return (
        "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' "
        "xmlns:mstts='https://www.w3.org/2001/mstts' xml:lang='en-US'>"
        f"<voice name='{tc.voice}'>"
        f"<prosody pitch='{tc.pitch}' rate='{tc.rate}' volume='{tc.volume}'>"
        f"{text}"
        "</prosody>"
        "</voice>"
        "</speak>"
    )

edge_tts.communicate.mkssml = custom_mkssml

styled_script = """
I thought I was completely alone in that basement.
<break time="300ms"/>
<mstts:express-as style="whispering">
The rain outside was relentless...
</mstts:express-as>
<break time="400ms"/>
<mstts:express-as style="terrified" styledegree="2">
Then the floorboards right above my head creaked! I held my breath. Don't move!
</mstts:express-as>
<break time="300ms"/>
<mstts:express-as style="whispering">
Whatever you do, do not make a sound. Slowly, I reached for the door handle. It was locked from the outside!
</mstts:express-as>
<break time="400ms"/>
<mstts:express-as style="terrified" styledegree="2">
Look behind you... right now!
</mstts:express-as>
"""

async def run():
    out_path = "output/showcase/davis_shocked_whisper.mp3"
    print("Synthesizing dramatic multi-style audio (terrified + whispering)...")
    comm = edge_tts.Communicate(styled_script, voice="en-US-DavisNeural")
    await comm.save(out_path)
    print(f"SUCCESS! Saved to {out_path}")
    
    # Also test GuyNeural with shouting / terrified
    out_path2 = "output/showcase/guy_shocked.mp3"
    comm2 = edge_tts.Communicate(styled_script, voice="en-US-GuyNeural")
    await comm2.save(out_path2)
    print(f"SUCCESS! Saved to {out_path2}")

if __name__ == "__main__":
    asyncio.run(run())
