"""Make one mp3 per slide from the speaker notes in SW7_Talking_Points.md, with a US English neural voice."""
import asyncio, re, sys, os
import edge_tts

MD, OUT = sys.argv[1], sys.argv[2]
VOICE = "en-US-AndrewNeural"
text = open(MD, encoding="utf-8").read()
parts = re.split(r"^## Slide (\d+): .*$", text, flags=re.M)
notes = {int(parts[i]): parts[i + 1].strip() for i in range(1, len(parts), 2)}


def speakable(t):
    t = t.replace("a w,", "a-w,").replace("RQ", "R Q ")
    t = t.replace("tuksense.site", "tuksense dot site")
    return t


async def main():
    os.makedirs(OUT, exist_ok=True)
    for n, t in sorted(notes.items()):
        dst = os.path.join(OUT, f"a{n:02d}.mp3")
        if os.path.exists(dst) and os.path.getsize(dst) > 10000:
            continue
        for attempt in range(5):
            try:
                await edge_tts.Communicate(speakable(t), VOICE, rate="+0%").save(dst)
                break
            except Exception as e:
                print(n, "retry", attempt, type(e).__name__)
                await asyncio.sleep(3)
        print(n, len(t.split()))

asyncio.run(main())
