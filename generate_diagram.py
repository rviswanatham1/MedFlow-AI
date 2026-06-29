"""
MedflowAI — Architectural Workflow Diagram
Run: python generate_diagram.py
Output: medflowai_architecture.png
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe
import numpy as np

# ── Palette ──────────────────────────────────────────────────────────────────
BG          = "#0D1B2A"
NAVY_MID    = "#112233"
NAVY_LIGHT  = "#1A2F45"
TEAL        = "#00C9B1"
TEAL_DIM    = "#0A3D35"
BLUE        = "#4A9EFF"
BLUE_DIM    = "#0A2A4A"
AMBER       = "#FFB344"
AMBER_DIM   = "#3A2A00"
RED         = "#FF5A5A"
RED_DIM     = "#3A0A0A"
GREEN       = "#4ADE80"
GREEN_DIM   = "#0A2A15"
PURPLE      = "#A78BFA"
PURPLE_DIM  = "#1E1040"
GRAY        = "#8899AA"
WHITE       = "#F0F4F8"
GLASS       = "#FFFFFF0F"

fig = plt.figure(figsize=(28, 20), facecolor=BG)
ax  = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 28)
ax.set_ylim(0, 20)
ax.axis("off")
ax.set_facecolor(BG)

# ── Helper: rounded box ───────────────────────────────────────────────────────
def box(ax, x, y, w, h, label, sublabel="", fill=NAVY_LIGHT, edge=TEAL,
        label_color=WHITE, sub_color=GRAY, icon="", fontsize=9, radius=0.35,
        badge=None, badge_color=TEAL):
    rect = FancyBboxPatch(
        (x - w/2, y - h/2), w, h,
        boxstyle=f"round,pad=0,rounding_size={radius}",
        facecolor=fill, edgecolor=edge, linewidth=1.4, zorder=3
    )
    ax.add_patch(rect)

    # inner glow line at top
    glow = FancyBboxPatch(
        (x - w/2 + 0.04, y + h/2 - 0.13), w - 0.08, 0.08,
        boxstyle=f"round,pad=0,rounding_size=0.1",
        facecolor=edge, edgecolor="none", alpha=0.35, zorder=4
    )
    ax.add_patch(glow)

    top = y + (0.1 if sublabel else 0)
    if icon:
        ax.text(x, top + 0.05, icon, ha="center", va="center",
                fontsize=fontsize + 4, zorder=5)
        top -= 0.28
    ax.text(x, top, label, ha="center", va="center",
            fontsize=fontsize, fontweight="bold", color=label_color, zorder=5,
            wrap=True)
    if sublabel:
        ax.text(x, y - 0.22, sublabel, ha="center", va="center",
                fontsize=fontsize - 1.5, color=sub_color, zorder=5,
                style="italic")
    if badge:
        bx, by = x + w/2 - 0.22, y + h/2 - 0.18
        circ = plt.Circle((bx, by), 0.17, color=badge_color, zorder=6)
        ax.add_patch(circ)
        ax.text(bx, by, badge, ha="center", va="center",
                fontsize=6.5, fontweight="bold", color=BG, zorder=7)

def arrow(ax, x1, y1, x2, y2, color=TEAL, lw=1.6, label="", style="->",
          rad=0.0, alpha=0.85):
    ax.annotate("",
        xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(
            arrowstyle=style, color=color, lw=lw,
            connectionstyle=f"arc3,rad={rad}",
            alpha=alpha
        ), zorder=2
    )
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx + 0.05, my + 0.05, label, fontsize=6.5, color=color,
                ha="center", va="center",
                bbox=dict(boxstyle="round,pad=0.15", fc=BG, ec="none", alpha=0.8),
                zorder=6)

def section_bg(ax, x, y, w, h, color, label="", alpha=0.18):
    rect = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0,rounding_size=0.4",
        facecolor=color, edgecolor=color, linewidth=1.0,
        alpha=alpha, zorder=1
    )
    ax.add_patch(rect)
    if label:
        ax.text(x + 0.25, y + h - 0.28, label,
                fontsize=7.5, color=color, fontweight="bold",
                alpha=0.9, zorder=2)

def legend_item(ax, x, y, color, label):
    rect = FancyBboxPatch((x, y), 0.28, 0.18,
                           boxstyle="round,pad=0,rounding_size=0.05",
                           facecolor=color, edgecolor="none", alpha=0.85, zorder=5)
    ax.add_patch(rect)
    ax.text(x + 0.38, y + 0.09, label, fontsize=7, color=GRAY,
            va="center", zorder=5)

# ══════════════════════════════════════════════════════════════════════════════
# TITLE
# ══════════════════════════════════════════════════════════════════════════════
ax.text(14, 19.45, "MedFlow", fontsize=30, fontweight="black",
        color=WHITE, ha="center", va="center", zorder=10,
        path_effects=[pe.withStroke(linewidth=6, foreground=BG)])
ax.text(18.15, 19.45, "AI", fontsize=30, fontweight="black",
        color=TEAL, ha="center", va="center", zorder=10)
ax.text(14, 18.95, "Multi-Agent Clinical Triage Architecture",
        fontsize=13, color=GRAY, ha="center", va="center", zorder=10,
        style="italic")

# thin divider
ax.axhline(18.65, color=TEAL, lw=0.6, alpha=0.3, zorder=2)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION BACKGROUNDS
# ══════════════════════════════════════════════════════════════════════════════
# Left column – Entry & LLM
section_bg(ax, 0.3,  9.5,  4.4, 8.85, BLUE,   "ENTRY LAYER",   alpha=0.10)
section_bg(ax, 0.3,  0.3,  4.4, 8.9,  PURPLE, "LLM PROVIDER",  alpha=0.10)

# Middle column – Agent Pipeline
section_bg(ax, 5.1,  0.3, 10.4, 18.0, TEAL,   "AGENT PIPELINE", alpha=0.07)

# Right column – Output & Frontend
section_bg(ax, 15.9, 9.5,  5.8, 8.85, AMBER,  "DATA STORE",    alpha=0.08)
section_bg(ax, 15.9, 0.3,  5.8, 8.9,  GREEN,  "FRONTEND",      alpha=0.08)

# Far-right – React Native
section_bg(ax, 22.1, 0.3,  5.5, 18.0, BLUE,   "REACT NATIVE APP", alpha=0.08)

# ══════════════════════════════════════════════════════════════════════════════
# ENTRY LAYER (left column, top)
# ══════════════════════════════════════════════════════════════════════════════
# Patient walk-in
box(ax, 2.5, 17.8, 3.5, 0.75, "🚶 Walk-in Patient",
    fill=BLUE_DIM, edge=BLUE, label_color=WHITE, fontsize=8.5)

# 911 call
box(ax, 2.5, 16.7, 3.5, 0.75, "🚑 Emergency (911 / EMS)",
    fill=RED_DIM, edge=RED, label_color=WHITE, fontsize=8.5)

# Voice transcription
box(ax, 2.5, 15.4, 3.5, 0.9, "Voice Transcription Agent",
    sublabel="voice_transcription_agent.py",
    fill=NAVY_LIGHT, edge=BLUE, fontsize=8)

# Image analysis
box(ax, 2.5, 14.1, 3.5, 0.9, "Image Analysis Agent",
    sublabel="image_analysis_agent.py",
    fill=NAVY_LIGHT, edge=PURPLE, fontsize=8,
    badge="opt", badge_color=PURPLE)

# Voice intake
box(ax, 2.5, 12.8, 3.5, 0.9, "Voice Intake Agent",
    sublabel="voice_intake_agent.py",
    fill=NAVY_LIGHT, edge=BLUE, fontsize=8)

# Sepsis screener
box(ax, 2.5, 11.4, 3.5, 0.9, "⚡ Sepsis Screener",
    sublabel="sepsis_screener.py  |  qSOFA",
    fill=RED_DIM, edge=RED, label_color=WHITE, fontsize=8)

# Vitals input
box(ax, 2.5, 10.2, 3.5, 0.75, "📊 Patient Vitals Input",
    fill=NAVY_LIGHT, edge=GRAY, label_color=GRAY, fontsize=8)

# ── LLM PROVIDER (left column, bottom) ────────────────────────────────────
box(ax, 2.5, 8.5, 3.6, 1.1, "LLM Provider Factory",
    sublabel="llm_provider.py",
    fill=PURPLE_DIM, edge=PURPLE, label_color=WHITE, fontsize=8.5)

llm_y = [7.15, 6.0, 4.85]
llm_labels = ["🤖 Gemini\n(Google)", "🦙 Ollama / DeepSeek\n(Local)", "🧠 Claude\n(Anthropic)"]
llm_cols   = [TEAL, AMBER, BLUE]
llm_edges  = [TEAL, AMBER, BLUE]
for i, (ly, ll, lc, le) in enumerate(zip(llm_y, llm_labels, llm_cols, llm_edges)):
    box(ax, 2.5, ly, 3.2, 0.75, ll,
        fill=BG, edge=le, label_color=lc, fontsize=7.5)

box(ax, 2.5, 3.55, 3.6, 0.9, "LangChain Chat Model",
    sublabel="Unified interface for all LLMs",
    fill=NAVY_LIGHT, edge=PURPLE, fontsize=8)

box(ax, 2.5, 2.35, 3.6, 0.9, "LangGraph State Graph",
    sublabel="Orchestration & routing",
    fill=NAVY_LIGHT, edge=PURPLE, fontsize=8)

box(ax, 2.5, 1.1, 3.6, 0.9, "Nurse Feedback Agent",
    sublabel="nurse_feedback_agent.py",
    fill=AMBER_DIM, edge=AMBER, label_color=WHITE, fontsize=8)

# ══════════════════════════════════════════════════════════════════════════════
# AGENT PIPELINE (middle column)
# ══════════════════════════════════════════════════════════════════════════════
px = 10.3

# Triage Orchestrator header
box(ax, px, 17.8, 4.8, 0.75, "🔀 Triage Orchestrator",
    sublabel="triage_orchestrator.py  |  LangGraph StateGraph",
    fill=TEAL_DIM, edge=TEAL, label_color=TEAL, fontsize=9, radius=0.3)

agents = [
    # (y,   label,                        sublabel,                              fill,        edge,   badge)
    (16.55, "1. US Triage Agent",          "us_triage_agent.py  |  ESI 1–5",      NAVY_LIGHT,  TEAL,   "ESI"),
    (15.25, "2. Clinical Workflow Agent",  "us_clinical_workflow.py",             NAVY_LIGHT,  BLUE,   None),
    (13.95, "3. Diagnostics Agent",        "diagnostics_agent.py",                NAVY_LIGHT,  BLUE,   None),
    (12.65, "4. Deterioration Agent",      "deterioration_agent.py  |  rule-based",NAVY_LIGHT, AMBER,  "🚨"),
    (11.35, "5. Queue Agent",              "queue_agent.py  |  dynamic priority", NAVY_LIGHT,  GREEN,  None),
    (10.05, "6. Specialist Agent",         "specialist_agent.py",                 NAVY_LIGHT,  PURPLE, None),
    (8.75,  "7. Appointment Agent",        "appointment_agent.py",                NAVY_LIGHT,  AMBER,  None),
    (7.45,  "8. Demand Forecasting Agent", "demand_forecasting_agent.py  |  Prophet", NAVY_LIGHT, RED,  "📈"),
]

EDGE_COLORS = [TEAL, BLUE, BLUE, AMBER, GREEN, PURPLE, AMBER, RED]

for (ay, al, asl, af, ae, ab) in agents:
    box(ax, px, ay, 4.8, 0.9, al, sublabel=asl,
        fill=af, edge=ae, fontsize=8.5,
        badge=ab, badge_color=ae if ab else TEAL)

# Sub-agents inside Clinical Workflow
sub_y = 15.25
box(ax, px - 1.15, sub_y - 0.0, 1.9, 0.62,
    "Clinical\nReasoning", fill=BLUE_DIM, edge=BLUE, fontsize=7, radius=0.2)
box(ax, px + 1.15, sub_y - 0.0, 1.9, 0.62,
    "Safety &\nVerification", fill=BLUE_DIM, edge=BLUE, fontsize=7, radius=0.2)

# Final result box
box(ax, px, 5.9, 4.8, 1.0, "✅  Final Triage Result",
    sublabel="patient_id · urgency · ESI · pathway · specialist · queue",
    fill=TEAL_DIM, edge=TEAL, label_color=TEAL, fontsize=9, radius=0.35)

# Sepsis inject note
box(ax, px, 4.7, 4.8, 0.7, "⚠️  Sepsis Context Injection",
    sublabel="Injected into pipeline when qSOFA ≥ 2",
    fill=RED_DIM, edge=RED, label_color=RED, fontsize=7.5, radius=0.25)

# ══════════════════════════════════════════════════════════════════════════════
# DATA STORE (right-middle)
# ══════════════════════════════════════════════════════════════════════════════
dx = 18.8

box(ax, dx, 17.8, 5.0, 0.75, "🗄️  In-Memory Triage Store",
    sublabel="_triage_store  {patient_id → result}",
    fill=AMBER_DIM, edge=AMBER, label_color=WHITE, fontsize=8)

csv_boxes = [
    (16.5, "patient_demographics.csv", NAVY_LIGHT, GRAY),
    (15.3, "past_medical_history.csv",  NAVY_LIGHT, GRAY),
    (14.1, "clinical_encounters.csv",   NAVY_LIGHT, GRAY),
    (12.9, "user_passwords.csv",        NAVY_LIGHT, GRAY),
    (11.7, "nurse_corrections.json",    NAVY_LIGHT, AMBER),
]
for cy, cl, cf, ce in csv_boxes:
    box(ax, dx, cy, 5.0, 0.75, cl, fill=cf, edge=ce, label_color=GRAY, fontsize=7.5)

# FastAPI server
box(ax, dx, 10.4, 5.0, 0.9, "⚙️  FastAPI Server",
    sublabel="api_server.py  |  port 8000  |  CORS",
    fill=NAVY_LIGHT, edge=GREEN, label_color=WHITE, fontsize=8.5)

# ── FRONTEND (right-bottom) ──────────────────────────────────────────────────
endpoints = [
    (9.0,  "POST /api/triage/assess",         GREEN),
    (8.1,  "GET  /api/triage/{id}/report",    TEAL),
    (7.2,  "POST /api/triage/approve",        AMBER),
    (6.3,  "GET  /api/queue",                 BLUE),
    (5.4,  "GET  /api/patients/profile",      BLUE),
    (4.5,  "GET  /api/appointments",          PURPLE),
    (3.6,  "GET  /api/referrals",             PURPLE),
    (2.7,  "GET  /api/analytics/summary",     RED),
    (1.8,  "GET  /api/analytics/forecast",    RED),
    (0.9,  "POST /api/auth/login",            GRAY),
]
for ey, el, ec in endpoints:
    box(ax, dx, ey, 5.0, 0.65, el, fill=NAVY_LIGHT, edge=ec,
        label_color=ec, fontsize=7, radius=0.2)

# ══════════════════════════════════════════════════════════════════════════════
# REACT NATIVE APP (far right)
# ══════════════════════════════════════════════════════════════════════════════
rx = 24.85

box(ax, rx, 17.8, 4.7, 0.75, "📱  MedflowAI App",
    sublabel="React Native / Expo Router",
    fill=BLUE_DIM, edge=BLUE, label_color=WHITE, fontsize=9)

# Patient side
box(ax, rx, 16.4, 4.7, 0.75, "👤  PATIENT SIDE",
    fill=TEAL_DIM, edge=TEAL, label_color=TEAL, fontsize=8.5)

patient_screens = [
    (15.45, "symptom-input.tsx",    TEAL),
    (14.55, "triage-result.tsx",    TEAL),
    (13.65, "approved-report.tsx",  TEAL),
    (12.75, "wait-time.tsx",        TEAL),
    (11.85, "records.tsx",          TEAL),
    (10.95, "book-appointment.tsx", TEAL),
    (10.05, "referrals.tsx",        TEAL),
    (9.15,  "home.tsx",             TEAL),
]
for sy, sl, sc in patient_screens:
    box(ax, rx, sy, 4.4, 0.65, sl, fill=NAVY_LIGHT, edge=sc,
        label_color=sc, fontsize=7.2, radius=0.2)

# Staff side
box(ax, rx, 8.0, 4.7, 0.75, "🏥  STAFF / CLINICIAN SIDE",
    fill=AMBER_DIM, edge=AMBER, label_color=AMBER, fontsize=8.5)

staff_screens = [
    (7.05,  "dashboard.tsx",       AMBER),
    (6.15,  "patient-queue.tsx",   AMBER),
    (5.25,  "patient-detail.tsx",  AMBER),
    (4.35,  "worklist.tsx",        AMBER),
    (3.45,  "analytics.tsx",       AMBER),
    (2.55,  "patient-search.tsx",  AMBER),
    (1.65,  "resource-alloc.tsx",  AMBER),
]
for sy, sl, sc in staff_screens:
    box(ax, rx, sy, 4.4, 0.65, sl, fill=NAVY_LIGHT, edge=sc,
        label_color=sc, fontsize=7.2, radius=0.2)

# AppContext
box(ax, rx, 0.75, 4.7, 0.75, "🔄  AppContext / State",
    sublabel="patientId · role · triageResult · profile",
    fill=PURPLE_DIM, edge=PURPLE, label_color=WHITE, fontsize=7.5)

# ══════════════════════════════════════════════════════════════════════════════
# ARROWS
# ══════════════════════════════════════════════════════════════════════════════

# Walk-in / EMS → Voice Transcription
arrow(ax, 2.5, 17.43, 2.5, 15.85, color=BLUE, label="audio/text")
arrow(ax, 2.5, 16.33, 2.5, 15.85, color=RED)

# Image → Voice Intake (optional path)
arrow(ax, 2.5, 13.65, 2.5, 13.25, color=PURPLE, label="image data")

# Voice Transcription → Voice Intake
arrow(ax, 2.5, 14.95, 2.5, 13.25, color=BLUE, label="transcript")

# Vitals → Sepsis Screener
arrow(ax, 2.5, 9.83, 2.5, 11.85, color=GRAY)

# Voice Intake → Sepsis Screener
arrow(ax, 2.5, 12.35, 2.5, 11.85, color=BLUE, label="symptoms")

# Sepsis Screener → LLM Provider region (sepsis signal)
arrow(ax, 4.3, 11.4, 5.1, 4.7, color=RED, lw=1.2, rad=-0.3, label="qSOFA result")

# Sepsis Screener → Orchestrator
arrow(ax, 3.7, 11.8, 7.85, 17.43, color=RED, lw=1.1, rad=0.25)

# Voice Intake → Orchestrator
arrow(ax, 3.7, 12.8, 7.85, 17.8, color=BLUE, lw=1.2, rad=0.15, label="intake result")

# Vitals → Orchestrator (wide arc)
arrow(ax, 4.3, 10.2, 7.85, 17.43, color=GRAY, lw=0.9, rad=0.3, label="vitals")

# LLM Provider → Orchestrator (feeds LLM)
arrow(ax, 4.3, 8.5, 7.85, 17.43, color=PURPLE, lw=1.1, rad=-0.15, label="LLM")

# LLM Factory → sub LLMs
for ly in llm_y:
    arrow(ax, 2.5, 8.05, 2.5, ly + 0.38, color=PURPLE, lw=0.9)

# sub LLMs → LangChain
for ly in llm_y:
    arrow(ax, 2.5, ly - 0.38, 2.5, 3.99, color=PURPLE, lw=0.8)

# LangChain → LangGraph
arrow(ax, 2.5, 3.1, 2.5, 2.79, color=PURPLE)

# LangGraph → Nurse Feedback
arrow(ax, 2.5, 1.9, 2.5, 1.54, color=AMBER)

# Nurse Feedback → Orchestrator (learning loop)
arrow(ax, 4.3, 1.1, 7.85, 17.43, color=AMBER, lw=1.0, rad=-0.25, label="bias adj.")

# Orchestrator → Agent 1
arrow(ax, px, 17.43, px, 17.0, color=TEAL)

# Agent → Agent down the chain
agent_ys = [16.55, 15.25, 13.95, 12.65, 11.35, 10.05, 8.75, 7.45]
for i in range(len(agent_ys) - 1):
    arrow(ax, px, agent_ys[i] - 0.45, px, agent_ys[i+1] + 0.45, color=TEAL, lw=1.5)

# Last agent → Final Result
arrow(ax, px, 7.0, px, 6.4, color=TEAL, lw=1.5, label="completed result")

# Final Result → Triage Store
arrow(ax, 12.7, 5.9, 16.3, 17.55, color=AMBER, lw=1.2, rad=-0.3, label="store result")

# Sepsis inject ← Sepsis Screener (already handled by Orchestrator path)
arrow(ax, px, 5.55, px, 5.05, color=RED, lw=1.0)

# Triage Store → FastAPI
arrow(ax, 18.8, 10.05, 18.8, 9.85, color=GREEN)

# FastAPI → endpoints (just one representative arrow)
arrow(ax, 18.8, 9.95, 18.8, 9.33, color=GREEN)

# Orchestrator → FastAPI (assess call)
arrow(ax, 12.7, 17.8, 16.3, 10.75, color=GREEN, lw=1.1, rad=0.2, label="assess result")

# FastAPI → React Native App
arrow(ax, 21.3, 10.4, 22.5, 17.55, color=BLUE, lw=1.5, rad=-0.1, label="REST API")

# AppContext ↔ screens (bi-directional)
arrow(ax, rx, 1.13, rx, 1.48, color=PURPLE, style="<->", lw=1.0)

# Triage Store → CSV data annotation
for cy, _, _, _ in csv_boxes:
    arrow(ax, 16.3, cy, 17.5, cy, color=GRAY, lw=0.7)

# ══════════════════════════════════════════════════════════════════════════════
# LEGEND
# ══════════════════════════════════════════════════════════════════════════════
lx, ly_start = 5.3, 3.8
ax.text(lx, ly_start + 0.1, "LEGEND", fontsize=8, color=GRAY,
        fontweight="bold", zorder=5)
legend_items = [
    (TEAL,   "Core pipeline / agent"),
    (BLUE,   "Entry / input layer"),
    (RED,    "Emergency / sepsis path"),
    (AMBER,  "Data store / feedback"),
    (GREEN,  "API / output"),
    (PURPLE, "LLM / orchestration"),
    (GRAY,   "Data files"),
]
for i, (lc, ll) in enumerate(legend_items):
    legend_item(ax, lx, ly_start - 0.40 - i * 0.38, lc, ll)

# Badge legend
ax.text(lx + 2.2, ly_start + 0.1, "BADGES", fontsize=8, color=GRAY,
        fontweight="bold", zorder=5)
badge_items = [("ESI", TEAL, "ESI 1–5 scoring"), ("opt", PURPLE, "Optional step"),
               ("🚨", AMBER, "Alert / escalation"), ("📈", RED, "ML model")]
for i, (b, bc, bl) in enumerate(badge_items):
    bx2, by2 = lx + 2.2, ly_start - 0.40 - i * 0.38
    circ = plt.Circle((bx2 + 0.14, by2 + 0.09), 0.15, color=bc, zorder=5)
    ax.add_patch(circ)
    ax.text(bx2 + 0.14, by2 + 0.09, b, ha="center", va="center",
            fontsize=5.5, color=BG, fontweight="bold", zorder=6)
    ax.text(bx2 + 0.38, by2 + 0.09, bl, fontsize=7, color=GRAY, va="center", zorder=5)

# Footer
ax.text(14, 0.15,
        "MedflowAI  ·  LangGraph multi-agent pipeline  ·  FastAPI  ·  React Native / Expo  ·  Gemini / Ollama / Claude",
        fontsize=7.5, color=GRAY, ha="center", va="center",
        alpha=0.7, zorder=5)

# ── Save ──────────────────────────────────────────────────────────────────────
out = "/Users/gayathriutla/Desktop/Projects/spinsci_traige/medflowai_architecture.png"
plt.savefig(out, dpi=180, bbox_inches="tight", facecolor=BG, pad_inches=0.15)
print(f"Saved → {out}")
