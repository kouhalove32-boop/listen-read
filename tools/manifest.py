"""Write audio/voices.json: which problems have audio for which voice."""
import json, os
out = {}
for v in sorted(os.listdir('audio')):
    d = os.path.join('audio', v)
    if not os.path.isdir(d):
        continue
    ids = sorted(f[:-5] for f in os.listdir(d) if f.endswith('.json') and os.path.exists(os.path.join(d, f[:-5] + '.mp3')))
    if ids:
        out[v] = ids
json.dump(out, open('audio/voices.json', 'w'), indent=1)
print({k: len(v) for k, v in out.items()})
