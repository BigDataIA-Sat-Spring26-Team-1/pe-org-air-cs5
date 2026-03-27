"""
PE Org-AI-R CS5 Architecture Diagram — Excalidraw generator (v2)
Fixes: proper gaps between sections, AWS/Snowflake icon badges, component icons
Run: python3 generate_architecture_diagram.py
Open output at excalidraw.com → File → Open
"""
import json, random, time

_counter = [0]
def uid():
    _counter[0] += 1
    return f"el_{_counter[0]:04d}"
def seed():
    return random.randint(100000, 999999)
TS = int(time.time() * 1000)

ELEMENTS = []

# ── Primitive builders ────────────────────────────────────────────────────────
def rect(x, y, w, h, stroke="#aaa", bg="#fff", opacity=85, sw=1, dashed=False):
    el = {
        "id": uid(), "type": "rectangle",
        "x": x, "y": y, "width": w, "height": h,
        "angle": 0, "strokeColor": stroke, "backgroundColor": bg,
        "fillStyle": "solid", "strokeWidth": sw,
        "strokeStyle": "dashed" if dashed else "solid",
        "roughness": 0, "opacity": opacity,
        "groupIds": [], "roundness": {"type": 3},
        "seed": seed(), "version": 1, "versionNonce": seed(),
        "isDeleted": False, "boundElements": None,
        "updated": TS, "link": None, "locked": False,
    }
    ELEMENTS.append(el)
    return el

def txt(x, y, content, size=12, color="#333", bold=False, w=None, align="center"):
    lines = content.split("\n")
    lh = size * 1.35
    th = lh * len(lines)
    tw = w if w else max(len(l) for l in lines) * size * 0.62
    el = {
        "id": uid(), "type": "text",
        "x": x, "y": y, "width": tw, "height": th,
        "angle": 0, "strokeColor": color, "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
        "roughness": 0, "opacity": 100,
        "groupIds": [], "roundness": None,
        "seed": seed(), "version": 1, "versionNonce": seed(),
        "isDeleted": False, "boundElements": None,
        "updated": TS, "link": None, "locked": False,
        "text": content, "fontSize": size, "fontFamily": 2,
        "textAlign": align, "verticalAlign": "top",
        "baseline": int(size * 0.9),
        "containerId": None, "originalText": content,
        "lineHeight": 1.35,
        "fontWeight": "bold" if bold else "normal",
    }
    ELEMENTS.append(el)
    return el

def arrow(x1, y1, x2, y2, color="#888", lw=1.5, label=""):
    dx, dy = x2-x1, y2-y1
    el = {
        "id": uid(), "type": "arrow",
        "x": x1, "y": y1, "width": abs(dx), "height": abs(dy),
        "angle": 0, "strokeColor": color, "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": lw, "strokeStyle": "solid",
        "roughness": 0, "opacity": 85,
        "groupIds": [], "roundness": {"type": 2},
        "seed": seed(), "version": 1, "versionNonce": seed(),
        "isDeleted": False, "boundElements": None,
        "updated": TS, "link": None, "locked": False,
        "points": [[0, 0], [dx, dy]],
        "lastCommittedPoint": None,
        "startBinding": None, "endBinding": None,
        "startArrowhead": None, "endArrowhead": "arrow",
    }
    ELEMENTS.append(el)
    if label:
        txt(x1+dx/2-35, y1+dy/2-14, label, size=9, color=color, w=70)

# ── Higher-level helpers ──────────────────────────────────────────────────────
def cluster(x, y, w, h, label, bg, stroke, icon_txt="", lsize=13, opacity=55, sw=2):
    """Outer cluster rectangle + bold header label with optional icon text element."""
    rect(x, y, w, h, stroke=stroke, bg=bg, opacity=opacity, sw=sw)
    if icon_txt:
        txt(x+8, y+7, icon_txt, size=lsize+1, color=stroke, bold=False, w=30)
        txt(x+44, y+8, label, size=lsize, color=stroke, bold=True, w=w-52)
    else:
        txt(x+8, y+8, label, size=lsize, color=stroke, bold=True, w=w-16)

def sub_cluster(x, y, w, h, label, bg, stroke, lsize=11, opacity=70):
    rect(x, y, w, h, stroke=stroke, bg=bg, opacity=opacity, sw=1)
    txt(x+8, y+6, label, size=lsize, color=stroke, bold=True, w=w-16)

# Icon box: icon emoji centred above label text
def icon_box(x, y, w, h, icon, label, bg="#fff", stroke="#bbb", fsize=10, is_new=False):
    bg_ = "#fff9c4" if is_new else bg
    st_ = "#f9a825" if is_new else stroke
    rect(x, y, w, h, stroke=st_, bg=bg_, opacity=95, sw=1)
    icon_size = min(fsize+4, 16)
    txt(x, y+6, icon, size=icon_size, color=stroke, w=w, align="center")
    txt(x+4, y+icon_size+10, label, size=fsize, color="#333", w=w-8, align="center")

