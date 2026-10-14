import sys, types, asyncio, ast, json, os, tempfile
sys.path.insert(0, "/home/claude/server/server")
# ---- stub heavy/external modules (no Manim / Gemini / Cloudinary here) ----
def stub(name, **attrs):
    m = types.ModuleType(name); m.__dict__.update(attrs); sys.modules[name] = m; return m
stub("google"); g = stub("google.genai", Client=lambda *a, **k: None); sys.modules["google"].genai = g
stub("google.genai.types", GenerateContentConfig=lambda **k: None); g.types = sys.modules["google.genai.types"]
stub("dotenv", load_dotenv=lambda *a, **k: None)
class AE:
    def __init__(self, **k): pass
    async def generate_episode_audio(self, ep): return {"status": "failed"}
stub("app.services.audio_engine", AudioEngine=AE)
stub("app.services.video_engine", VideoEngine=lambda **k: None)
stub("app.storage.cloudinary_storage", upload_episode_video=lambda *a, **k: None)
from app.services import manim_engine as me

eng = object.__new__(me.Manim_Engine)
eng.output_dir = tempfile.mkdtemp()
for d in ("audio", "final", "videos"): os.makedirs(os.path.join(eng.output_dir, d))
rendered = []
def fake_run(filepath):
    code = open(filepath, encoding="utf-8").read(); ast.parse(code); rendered.append(code); return True, "ok"
eng._run_manim = fake_run
eng._resolve_rendered_mp4_path = lambda p: p
eng._ask_gemini_to_fix_lines = lambda **k: None
eng._ask_gemini_to_fix = lambda **k: None

# A realistic NEW-format episode, including the failure modes found in the audit:
bad = json.loads('{"x":"\\frac{1}{2} \\theta \\beta \\nu"}')["x"]          # JSON-corrupted latex
ep = {
 "episode_number": 1, "title": "โจทย์ข้อ 1: หา T1", "problem_desc": "มวล 5 kg แขวนด้วยเชือก",
 "video_plan": {"estimated_duration_seconds": 60, "visual_cues": "", "audio_cues": ""},
 "script": {"hook": "", "main_body": "", "example_or_trick": "", "call_to_action": ""},
 "diagram_code_lines": [                       # un-indented + forbidden re-import + redefinition
   "from manim import *", "middle_center = np.array([0,0,0])",
   "axes = Axes(x_range=[0,10,1], x_length=frame_width*0.6, y_length=middle_zone_height*0.6)",
   "lbl = MathTex(r'T_1 \\sin\\theta', font_size=18, color=BLUE_C)",
   "g = VGroup(axes, lbl)", "g.scale_to_fit_width(frame_width * 0.88)",
   "g.move_to(middle_center)", "self.play(Create(g))", "self.wait(1.0)"],
 "steps": [
   {"title": "1. สมดุล:", "lines": [{"label": "จาก (2):", "latex": bad},
                                    {"latex": "\\\\\\\\frac{T_1}{T_2}"},          # over-escaped
                                    {"latex": "\\mathrm{แรงตึง} = 5\\,N"},        # Thai in latex
                                    {"latex": "\\frac{1}{2"}]},                  # unbalanced -> dropped
 ]}
res = asyncio.run(eng.render_episode(ep))
print("status:", res["status"], "| attempts:", res["attempts"], "| degraded:", res.get("degraded"))
code = rendered[-1]
print("---- compiled scene (diagram + steps region) ----")
for l in code.splitlines()[27:]: print(l)

# stub episode from enforce_episode_count (new schema) must render too
rendered.clear()
stub_lj = eng.enforce_episode_count({"episodes": []}, 1, ["โจทย์ ข้อ 3's test"])
r2 = asyncio.run(eng.render_episode(stub_lj["episodes"][0]))
print("\nstub episode ->", r2["status"])

# old-format episode (what used to crash with KeyError) now fails CLEANLY, not with an exception
r3 = asyncio.run(eng.render_episode({"episode_number": 9, "title": "old", "manim_code_lines": ["pass"]}))
print("old-format ->", r3["status"], "|", r3["message"][:90])

print("\n=== fallback test: diagram always crashes Manim ===")
rendered.clear()
def crashy(filepath):
    code = open(filepath, encoding="utf-8").read()
    if "DiagramBoom" in code: return False, "NameError: DiagramBoom"
    rendered.append(code); return True, "ok"
eng._run_manim = crashy
ep2 = dict(ep); ep2["diagram_code_lines"] = ["        x = DiagramBoom()", "        self.play(Create(x))"]
r = asyncio.run(eng.render_episode(ep2))
print("status:", r["status"], "| attempts:", r["attempts"], "| degraded:", r.get("degraded"),
      "| steps still rendered:", "step1_group" in rendered[-1])