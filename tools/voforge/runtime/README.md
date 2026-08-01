# voforge runtime consumers

Drop-in players for a voforge pack. All three compute the identical
content-address hash (djb2 over UTF-8 of `who|text`), so they find lines with
no manifest; a missing file is the fallback signal.

| File | Platform | Status |
|---|---|---|
| `voforge.js` | Browser / Web (ES module, WebAudio) | tested — this is what VENTFALL's pattern is based on |
| `VoForge.cs` | Unity (any 5.3+) | reference implementation — hash verified against Python, playback path untested in-engine |
| `voforge.gd` | Godot 4 | reference implementation — hash verified against Python, playback path untested in-engine |

## Web

```js
import { VoPlayer } from "./voforge.js";

const vo = new VoPlayer({
  base: "vo/",
  fallback: (who, text) => speechSynthesis.speak(new SpeechSynthesisUtterance(text)),
});
await vo.say("voss", "Four drones and a rig older than I am.");
vo.preload("krane", "The quota stands.");   // warm the next line
vo.stop();                                   // player advanced the scene
```

Pass `ctx`/`output` to route through your game's existing AudioContext and
master gain (for ducking, mute, etc.).

## Unity

```csharp
string url = System.IO.Path.Combine(Application.streamingAssetsPath,
                                    VoForge.Path("vo", "voss", line));
StartCoroutine(VoForge.Play(this, audioSource, url,
               onMissing: () => Debug.Log("no VO, use subtitle only")));
```

## Godot

```gdscript
var vo := VoForge.new()
add_child(vo)
vo.line_missing.connect(func(who, text): print("no VO for ", who))
vo.say("res://vo", "voss", line)
```