# Plain text box (no icon)
def box(x, y, w, h, label, bg="#fff", stroke="#bbb", fsize=10, bold=False, is_new=False):
    bg_ = "#fff9c4" if is_new else bg
    st_ = "#f9a825" if is_new else stroke
    rect(x, y, w, h, stroke=st_, bg=bg_, opacity=95, sw=1)
    lh = fsize*1.35*(label.count("\n")+1)
    txt(x+4, y+(h-lh)/2, label, size=fsize, color="#333", w=w-8, align="center", bold=bold)

# AWS S3 orange badge
def s3_badge(x, y):
    rect(x, y, 32, 22, stroke="#ff9900", bg="#ff9900", opacity=100, sw=0)
    txt(x+16, y+4, "S3", size=10, color="#fff", bold=True, w=0)

# Snowflake blue badge
def sf_badge(x, y):
    rect(x, y, 32, 22, stroke="#29b5e8", bg="#29b5e8", opacity=100, sw=0)
    txt(x+16, y+3, "❄", size=14, color="#fff", bold=True, w=0)

# "★ NEW" pink badge
def new_badge(x, y):
    rect(x, y, 58, 20, stroke="#e91e63", bg="#e91e63", opacity=100, sw=0)
    txt(x+29, y+3, "★  NEW", size=9, color="#fff", bold=True, w=0)

# ═════════════════════════════════════════════════════════════════════════════
# LAYOUT
# Column x-positions (with explicit 50 px gaps between sections)
# ═════════════════════════════════════════════════════════════════════════════
GAP   = 50     # horizontal gap between sections
RGAP  = 60     # vertical gap between row tiers

C_EXT   = 20;   W_EXT   = 270
C_PIPE  = C_EXT  + W_EXT  + GAP;  W_PIPE  = 500
C_STORE = C_PIPE + W_PIPE + GAP;  W_STORE = 610
C_SCORE = C_STORE+ W_STORE+ GAP;  W_SCORE = 710
C_MCP   = C_SCORE+ W_SCORE+ GAP;  W_MCP   = 590

# Bottom-row columns
W_BACK  = 1590
C_BACK  = C_PIPE
C_ANAL  = C_BACK + W_BACK + GAP;  W_ANAL  = 590
C_FRONT = C_ANAL + W_ANAL + GAP;  W_FRONT = 680

# Row y-positions
R_TOP   = 100
H_TOP   = 1310   # height of top-tier clusters
R_MID   = R_TOP + H_TOP + RGAP    # ~1470
H_MID   = 700
R_BOT   = R_MID + H_MID + RGAP    # ~2230
H_BOT   = 1090

# ─────────────────────────────────────────────────────────────────────────────
# TITLE
# ─────────────────────────────────────────────────────────────────────────────
txt(C_PIPE, 30, "PE Org-AI-R Platform  —  Architecture Diagram  (CS1–CS5)",
    size=22, color="#1a237e", bold=True, w=2400)
txt(C_PIPE, 64, "Yellow = New CS5 component  |  Pink = LangGraph Agents  |  Lime = MCP Server  |  Teal = Analytics & Observability",
    size=11, color="#555", w=2400)

# ═════════════════════════════════════════════════════════════════════════════
# 1. EXTERNAL SOURCES
# ═════════════════════════════════════════════════════════════════════════════
cluster(C_EXT, R_TOP, W_EXT, H_TOP, "EXTERNAL SOURCES", "#fafafa", "#9e9e9e",
        icon_txt="@", lsize=12, opacity=45)
ext_items = [
    ("📄", "Proxy\nDEF 14A"),
    ("🏢", "Company\nWebsites"),
    ("📰", "Press\nReleases"),
    ("💼", "JobSpy\n(LinkedIn)"),
    ("💡", "PatentsView\nAPI"),
    ("⭐", "Glassdoor\n(Wextractor)"),
]
for i, (ico, lbl) in enumerate(ext_items):
    icon_box(C_EXT+15, R_TOP+80+i*190, W_EXT-30, 160, ico, lbl,
             bg="#f5f5f5", stroke="#bdbdbd")

# ═════════════════════════════════════════════════════════════════════════════
# 2. PIPELINES
# ═════════════════════════════════════════════════════════════════════════════
cluster(C_PIPE, R_TOP, W_PIPE, H_TOP+590, "PIPELINES", "#e8f5e9", "#43a047",
        icon_txt="⚙", lsize=13, opacity=50)

# — Signals Pipeline —
sub_cluster(C_PIPE+15, R_TOP+55, W_PIPE-30, 390, "⚡ SIGNALS PIPELINE",
            "#c8e6c9", "#43a047", opacity=65)
sig_items = [("👤","Leadership\nDetector"),("💼","JobSpy\nScraper"),
             ("🔧","Tech Stack\nScraper"),("💡","PatentsView\nFetch")]
for i,(ico,lbl) in enumerate(sig_items):
    icon_box(C_PIPE+25+(i%2)*235, R_TOP+115+(i//2)*145, 210, 125, ico, lbl,
             stroke="#43a047")
box(C_PIPE+145, R_TOP+395, 210, 38, "Aggregate Signals",
    bg="#a5d6a7", stroke="#43a047", fsize=10)

# — SEC Pipeline —
sub_cluster(C_PIPE+15, R_TOP+480, W_PIPE-30, 340, "📄 SEC PIPELINE",
            "#c8e6c9", "#43a047", opacity=65)
sec_items = [("📋","Parse\nSections"),("⬇","Fetch\nFilings"),
             ("🔀","Semantic\nChunking"),("🔄","Airflow\nScheduler")]
for i,(ico,lbl) in enumerate(sec_items):
    icon_box(C_PIPE+25+(i%2)*235, R_TOP+540+(i//2)*130, 210, 115, ico, lbl,
             stroke="#43a047")

# — Culture Collectors —
sub_cluster(C_PIPE+15, R_TOP+855, W_PIPE-30, 220,
            "👥 COMPANY CULTURE COLLECTORS", "#c8e6c9", "#43a047", opacity=65)
icon_box(C_PIPE+25, R_TOP+915, 210, 130, "🏛", "Board Comp.\nAnalyzer", stroke="#43a047")
icon_box(C_PIPE+265, R_TOP+915, 210, 130, "⭐", "Culture\nCollector", stroke="#43a047")

# — Ingestion —
sub_cluster(C_PIPE+15, R_TOP+1110, W_PIPE-30, 105, "⬆ INGESTION",
            "#c8e6c9", "#43a047", opacity=65)
box(C_PIPE+110, R_TOP+1150, 265, 48, "Retry Handler  (Tenacity)",
    stroke="#43a047", fsize=10)

# — API Triggers —
sub_cluster(C_PIPE+15, R_TOP+1250, W_PIPE-30, 620, "⚡ API TRIGGERS",
            "#c8e6c9", "#43a047", opacity=65)
trigger_items = [
    ("/signals/collect",           False),
    ("/documents/collect",          False),
    ("/rag/ingest",                 False),
    ("/rag/index-airflow",          False),
    ("/agent-ui/trigger-due-diligence  ★", True),
]
for i,(lbl,new) in enumerate(trigger_items):
    box(C_PIPE+25, R_TOP+1315+i*103, W_PIPE-50, 82, lbl,
        stroke="#43a047", fsize=10, is_new=new)

# ═════════════════════════════════════════════════════════════════════════════
# 3. STORAGE
# ═════════════════════════════════════════════════════════════════════════════
cluster(C_STORE, R_TOP, W_STORE, 1380, "STORAGE", "#e3f2fd", "#1976d2",
        icon_txt="🗄", lsize=13, opacity=50)

# AWS S3 row
s3_badge(C_STORE+50, R_TOP+70)
txt(C_STORE+90, R_TOP+70, "AWS S3", size=13, color="#ff9900", bold=True, w=100)
box(C_STORE+15, R_TOP+60, W_STORE-30, 70,
    "SEC filings  ·  Glassdoor review cache  ·  Analyst notes",
    bg="#fff8e1", stroke="#ff9900", fsize=10)

# Snowflake cluster
sf_badge(C_STORE+30, R_TOP+165)
sub_cluster(C_STORE+15, R_TOP+155, W_STORE-30, 1205,
            "         SNOWFLAKE  (Primary Data Warehouse)",
            "#bbdefb", "#1976d2", lsize=11, opacity=72)
snow_items = [
    ("📄","DOCUMENTS"), ("🏢","COMPANIES"), ("📊","ASSESS-\nMENTS"),
    ("📡","EXTERNAL_\nSIGNALS"), ("📈","SIGNAL_\nEVIDENCE"), ("🏭","COMPANY_SI\nGNAL_SUMMARIES"),
    ("📑","DOCUMENT_\nCHUNKS"), ("🔒","GOVERNANC\nE_SIGNALS"), ("⭐","CULTURE_SI\nGNALS"),
]
for i,(ico,tbl) in enumerate(snow_items):
    icon_box(C_STORE+25+(i%2)*285, R_TOP+240+(i//2)*225, 265, 200, ico, tbl,
             bg="#e3f2fd", stroke="#1976d2")

# ═════════════════════════════════════════════════════════════════════════════
# 4a. SCORING PIPELINE
# ═════════════════════════════════════════════════════════════════════════════
cluster(C_SCORE, R_TOP, W_SCORE, 1350, "SCORING PIPELINE", "#fff3e0", "#f57c00",
        icon_txt="📊", lsize=13, opacity=50)

# Processing
sub_cluster(C_SCORE+15, R_TOP+60, W_SCORE-30, 230,
            "⚙ PROCESSING  (Airflow DAG)", "#ffe0b2", "#f57c00", opacity=68)
proc_items = [("🧹","Data\nCleaner"),("🗺","Map\nCompanies"),("💾","Database"),("✈","Airflow")]
for i,(ico,lbl) in enumerate(proc_items):
    icon_box(C_SCORE+25+i*166, R_TOP+115, 150, 148, ico, lbl, stroke="#f57c00")

# Integration Service
sub_cluster(C_SCORE+15, R_TOP+330, W_SCORE-30, 280,
            "🔗 INTEGRATION SERVICE", "#ffe0b2", "#f57c00", opacity=68)
int_items = [("👤","Talent Conc.\nCalc"),("≈","Evidence-to-\nDim. Mapper"),("📐","Rubric-Based\nScorer (7 dims)")]
for i,(ico,lbl) in enumerate(int_items):
    icon_box(C_SCORE+25+i*222, R_TOP+395, 205, 190, ico, lbl, stroke="#f57c00")

# Scoring Engine
sub_cluster(C_SCORE+15, R_TOP+655, W_SCORE-30, 700,
            "⚡ SCORING ENGINE", "#ffe0b2", "#f57c00", opacity=68)
eng_items = [
    ("🧮","H*R Calc.\n(S=G·1S)"),  ("📈","Weighted\nSignal Density"),("△","Compute V*R\nScores"),
    ("🔄","Synergy\nCalculator"),    ("📊","Persist to\nSUMMARIES"),    ("🎯","Org-AI-R\nCalc"),
    ("📌","Position Factor\nCalculator"),("🤖","SEM\nConf. Int."),
]
for i,(ico,lbl) in enumerate(eng_items):
    icon_box(C_SCORE+25+(i%2)*338, R_TOP+725+(i//2)*155, 315, 135, ico, lbl,
             bg="#fff8e1", stroke="#f57c00")

# ═════════════════════════════════════════════════════════════════════════════
# 5. MCP SERVER (CS5 NEW)
# ═════════════════════════════════════════════════════════════════════════════
cluster(C_MCP, R_TOP, W_MCP, H_TOP, "MCP SERVER  (CS5)", "#f9fbe7", "#7cb342",
        icon_txt="🔌", lsize=13, opacity=52, sw=2)
new_badge(C_MCP+W_MCP-68, R_TOP+8)

# Transport banner
rect(C_MCP+15, R_TOP+62, W_MCP-30, 58, stroke="#7cb342", bg="#f0f4c3", opacity=95)
txt(C_MCP+W_MCP//2, R_TOP+68, "SSE Transport  :3001", size=12, color="#33691e", bold=True, w=W_MCP-30)
txt(C_MCP+W_MCP//2, R_TOP+88, "nginx proxies /mcp/* → container", size=10, color="#558b2f", w=W_MCP-30)

# Tools
sub_cluster(C_MCP+15, R_TOP+148, W_MCP-30, 590, "🔧 TOOLS (7)",
            "#f1f8e9", "#7cb342", opacity=72)
tools = [
    ("📋","get_portfolio_summary",False),
    ("🔢","calculate_org_air_score",False),
    ("🔍","get_company_evidence",False),
    ("📝","generate_justification",False),
    ("⚡","batch_generate_justifications ★\n(parallel asyncio.gather)",True),
    ("💰","project_ebitda_impact",False),
    ("📐","run_gap_analysis",False),
]
for i,(ico,lbl,new) in enumerate(tools):
    icon_box(C_MCP+25, R_TOP+210+i*74, W_MCP-50, 62, ico, lbl,
             stroke="#7cb342", fsize=9, is_new=new)

# Prompts
sub_cluster(C_MCP+15, R_TOP+768, W_MCP-30, 218, "📜 PROMPTS (2)",
            "#f1f8e9", "#7cb342", opacity=72)
icon_box(C_MCP+25, R_TOP+825, (W_MCP-60)//2, 140, "📋",
         "due_diligence\n_assessment", bg="#f0f4c3", stroke="#7cb342", fsize=9)
icon_box(C_MCP+35+(W_MCP-60)//2, R_TOP+825, (W_MCP-60)//2, 140, "🏛",
         "ic_meeting\n_prep", bg="#f0f4c3", stroke="#7cb342", fsize=9)

# Resources
sub_cluster(C_MCP+15, R_TOP+1015, W_MCP-30, 258, "📦 RESOURCES (2)",
            "#f1f8e9", "#7cb342", opacity=72)
icon_box(C_MCP+25, R_TOP+1075, (W_MCP-60)//2, 175, "⚙",
         "orgair://parameters/v2.0\nalpha=0.60\nbeta=0.12\ngamma values",
         bg="#f0f4c3", stroke="#7cb342", fsize=9)
icon_box(C_MCP+35+(W_MCP-60)//2, R_TOP+1075, (W_MCP-60)//2, 175, "🏭",
         "orgair://sectors\ntech, healthcare\nbaselines &\nweights",
         bg="#f0f4c3", stroke="#7cb342", fsize=9)

# ═════════════════════════════════════════════════════════════════════════════
# 3b. RAG PIPELINE  (middle row, under Storage)
# ═════════════════════════════════════════════════════════════════════════════
cluster(C_STORE, R_MID, W_STORE, H_MID, "RAG PIPELINE  (CS4)", "#f3e5f5", "#8e24aa",
        icon_txt="🔍", lsize=13, opacity=50)

icon_box(C_STORE+15, R_MID+70, 270, 205, "🗄",
         "Vector Database\n(ChromaDB)\nHNSW cosine index\ntext-embedding-3-small",
         bg="#f3e5f5", stroke="#8e24aa")
icon_box(C_STORE+305, R_MID+70, 270, 205, "📋",
         "Embeddings Index\n(BM25Okapi)\nKeyword retrieval\nIn-memory",
         bg="#f3e5f5", stroke="#8e24aa")

box(C_STORE+15, R_MID+293, W_STORE-30, 65,
    "Hybrid Retriever  (RRF Fusion: Dense 0.6 + BM25 0.4)  +  HyDE Query Expansion",
    bg="#e1bee7", stroke="#8e24aa", fsize=10, bold=True)
box(C_STORE+15, R_MID+375, W_STORE-30, 58,
    "LiteLLM Router  →  GPT-4o (primary)  /  Claude-3.5-Sonnet (fallback)  |  $50/day cap",
    bg="#e8eaf6", stroke="#5c6bc0", fsize=10)
txt(C_STORE+W_STORE//2, R_MID+448, "Fetches from Snowflake ↑  |  Indexes SEC chunks, signals, analyst notes",
    size=9, color="#8e24aa", w=W_STORE-30)
box(C_STORE+15, R_MID+475, W_STORE-30, 150,
    "JustificationGenerator\n~150-word PE memos per dimension\nICPrepWorkflow  →  Buy / Hold / Pass",
    bg="#f8bbd0", stroke="#ad1457", fsize=10)

# ═════════════════════════════════════════════════════════════════════════════
# 4b. LANGGRAPH AGENTS (CS5 NEW)  — middle row under Scoring
# ═════════════════════════════════════════════════════════════════════════════
cluster(C_SCORE, R_MID, W_SCORE, H_MID, "LANGGRAPH AGENTS  (CS5)", "#fce4ec", "#c2185b",
        icon_txt="🤖", lsize=13, opacity=52, sw=2)
new_badge(C_SCORE+W_SCORE-68, R_MID+8)

# State
sub_cluster(C_SCORE+15, R_MID+58, W_SCORE-30, 148,
            "DueDiligenceState  (Shared Thread Context — TypedDict)",
            "#f8bbd0", "#c2185b", opacity=80)
state_items = ["company_id","sec_analysis","scoring_result","evidence","value_creation_plan","requires_approval / hitl_status"]
for i,f in enumerate(state_items):
    box(C_SCORE+25+(i%3)*223, R_MID+108+(i//3)*50, 213, 44,
        f, bg="#fce4ec", stroke="#c2185b", fsize=9)

# Agent flow
AY = R_MID+230
agent_cols = [
    ("🔍","SEC Analyst\nAgent",  C_SCORE+20),
    ("🔢","Scorer\nAgent",       C_SCORE+185),
    ("📋","Evidence\nAgent",     C_SCORE+350),
]
for ico,lbl,ax_ in agent_cols:
    icon_box(ax_, AY, 150, 130, ico, lbl, bg="#f48fb1", stroke="#c2185b")
arrow(C_SCORE+172, AY+65, C_SCORE+185, AY+65, "#c2185b")
arrow(C_SCORE+337, AY+65, C_SCORE+350, AY+65, "#c2185b")
# Supervisor label
txt(C_SCORE+525, AY+15, "Supervisor\n(StateGraph)\nconditional\nrouting",
    size=9, color="#c2185b", w=170)
rect(C_SCORE+520, AY+8, 175, 90, stroke="#c2185b", bg="transparent", opacity=0)

icon_box(C_SCORE+20, AY+158, 295, 120, "💡",
         "Value Creator Agent\n(Full mode only)\nGap Analysis + EBITDA Projection",
         bg="#f48fb1", stroke="#c2185b")
icon_box(C_SCORE+335, AY+158, 295, 120, "⚠",
         "HITL Check\n(approval gate)\nstatus: pending / approved",
         bg="#ef9a9a", stroke="#b71c1c", is_new=False)

txt(C_SCORE+20, AY+295,
    "Full:   SEC → Score → Evidence → Value Creator → HITL → END",
    size=9, color="#880e4f", w=640)
txt(C_SCORE+20, AY+316,
    "Quick: SEC → Score → Evidence → HITL → END  (skips Value Creator, ~20–40s faster)",
    size=9, color="#880e4f", w=640)

icon_box(C_SCORE+20, AY+342, 360, 90, "📄",
         "IC Memo (.docx)  ·  LP Letter (.docx)\n/generate-ic-memo  /generate-lp-letter",
         bg="#fff9c4", stroke="#f9a825")

# Mem0 Platform — cross-session memory (side-by-side with IC Memo box)
icon_box(C_SCORE+400, AY+342, 280, 90, "🧠",
         "Mem0 Platform API\nsearch_memory()  ·  add_memory()\nper-company namespace (user_id)",
         bg="#e8eaf6", stroke="#3949ab", fsize=9, is_new=True)

# ═════════════════════════════════════════════════════════════════════════════
# 6. CLAUDE DESKTOP  (CS5 NEW) — middle row under MCP
# ═════════════════════════════════════════════════════════════════════════════
cluster(C_MCP, R_MID, W_MCP, H_MID, "Claude Desktop  +  mcp-remote", "#e8f5e9", "#388e3c",
        icon_txt="🖥", lsize=13, opacity=52, sw=2)
new_badge(C_MCP+W_MCP-68, R_MID+8)

box(C_MCP+15, R_MID+65, W_MCP-30, 62,
    "npx mcp-remote http://localhost:3001/sse\n(stdio ↔ SSE bridge)",
    bg="#c8e6c9", stroke="#388e3c", fsize=10, bold=True)

icon_box(C_MCP+15, R_MID+150, 260, 250, "💬",
         "Natural Language\nTool Calls\n(sequential per call)",
         bg="#e8f5e9", stroke="#388e3c")
icon_box(C_MCP+295, R_MID+150, 260, 250, "⚡",
         "batch_generate_\njustifications ★\n→ all 7 dims\nin 1 call",
         bg="#fff9c4", stroke="#f9a825")

box(C_MCP+15, R_MID+425, W_MCP-30, 60,
    "Connects as MCP client  |  Resources surfaced in sidebar  |  Prompts as slash-commands",
    bg="#dcedc8", stroke="#558b2f", fsize=9)

# ═════════════════════════════════════════════════════════════════════════════
# BOTTOM ROW
# ═════════════════════════════════════════════════════════════════════════════

# ── FastAPI Backend ────────────────────────────────────────────────────────
cluster(C_BACK, R_BOT, W_BACK, H_BOT, "BACKEND  —  FastAPI Service", "#e8eaf6", "#3949ab",
        icon_txt="⚡", lsize=14, opacity=50)
# sub: FastAPI Service
sub_cluster(C_BACK+15, R_BOT+60, W_BACK-30, 80, "● FASTAPI SERVICE",
            "#c5cae9", "#3949ab", opacity=65)

# Existing routes row 1
route1 = [("/companies","🏢"),("/assessments","📋"),("/signals","📡"),("/metrics","📈"),("/health","❤"),("/score","🎯")]
for i,(r,ico) in enumerate(route1):
    icon_box(C_BACK+20+i*255, R_BOT+155, 240, 100, ico, r, stroke="#3949ab")

# Existing routes row 2
route2 = [("/rag\n(ingest, query, notes)","🔍"),("/justify\n(IC Meeting Package)","📝"),("/audit/{ticker}","🔍"),("/documents","📄"),("/integration","🔗")]
for i,(r,ico) in enumerate(route2):
    icon_box(C_BACK+20+i*307, R_BOT+270, 290, 100, ico, r, stroke="#3949ab")

# New CS5 routes
txt(C_BACK+20, R_BOT+388, "★  NEW CS5 ROUTES:", size=11, color="#f9a825", bold=True, w=350)
new_routes_data = [
    ("/agent-ui/portfolio  /agent-ui/fund-air\n/agent-ui/trigger-due-diligence\n/agent-ui/generate-ic-memo  /generate-lp-letter\n/agent-ui/mcp-tools","🤖"),
    ("/investments/portfolio-roi\n/investments/{company_id}/roi","📈"),
    ("/observability/metrics-snapshot","📊"),
]
for i,(r,ico) in enumerate(new_routes_data):
    icon_box(C_BACK+20+i*525, R_BOT+415, 505, 155, ico, r,
             stroke="#f9a825", fsize=9, is_new=True)

# Infrastructure
icon_box(C_BACK+20, R_BOT+590, 370, 110, "🔴",
         "Redis Cache\n(session cache · score cache)",
         bg="#ffebee", stroke="#f44336")
icon_box(C_BACK+410, R_BOT+590, 370, 110, "📊",
         "Prometheus Metrics\n(per-process counters\nresets on container restart)",
         bg="#fff9c4", stroke="#f9a825", is_new=True)
icon_box(C_BACK+800, R_BOT+590, 770, 110, "🔧",
         "Assessment History Service  +  InvestmentTracker  +  Fund-AI-R Calculator\n(seeded from CS3 portfolio data on first request)",
         bg="#fff9c4", stroke="#f9a825", is_new=True)

box(C_BACK+20, R_BOT+720, W_BACK-30, 55,
    "@track_mcp_tool()   @track_agent()   @track_cs_client()  —  Prometheus decorators instrument all service boundaries",
    bg="#e8eaf6", stroke="#3949ab", fsize=9)

# Redis Cache dashed arrow to /rag
# (Redis cache is internal to FastAPI — no cross-box arrow needed)

# ── Analytics & Observability (CS5 NEW) ────────────────────────────────────
cluster(C_ANAL, R_BOT, W_ANAL, H_BOT, "ANALYTICS &\nOBSERVABILITY  (CS5)", "#e0f2f1", "#00796b",
        icon_txt="📈", lsize=13, opacity=52, sw=2)
new_badge(C_ANAL+W_ANAL-68, R_BOT+8)

obs_items = [
    ("💰","InvestmentTracker\nMOIC · IRR · Simple ROI\nAnnualised ROI %"),
    ("🤖","AI Attribution (%)\ndelta_org_air × sector\ncoefficient (tech: 35%)"),
    ("🏦","Fund-AI-R Calculator\nEV-weighted composite\nOrg-AI-R across fund"),
    ("📊","PortfolioROISummary\nTotal invested\nBest / worst performer"),
    ("📜","Assessment History\nMulti-session trends\nHistorical snapshots"),
    ("📡","Prometheus Registry\nmcp_tool_calls\nagent_invocations\nhitl_approvals · cs_client_calls"),
]
for i,(ico,lbl) in enumerate(obs_items):
    icon_box(C_ANAL+20, R_BOT+80+i*155, W_ANAL-40, 135,
             ico, lbl, bg="#b2dfdb", stroke="#00796b")

# ── Frontend (CS5 expanded) ────────────────────────────────────────────────
cluster(C_FRONT, R_BOT, W_FRONT, H_BOT, "FRONTEND  —  Next.js 15\n(App Router · TypeScript · Tailwind)",
        "#e0f7fa", "#0097a7", icon_txt="🖥", lsize=13, opacity=50)

# Next.js Dashboard sub-header
sub_cluster(C_FRONT+15, R_BOT+65, W_FRONT-30, 60, "● NEXT.JS DASHBOARD",
            "#b2ebf2", "#0097a7", opacity=70)
icon_box(C_FRONT+25, R_BOT+135, 290, 70, "⚡", "Realtime Fetch",
         bg="#e0f7fa", stroke="#0097a7", fsize=9)
icon_box(C_FRONT+335, R_BOT+135, 290, 70, "🖥", "SSR",
         bg="#e0f7fa", stroke="#0097a7", fsize=9)

# Existing pages
sub_cluster(C_FRONT+15, R_BOT+222, W_FRONT-30, 60, "● EXISTING PAGES",
            "#b2ebf2", "#0097a7", opacity=70)
existing = [("📊","Dashboard"),("📈","Analytics"),("🤖","AI Readiness"),
            ("📄","SEC Explorer"),("🔍","RAG Analysis"),("📋","Documents")]
for i,(ico,lbl) in enumerate(existing):
    icon_box(C_FRONT+25+(i%2)*315, R_BOT+292+(i//2)*105, 295, 90,
             ico, lbl, stroke="#0097a7", fsize=9)

# New CS5 pages
sub_cluster(C_FRONT+15, R_BOT+617, W_FRONT-30, 60, "★  NEW CS5 PAGES",
            "#fff9c4", "#f9a825", opacity=80)
new_pg = [
    ("🔄","/workflow\nAgentic Workflow UI\n(live agent progress)"),
    ("🔌","/mcp-server\nMCP Setup + Tools\n(5 tabs · 15 prompts)"),
    ("💰","/investments\nInvestment ROI\n(MOIC · AI attribution)"),
    ("📊","/observability\nPrometheus Metrics\n(auto-refresh 15s)"),
]
for i,(ico,lbl) in enumerate(new_pg):
    icon_box(C_FRONT+25+(i%2)*315, R_BOT+690+(i//2)*170, 295, 150,
             ico, lbl, bg="#fff9c4", stroke="#f9a825", fsize=9, is_new=True)

box(C_FRONT+15, R_BOT+1030, W_FRONT-30, 55,
    "SSR + Realtime fetch  |  Lucide React icons  |  Tailwind CSS dark theme",
    bg="#b2ebf2", stroke="#0097a7", fsize=10)

# ═════════════════════════════════════════════════════════════════════════════
# ARROWS — key data flows
# All labels placed ABOVE the arrow at the midpoint of the gap,
# never inside destination boxes.
# ═════════════════════════════════════════════════════════════════════════════

def _label_above(x1, x2, y, label, color):
    """Place a label centered above a horizontal arrow gap."""
    mid_x = (x1 + x2) / 2
    txt(mid_x - 35, y - 32, label, size=9, color=color, w=70)

def _label_right(x, y, label, color):
    """Place a label just right of an arrow start on a vertical arrow."""
    txt(x + 6, y + 8, label, size=9, color=color, w=85)

# 1. External Sources → Pipelines
arrow(C_EXT+W_EXT, R_TOP+350, C_PIPE, R_TOP+350, "#9e9e9e")
_label_above(C_EXT+W_EXT, C_PIPE, R_TOP+350, "signals", "#9e9e9e")
arrow(C_EXT+W_EXT, R_TOP+680, C_PIPE, R_TOP+680, "#9e9e9e")
_label_above(C_EXT+W_EXT, C_PIPE, R_TOP+680, "SEC docs", "#9e9e9e")

# 2. Pipelines → Snowflake
arrow(C_PIPE+W_PIPE, R_TOP+550, C_STORE, R_TOP+550, "#1976d2")
_label_above(C_PIPE+W_PIPE, C_STORE, R_TOP+550, "persist", "#1976d2")

# 3. Snowflake → RAG Pipeline (downward, left side of Storage col)
arrow(C_STORE+130, R_TOP+H_TOP, C_STORE+130, R_MID, "#8e24aa")
_label_right(C_STORE+130, R_TOP+H_TOP, "index →\nChromaDB", "#8e24aa")

# 4. Snowflake → Scoring Pipeline (horizontal, right side of Storage)
arrow(C_STORE+W_STORE, R_TOP+480, C_SCORE, R_TOP+480, "#f57c00")
_label_above(C_STORE+W_STORE, C_SCORE, R_TOP+480, "raw data", "#f57c00")

# 5. Scoring Pipeline → LangGraph Agents (downward)
arrow(C_SCORE+250, R_TOP+H_TOP, C_SCORE+250, R_MID, "#c2185b")
_label_right(C_SCORE+250, R_TOP+H_TOP, "scores &\nresults", "#c2185b")

# 6. MCP Server → Claude Desktop (downward, within MCP column)
arrow(C_MCP+W_MCP//2, R_TOP+H_TOP, C_MCP+W_MCP//2, R_MID, "#388e3c")
_label_right(C_MCP+W_MCP//2, R_TOP+H_TOP, "mcp-remote\n(stdio↔SSE)", "#388e3c")

# 7. LangGraph Agents → FastAPI Backend (downward)
arrow(C_SCORE+250, R_MID+H_MID, C_SCORE+250, R_BOT, "#c2185b")
_label_right(C_SCORE+250, R_MID+H_MID, "workflow\nresults", "#c2185b")

# 8. RAG Pipeline → FastAPI Backend (downward)
arrow(C_STORE+450, R_MID+H_MID, C_STORE+450, R_BOT, "#8e24aa")
_label_right(C_STORE+450, R_MID+H_MID, "justifications", "#8e24aa")

# 9. Backend → Analytics & Observability (horizontal, 50 px gap)
#    Label placed above the gap, NOT inside either box
arrow(C_BACK+W_BACK, R_BOT+380, C_ANAL, R_BOT+380, "#00796b", lw=1.5)
txt(C_BACK+W_BACK + GAP//2 - 38, R_BOT+348, "metrics &\nROI data", size=9, color="#00796b", w=76)

# 10. Analytics → Frontend (horizontal, 50 px gap)
#     Label placed above the gap
arrow(C_ANAL+W_ANAL, R_BOT+380, C_FRONT, R_BOT+380, "#0097a7", lw=1.5)
txt(C_ANAL+W_ANAL + GAP//2 - 38, R_BOT+348, "API\nresponses", size=9, color="#0097a7", w=76)

# ═════════════════════════════════════════════════════════════════════════════
# LEGEND
# ═════════════════════════════════════════════════════════════════════════════
LX, LY = C_BACK, R_BOT+H_BOT+30
rect(LX, LY, 1500, 100, stroke="#aaa", bg="#fafafa", opacity=90)
txt(LX+10, LY+10, "LEGEND", size=11, color="#333", bold=True, w=70)
legend = [
    ("#fff9c4","#f9a825","★ New CS5 Component"),
    ("#fce4ec","#c2185b","🤖 LangGraph Agents"),
    ("#f9fbe7","#7cb342","🔌 MCP Server"),
    ("#e0f2f1","#00796b","📈 Analytics & Obs."),
    ("#fff3e0","#f57c00","📊 Scoring Pipeline"),
    ("#f3e5f5","#8e24aa","🔍 RAG Pipeline"),
    ("#e3f2fd","#1976d2","❄ Snowflake/Storage"),
]
for i,(bg,st,lbl) in enumerate(legend):
    rect(LX+10+i*210, LY+40, 195, 28, stroke=st, bg=bg, opacity=95)
    txt(LX+10+i*210+5, LY+72, lbl, size=9, color="#333", w=200)

# ═════════════════════════════════════════════════════════════════════════════
# OUTPUT
# ═════════════════════════════════════════════════════════════════════════════
outpath = ("/Users/aakashbelide/Aakash/Higher Studies/Course/Sem-4/"
           "DAMG 7245/Case Study 5/pe-org-air-cs5/pe-org-air-platform/"
           "Architecture_Diagram_CS5.excalidraw")

excalidraw = {
    "type": "excalidraw",
    "version": 2,
    "source": "https://excalidraw.com",
    "elements": ELEMENTS,
    "appState": {
        "gridSize": None,
        "viewBackgroundColor": "#f5f7fa",
        "currentItemFontFamily": 2,
        "theme": "light",
        "zoom": {"value": 0.5},
    },
    "files": {}
}

with open(outpath, "w") as f:
    json.dump(excalidraw, f, indent=2)

print(f"✅  {len(ELEMENTS)} elements → {outpath}")
print("   Open at excalidraw.com  →  File  →  Open")
