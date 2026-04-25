"""CrisisGrid AI — Emergency Dispatch Dashboard."""
import streamlit as st
import pandas as pd
import requests, json, math, random, time
from datetime import datetime, timezone, timedelta

BASE_URL = "http://localhost:8000"
IST = timezone(timedelta(hours=5, minutes=30))

# ── Import mock data ──
from mock_data import (
    MOCK_INCIDENTS, MOCK_RESOURCES,
    MOCK_DISPATCH_LOG, MOCK_TRANSCRIPTS, AGENT_REASONING,
)

# ── Page config ──
st.set_page_config(page_title="CrisisGrid AI", page_icon="🚨", layout="wide")

# ── Session state init ──
for k, v in [
    ("incidents", list(MOCK_INCIDENTS)),
    ("resources", list(MOCK_RESOURCES)),
    ("dispatch_log", list(MOCK_DISPATCH_LOG)),
    ("transcripts", list(MOCK_TRANSCRIPTS)),
    ("agent_reasoning", dict(AGENT_REASONING)),
    ("selected_incident", None),
    ("backend_online", False),
    ("new_call_flash", False),
    ("base_url", "http://localhost:8000"),
    ("live_feed", []),
    ("auto_mode", False),
    ("sim_index", 0),
]:
    if k not in st.session_state:
        st.session_state[k] = v

def transform_dispatch_log(dispatch_log):
    return [
        {**d, "route": " → ".join(str(x) for x in d["route"]) if isinstance(d.get("route"), list) else d.get("route", "")}
        for d in dispatch_log
    ]

def transform_resources(resources, dispatch_log):
    res_list = []
    for r in resources:
        new_r = r.copy()
        if new_r.get("status") == "DISPATCHED":
            # find latest dispatch
            unit_dispatches = [d for d in dispatch_log if d.get("unit_id") == new_r.get("id")]
            if unit_dispatches:
                latest = max(unit_dispatches, key=lambda x: x.get("timestamp", ""))
                eta = latest.get("eta", 0)
                new_r["eta"] = f"{eta:.1f} min" if isinstance(eta, (int, float)) else str(eta)
                new_r["incident"] = latest.get("incident_id", "")
        res_list.append(new_r)
    return res_list

# ── Check backend ──
def check_backend():
    base_url = st.session_state.base_url
    try:
        r = requests.get(f"{base_url}/state", timeout=2)
        if r.status_code == 200:
            st.session_state.backend_online = True
            data = r.json()
            incidents = data.get("incidents", [])
            for inc in incidents:
                if "status" not in inc: inc["status"] = "ACTIVE"
            if incidents:
                st.session_state.incidents = incidents
            dispatch_log = data.get("dispatch_log", [])
            if dispatch_log:
                st.session_state.dispatch_log = dispatch_log
            resources = data.get("resources", [])
            if resources:
                st.session_state.resources = resources
            if data.get("agent_reasoning"):
                st.session_state.agent_reasoning = data["agent_reasoning"]
            st.session_state.live_feed = data.get("live_feed", [])
        else:
            st.session_state.backend_online = False
    except Exception:
        st.session_state.backend_online = False

check_backend()

# ── CSS ──
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;600;700;900&display=swap');
.stApp {background:#0A0E1A!important;}
div[data-testid="stSidebar"]{background:#0F1629!important;border-right:1px solid #1E2D4A!important;}
h1,h2,h3,h4,h5,h6{font-family:'Inter',sans-serif!important;color:#fff!important;}
p,span,li,div{color:#C8D1E4;}
.top-bar{background:linear-gradient(135deg,#0F1629 0%,#131B33 100%);border:1px solid #1E2D4A;border-radius:8px;padding:12px 24px;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;}
.logo{font-family:'Inter',sans-serif;font-weight:900;font-size:28px;color:#00D4FF;text-shadow:0 0 20px rgba(0,212,255,0.5),0 0 40px rgba(0,212,255,0.2);letter-spacing:2px;}
.logo-sub{font-size:11px;color:#8E9BB5;letter-spacing:3px;text-transform:uppercase;}
.stat-box{background:#0F1629;border:1px solid #1E2D4A;border-radius:6px;padding:10px 16px;text-align:center;min-width:120px;}
.stat-val{font-family:'JetBrains Mono',monospace;font-size:24px;font-weight:700;color:#00D4FF;}
.stat-lbl{font-size:10px;color:#8E9BB5;text-transform:uppercase;letter-spacing:1px;margin-top:2px;}
.clock{font-family:'JetBrains Mono',monospace;font-size:20px;color:#fff;text-shadow:0 0 10px rgba(255,255,255,0.3);}
.sys-status{font-family:'JetBrains Mono',monospace;font-size:12px;padding:6px 14px;border-radius:20px;letter-spacing:1px;}
.sys-online{background:rgba(48,209,88,0.15);color:#30D158;border:1px solid rgba(48,209,88,0.3);}
.sys-offline{background:rgba(255,45,85,0.15);color:#FF2D55;border:1px solid rgba(255,45,85,0.3);}
.incident-card{background:#0F1629;border:1px solid #1E2D4A;border-radius:8px;padding:12px;margin-bottom:8px;cursor:pointer;transition:all 0.2s;}
.incident-card:hover{border-color:#00D4FF;box-shadow:0 0 15px rgba(0,212,255,0.1);}
.incident-card.critical{border-left:3px solid #FF2D55;}
.incident-card.medium{border-left:3px solid #FF9500;}
.incident-card.low{border-left:3px solid #30D158;}
.badge{font-family:'JetBrains Mono',monospace;font-size:10px;padding:2px 8px;border-radius:10px;font-weight:700;letter-spacing:1px;display:inline-block;}
.badge-critical{background:rgba(255,45,85,0.2);color:#FF2D55;border:1px solid rgba(255,45,85,0.4);}
.badge-medium{background:rgba(255,149,0,0.2);color:#FF9500;border:1px solid rgba(255,149,0,0.4);}
.badge-low{background:rgba(48,209,88,0.2);color:#30D158;border:1px solid rgba(48,209,88,0.4);}
.badge-dispatched{background:rgba(255,45,85,0.2);color:#FF2D55;border:1px solid rgba(255,45,85,0.4);}
.badge-available{background:rgba(48,209,88,0.2);color:#30D158;border:1px solid rgba(48,209,88,0.4);}
.resource-card{background:#0F1629;border:1px solid #1E2D4A;border-radius:8px;padding:10px;margin-bottom:6px;}
.terminal-box{background:#080C15;border:1px solid #1E2D4A;border-radius:6px;padding:14px;font-family:'JetBrains Mono',monospace;font-size:12px;color:#30D158;white-space:pre-wrap;line-height:1.6;max-height:400px;overflow-y:auto;}
.section-hdr{font-family:'Inter',sans-serif;font-size:14px;color:#8E9BB5;text-transform:uppercase;letter-spacing:2px;margin-bottom:10px;padding-bottom:6px;border-bottom:1px solid #1E2D4A;}
.pulse-dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:#FF2D55;margin-right:6px;animation:pulse 1.5s infinite;}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(255,45,85,0.7);}70%{box-shadow:0 0 0 8px rgba(255,45,85,0);}100%{box-shadow:0 0 0 0 rgba(255,45,85,0);}}
.flash-banner{background:linear-gradient(90deg,rgba(255,45,85,0.2),rgba(255,149,0,0.2));border:1px solid #FF2D55;border-radius:6px;padding:10px;text-align:center;font-family:'JetBrains Mono',monospace;color:#FF2D55;animation:flashpulse 1s 3;}
@keyframes flashpulse{0%,100%{opacity:1;}50%{opacity:0.5;}}
.offline-banner{background:rgba(255,45,85,0.1);border:1px solid rgba(255,45,85,0.3);border-radius:6px;padding:8px 16px;text-align:center;font-family:'JetBrains Mono',monospace;font-size:12px;color:#FF9500;margin-bottom:10px;}
.transcript-box{background:#080C15;border:1px solid #1E2D4A;border-radius:6px;padding:12px;font-family:'JetBrains Mono',monospace;font-size:12px;color:#C8D1E4;line-height:1.5;}
.transcript-orig{color:#FF9500;}
.transcript-proc{color:#00D4FF;}
div[data-testid="stTabs"] button{color:#8E9BB5!important;font-family:'Inter',sans-serif!important;border-bottom-color:#1E2D4A!important;}
div[data-testid="stTabs"] button[aria-selected="true"]{color:#00D4FF!important;border-bottom-color:#00D4FF!important;}
div[data-testid="stExpander"]{background:#0F1629!important;border:1px solid #1E2D4A!important;border-radius:8px!important;}
.stDataFrame{font-family:'JetBrains Mono',monospace!important;}
div[data-testid="stDataFrame"] td,div[data-testid="stDataFrame"] th{background:#0F1629!important;color:#C8D1E4!important;border-color:#1E2D4A!important;font-size:12px!important;}
</style>""", unsafe_allow_html=True)

# ── Helpers ──
def sev_badge(s):
    c = {"CRITICAL":"critical","MEDIUM":"medium","LOW":"low"}.get(s,"low")
    dot = '<span class="pulse-dot"></span>' if s == "CRITICAL" else ""
    return f'{dot}<span class="badge badge-{c}">{s}</span>'

def status_badge(s):
    c = "dispatched" if s == "DISPATCHED" else "available"
    return f'<span class="badge badge-{c}">{s}</span>'

def type_icon(t):
    return {"Fire":"🔥","Flood":"🌊","Earthquake":"🏚️","Accident":"💥","Medical":"🚑"}.get(t, {"fire":"🔥","flood":"🌊","earthquake":"🏚️","accident":"💥","medical":"🚑"}.get(str(t).lower(),"⚠️"))

# ── TOP BAR ──
now_ist = datetime.now(IST)
active = sum(1 for i in st.session_state.incidents if i.get("status") == "ACTIVE")
deployed = sum(1 for r in st.session_state.resources if r.get("status") == "DISPATCHED")
calls = sum(i.get("calls_merged", 1) for i in st.session_state.incidents)

st.markdown(f"""<div class="top-bar">
<div><div class="logo">🚨 CrisisGrid AI</div><div class="logo-sub">Autonomous Multi-Agent Emergency Dispatch</div></div>
<div class="clock">{now_ist.strftime("%H:%M:%S")} IST</div>
<div class="{'sys-status sys-online' if st.session_state.backend_online else 'sys-status sys-offline'}">
{'● ALL AGENTS ACTIVE' if st.session_state.backend_online else '○ DEMO MODE — BACKEND OFFLINE'}</div>
<div style="display:flex;gap:12px;">
<div class="stat-box"><div class="stat-val" style="color:#FF2D55;">{active}</div><div class="stat-lbl">Active Incidents</div></div>
<div class="stat-box"><div class="stat-val" style="color:#FF9500;">{deployed}</div><div class="stat-lbl">Units Deployed</div></div>
<div class="stat-box"><div class="stat-val">{calls}</div><div class="stat-lbl">Calls Processed</div></div>
</div></div>""", unsafe_allow_html=True)

if not st.session_state.backend_online:
    st.markdown('<div class="offline-banner">⚠ Backend Offline — Running in Demo Mode with mock data</div>', unsafe_allow_html=True)
if st.session_state.new_call_flash:
    st.markdown('<div class="flash-banner">📞 NEW CALL INCOMING — Processing through agents...</div>', unsafe_allow_html=True)
    st.session_state.new_call_flash = False

# ── LIVE SYSTEM FEED ──
if st.session_state.live_feed:
    feed_html = '<div style="background:#080C15;border:1px solid #1E2D4A;border-radius:6px;padding:10px;margin-bottom:12px;font-family:JetBrains Mono,monospace;font-size:12px;">'
    for evt in st.session_state.live_feed[:5]:
        feed_html += f'<div style="color:#00D4FF;margin-bottom:4px;">{evt}</div>'
    feed_html += '</div>'
    st.markdown(feed_html, unsafe_allow_html=True)

# ── SIDEBAR ──
with st.sidebar:
    st.markdown('<div class="logo" style="font-size:20px;margin-bottom:4px;">📡 DISPATCH CONSOLE</div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown('<div class="section-hdr">Connection</div>', unsafe_allow_html=True)

    def update_base_url():
        st.session_state.base_url = st.session_state.temp_base_url
        check_backend()

    st.text_input("BASE URL", value=st.session_state.base_url, key="temp_base_url", on_change=update_base_url)

    st.markdown("---")
    st.markdown('<div class="section-hdr">Submit 112 Call</div>', unsafe_allow_html=True)
    transcript_input = st.text_area("Enter emergency call transcript:", height=120, placeholder="e.g. Bhai jaldi aao, yahan aag lagi hai...")
    if st.button("Process Call", use_container_width=True, type="primary"):
        if transcript_input.strip():
            st.session_state.new_call_flash = True
            try:
                r = requests.post(f"{st.session_state.base_url}/process-call", json={"transcript": transcript_input}, timeout=30)
                if r.status_code == 200:
                    data = r.json()
                    st.session_state.incidents = data.get("incidents", st.session_state.incidents)
                    st.session_state.dispatch_log = data.get("dispatch_log", st.session_state.dispatch_log)
                    st.session_state.resources = data.get("resources", st.session_state.resources)
                    if data.get("agent_reasoning"):
                        st.session_state.agent_reasoning = data["agent_reasoning"]
                    st.session_state.live_feed = data.get("live_feed", [])
                    latest_id = st.session_state.incidents[-1]["id"] if st.session_state.incidents else "N/A"
                    st.session_state.transcripts.append({
                        "original": transcript_input,
                        "processed": f"Processed via LangGraph backend. Incident: {latest_id}",
                        "incident_id": latest_id
                    })
                    st.success("✅ Dispatched via backend!")
                else:
                    raise Exception("Bad response")
            except Exception:
                sev = "CRITICAL" if any(w in transcript_input.lower() for w in ["jaldi","critical","fas","trapped","blast","explosion"]) else "MEDIUM"
                new_inc = {
                    "id": f"INC-{len(st.session_state.incidents)+1:03d}",
                    "location": "Downtown",
                    "type": "Fire" if "aag" in transcript_input.lower() or "fire" in transcript_input.lower() else "Accident" if "accident" in transcript_input.lower() else "Medical" if "ambulance" in transcript_input.lower() or "medical" in transcript_input.lower() else "Flood" if "pani" in transcript_input.lower() else "Emergency",
                    "severity": sev,
                    "time": now_ist.strftime("%H:%M:%S"),
                    "timestamp": now_ist.strftime("%Y-%m-%d %H:%M:%S"),
                    "description": "New incident from 112 call — backend offline",
                    "calls_merged": 1,
                    "status": "ACTIVE",
                    "units": [],
                    "escalated": False,
                }
                st.session_state.incidents.append(new_inc)
                st.session_state.transcripts.append({
                    "original": transcript_input,
                    "processed": f"EMERGENCY: {new_inc['type']} at {new_inc['location']}. Severity: {new_inc['severity']}.",
                    "incident_id": new_inc["id"]
                })
                st.info("📡 Backend offline — processed with mock pipeline")
            st.rerun()

    st.markdown("---")
    st.markdown('<div class="section-hdr">Quick Actions</div>', unsafe_allow_html=True)
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        if st.button("🔄 Refresh", use_container_width=True):
            check_backend()
            st.rerun()
    with col_r2:
        if st.button("🔄 Reset", use_container_width=True):
            try:
                r = requests.post(f"{st.session_state.base_url}/reset", timeout=5)
                if r.status_code == 200:
                    check_backend()
                    st.toast("✅ State reset")
                    st.rerun()
            except Exception:
                st.toast("⚠ Backend offline")

    if st.session_state.backend_online:
        if st.button("🎬 Run Test Scenario", use_container_width=True):
            try:
                r = requests.post(f"{st.session_state.base_url}/run-scenario", timeout=120)
                if r.status_code == 200:
                    data = r.json().get("final_state", {})
                    st.session_state.incidents = data.get("incidents", st.session_state.incidents)
                    st.session_state.dispatch_log = data.get("dispatch_log", st.session_state.dispatch_log)
                    st.session_state.resources = data.get("resources", st.session_state.resources)
                    if data.get("agent_reasoning"):
                        st.session_state.agent_reasoning = data["agent_reasoning"]
                    st.session_state.live_feed = data.get("live_feed", [])
                    st.toast("✅ Scenario complete!")
                    st.rerun()
            except Exception as e:
                st.toast(f"⚠ Scenario error: {e}")

    st.markdown("---")
    st.markdown('<div class="section-hdr">🔥 Live Simulation</div>', unsafe_allow_html=True)
    if st.session_state.auto_mode:
        if st.button("⏹ Stop Simulation", use_container_width=True, type="secondary"):
            st.session_state.auto_mode = False
            st.rerun()
        st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:11px;color:#30D158;">● Simulation running...</div>', unsafe_allow_html=True)
    else:
        if st.button("▶ Start Live Simulation", use_container_width=True, type="primary"):
            st.session_state.auto_mode = True
            st.session_state.sim_index = 0
            st.rerun()

    st.markdown("---")
    # Stats box
    n_critical = sum(1 for i in st.session_state.incidents if i.get("severity") == "CRITICAL")
    n_deployed = sum(1 for r in st.session_state.resources if r.get("status") == "DISPATCHED")
    util_pct = int(n_deployed / max(len(st.session_state.resources), 1) * 100)
    util_color = "#FF2D55" if util_pct >= 75 else "#FF9500" if util_pct >= 50 else "#30D158"
    st.markdown(f"""<div style="font-family:'JetBrains Mono',monospace;font-size:11px;color:#8E9BB5;line-height:2.0;">
    Agents: Triage / Fusion / Dispatch / Strategy<br>
    Resources: {len(st.session_state.resources)} units ({n_deployed} deployed)<br>
    Utilization: <span style="color:{util_color};font-weight:700;">{util_pct}%</span><br>
    CRITICAL active: <span style="color:#FF2D55;">{n_critical}</span><br>
    API: {st.session_state.base_url}<br>
    Last sync: {now_ist.strftime("%H:%M:%S")} IST
    </div>""", unsafe_allow_html=True)

# ── MAIN 3-COL LAYOUT ──
col_left, col_center, col_right = st.columns([1, 2, 1])

# ── LEFT: Incident Feed ──
with col_left:
    st.markdown('<div class="section-hdr">🔴 Real-time Incident Queue</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:9px;color:#30D158;font-family:JetBrains Mono,monospace;margin-bottom:6px;">PRIORITY ENGINE: Critical incidents handled first</div>', unsafe_allow_html=True)
    sev_order = {"CRITICAL": 0, "MEDIUM": 1, "LOW": 2}
    sorted_incidents = sorted(st.session_state.incidents, key=lambda x: sev_order.get(x.get("severity","LOW"), 3))
    for idx, inc in enumerate(sorted_incidents):
        sev_class = inc.get("severity","LOW").lower()
        is_selected = st.session_state.selected_incident == inc["id"]
        border_extra = "border-color:#00D4FF!important;box-shadow:0 0 20px rgba(0,212,255,0.2);" if is_selected else ""
        inc_time = inc.get("time", inc.get("timestamp", ""))
        if " " in str(inc_time): inc_time = str(inc_time).split(" ")[1]
        inc_desc = inc.get("description", "")[:80]
        units_list = inc.get("units", [])
        units_str = ", ".join(units_list) if units_list else "Pending"
        calls_merged = inc.get("calls_merged", 1)
        merged_badge = f'<span style="font-family:JetBrains Mono,monospace;font-size:9px;background:rgba(0,212,255,0.15);color:#00D4FF;border:1px solid rgba(0,212,255,0.3);border-radius:8px;padding:1px 6px;">{calls_merged} calls</span>' if calls_merged > 1 else ""
        escalated_badge = '<span style="font-family:JetBrains Mono,monospace;font-size:9px;background:rgba(255,149,0,0.2);color:#FF9500;border:1px solid rgba(255,149,0,0.4);border-radius:8px;padding:1px 6px;">⬆ ESCALATED</span>' if inc.get("escalated") else ""
        rerouted_units = [d for d in st.session_state.dispatch_log if (d.get("incident") == inc["id"] or d.get("incident_id") == inc["id"]) and "REROUTED" in d.get("status","")]
        reroute_badge = '<span style="font-family:JetBrains Mono,monospace;font-size:9px;background:rgba(255,45,85,0.2);color:#FF2D55;border:1px solid rgba(255,45,85,0.4);border-radius:8px;padding:1px 6px;">🔄 REROUTED</span>' if rerouted_units else ""
        st.markdown(f"""<div class="incident-card {sev_class}" style="{border_extra}">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px;">
        <span style="font-family:'JetBrains Mono',monospace;font-size:12px;color:#00D4FF;">{inc['id']}</span>
        <div style="display:flex;gap:4px;align-items:center;">{merged_badge}{escalated_badge}{reroute_badge}{sev_badge(inc.get('severity','LOW'))}</div>
        </div>
        <div style="font-size:14px;color:#fff;font-weight:600;margin-bottom:4px;">{type_icon(inc.get('type',''))} {inc.get('type','')} — {inc.get('location','')}</div>
        <div style="font-size:11px;color:#8E9BB5;margin-bottom:4px;">{inc_desc}</div>
        <div style="font-size:10px;color:#8E9BB5;margin-bottom:2px;">🚑 Units: {units_str}</div>
        <div style="display:flex;justify-content:space-between;font-size:10px;color:#8E9BB5;">
        <span>🕐 {inc_time}</span>
        <span>Status: {inc.get('status','ACTIVE')}</span>
        </div></div>""", unsafe_allow_html=True)
        if st.button(f"Select", key=f"sel_{idx}", use_container_width=True):
            st.session_state.selected_incident = inc["id"]
            st.toast(f"🎯 Tracking {inc['id']}")
            st.rerun()

# ── CENTER: City Map + Incident Panel ──
LOCATION_COORDS = {
    "Karol Bagh": [28.6514, 77.1907], "Connaught Place": [28.6315, 77.2167],
    "ITO": [28.6285, 77.2410], "Dwarka": [28.5921, 77.0460],
    "Rohini": [28.7495, 77.0565], "Lajpat Nagar": [28.5700, 77.2400],
    "Saket": [28.5244, 77.2066], "Nehru Place": [28.5491, 77.2533],
    "Rajouri Garden": [28.6492, 77.1219], "Janakpuri": [28.6219, 77.0878],
    "Vasant Kunj": [28.5195, 77.1539], "Chandni Chowk": [28.6506, 77.2303],
    # City graph zone names
    "Downtown": [28.6315, 77.2167], "downtown": [28.6315, 77.2167],
    "Harbor": [28.6285, 77.2410], "harbor": [28.6285, 77.2410],
    "Industrial": [28.5491, 77.2533], "industrial": [28.5491, 77.2533],
    "Sector7": [28.6219, 77.0878], "sector7": [28.6219, 77.0878],
    "North Grid": [28.7495, 77.0565], "north_grid": [28.7495, 77.0565],
    "Central Park": [28.5700, 77.2400], "central_park": [28.5700, 77.2400],
    "Westside": [28.6492, 77.1219], "westside": [28.6492, 77.1219],
    "Port": [28.5921, 77.0460], "port": [28.5921, 77.0460],
    "Eastside": [28.5244, 77.2066], "eastside": [28.5244, 77.2066],
    "Suburbs": [28.5195, 77.1539], "suburbs": [28.5195, 77.1539],
    "Midtown": [28.6506, 77.2303], "midtown": [28.6506, 77.2303],
    "Airport": [28.5562, 77.1000], "airport": [28.5562, 77.1000],
}

with col_center:
    st.markdown('<div class="section-hdr">🗺️ Delhi Emergency Grid — Live Map</div>', unsafe_allow_html=True)
    sel_id = st.session_state.selected_incident
    map_data = []
    for inc in st.session_state.incidents:
        loc = inc.get("location", "")
        coords = LOCATION_COORDS.get(loc)
        if coords:
            map_data.append({"lat": coords[0], "lon": coords[1], "incident": inc["id"], "type": inc.get("type", "")})
    if sel_id:
        sel_data = [m for m in map_data if m["incident"] == sel_id]
        if sel_data:
            df_map = pd.DataFrame(sel_data)
            st.map(df_map, latitude="lat", longitude="lon", zoom=12, use_container_width=True)
        elif map_data:
            df_map = pd.DataFrame(map_data)
            st.map(df_map, latitude="lat", longitude="lon", zoom=11, use_container_width=True)
        else:
            st.info("No incidents with mapped locations yet.")
    elif map_data:
        df_map = pd.DataFrame(map_data)
        st.map(df_map, latitude="lat", longitude="lon", zoom=11, use_container_width=True)
    else:
        st.info("No active incidents to display on map.")

    # ── Incident Control Panel ──
    if sel_id:
        sel_inc = next((i for i in st.session_state.incidents if i["id"] == sel_id), None)
        if sel_inc:
            sev = sel_inc.get('severity', 'LOW')
            sev_color = {"CRITICAL": "#FF2D55", "MEDIUM": "#FF9500", "LOW": "#30D158"}.get(sev, "#8E9BB5")
            units_list = sel_inc.get("units", [])
            units_str = ", ".join(units_list) if units_list else "None assigned"
            desc = sel_inc.get("description", "No description")
            inc_time = sel_inc.get("time", sel_inc.get("timestamp", ""))
            st.markdown(f"""<div style="background:#0F1629;border:1px solid {sev_color};border-radius:8px;padding:16px;margin-top:10px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
            <span style="font-family:'JetBrains Mono',monospace;font-size:16px;color:#00D4FF;font-weight:700;">🔍 {sel_inc['id']}</span>
            <span style="font-family:'JetBrains Mono',monospace;font-size:11px;color:{sev_color};border:1px solid {sev_color};border-radius:10px;padding:2px 10px;">{sev}</span>
            </div>
            <div style="color:#fff;font-weight:600;font-size:15px;margin-bottom:6px;">{type_icon(sel_inc.get('type',''))} {sel_inc.get('type','')} — {sel_inc.get('location','')}</div>
            <div style="color:#C8D1E4;font-size:12px;margin-bottom:8px;">{desc}</div>
            <div style="display:flex;gap:20px;font-size:11px;color:#8E9BB5;">
            <span>🕐 {inc_time}</span>
            <span>🚑 {units_str}</span>
            <span>📊 Status: {sel_inc.get('status','ACTIVE')}</span>
            </div></div>""", unsafe_allow_html=True)

            # Filtered dispatch log for this incident
            inc_dispatches = [d for d in st.session_state.dispatch_log if d.get("incident") == sel_id or d.get("incident_id") == sel_id]
            if inc_dispatches:
                st.markdown(f'<div style="font-size:11px;color:#8E9BB5;margin-top:8px;">📋 Dispatch entries for {sel_id}:</div>', unsafe_allow_html=True)
                df_disp = pd.DataFrame(inc_dispatches)
                df_disp.columns = [c.upper().replace("_"," ") for c in df_disp.columns]
                st.dataframe(df_disp, use_container_width=True, hide_index=True, height=150)
                # Show route text
                for d in inc_dispatches:
                    route = d.get("route", d.get("ROUTE", ""))
                    if route:
                        st.markdown(f'<div style="font-size:11px;color:#00D4FF;font-family:JetBrains Mono,monospace;margin-top:4px;">🚨 Route: {route}</div>', unsafe_allow_html=True)
        if st.button("✖ Clear Selection", use_container_width=True):
            st.session_state.selected_incident = None
            st.rerun()

# ── RIGHT: Resource Status ──
with col_right:
    st.markdown('<div class="section-hdr">📦 Resource Status</div>', unsafe_allow_html=True)
    type_map = {"ambulance": "🚑 Ambulances", "fire_truck": "🚒 Fire Trucks", "police": "🚔 Police Vans",
                "Ambulance": "🚑 Ambulances", "Fire Truck": "🚒 Fire Trucks", "Police Van": "🚔 Police Vans"}
    seen_types = []
    for res in st.session_state.resources:
        rtype = res.get("type", "")
        label = type_map.get(rtype, rtype)
        if label not in seen_types:
            seen_types.append(label)
            st.markdown(f"<div style='font-size:12px;color:#8E9BB5;margin:8px 0 4px;font-weight:600;'>{label}</div>", unsafe_allow_html=True)
        status = res.get("status", "AVAILABLE")
        eta_val = res.get("eta_display", res.get("eta", ""))
        eta_txt = f"<span style='color:#FF9500;'>ETA: {eta_val}</span>" if status == "DISPATCHED" and eta_val else ""
        inc_val = res.get("assigned_incident", res.get("incident", ""))
        inc_txt = f"<span style='color:#FF2D55;font-size:10px;'>→ {inc_val}</span>" if status == "DISPATCHED" and inc_val else ""
        loc = res.get("location", "").replace("_", " ").title()
        st.markdown(f"""<div class="resource-card">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
            <span style="font-family:'JetBrains Mono',monospace;font-size:12px;color:#fff;font-weight:700;">{res.get('id','')}</span>
            {status_badge(status)}
            </div>
            <div style="font-size:11px;color:#8E9BB5;">📍 {loc} {eta_txt}</div>
            <div>{inc_txt}</div>
            </div>""", unsafe_allow_html=True)

# ── BOTTOM TABS ──
st.markdown("---")
tab1, tab2, tab3, tab4 = st.tabs(["📋 Dispatch Log", "🧠 Agent Reasoning", "📞 Raw Transcripts", "⚠️ Alerts"])

with tab1:
    sel_filter = st.session_state.selected_incident
    if st.session_state.dispatch_log:
        display_log = st.session_state.dispatch_log
        if sel_filter:
            filtered = [d for d in display_log if d.get("incident") == sel_filter or d.get("incident_id") == sel_filter]
            if filtered:
                st.markdown(f'<div style="font-size:11px;color:#00D4FF;margin-bottom:6px;">Showing dispatches for {sel_filter}</div>', unsafe_allow_html=True)
                display_log = filtered
            else:
                st.info(f"No dispatch entries for {sel_filter} — showing all")
        # Highlight rerouted entries
        rerouted_count = sum(1 for d in display_log if "REROUTED" in d.get("status", ""))
        if rerouted_count:
            st.markdown(f'<div style="font-family:JetBrains Mono,monospace;font-size:11px;color:#FF2D55;margin-bottom:6px;">🔄 {rerouted_count} dynamic reroute(s) in log</div>', unsafe_allow_html=True)
        df = pd.DataFrame(display_log)
        # Keep only key columns
        show_cols = [c for c in ["time","incident","unit","severity","route","eta","status","rerouted_from"] if c in df.columns]
        df = df[show_cols]
        df.columns = [c.upper().replace("_"," ") for c in df.columns]
        st.dataframe(df, use_container_width=True, hide_index=True, height=280)
    else:
        st.info("No dispatch activity yet.")

with tab2:
    agent_order = ["Triage Agent", "Fusion Agent", "Dispatch Agent", "Strategy Agent"]
    icons = {"Triage Agent": "🔍", "Fusion Agent": "🔗", "Dispatch Agent": "🚀", "Strategy Agent": "🧠"}
    for agent in agent_order:
        reasoning = st.session_state.agent_reasoning.get(agent, "")
        if not reasoning:
            continue
        icon = icons.get(agent, "⚙️")
        expanded = agent in ("Dispatch Agent", "Strategy Agent")
        with st.expander(f"{icon} {agent}", expanded=expanded):
            st.markdown(f'<div class="terminal-box">{reasoning}</div>', unsafe_allow_html=True)

with tab3:
    if not st.session_state.transcripts:
        st.info("No transcripts yet.")
    for t in reversed(st.session_state.transcripts[-10:]):  # show last 10, newest first
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"<div style='font-size:11px;color:#8E9BB5;margin-bottom:4px;'>ORIGINAL — {t['incident_id']}</div>", unsafe_allow_html=True)
            st.markdown(f'<div class="transcript-box"><span class="transcript-orig">{t["original"]}</span></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div style='font-size:11px;color:#8E9BB5;margin-bottom:4px;'>PROCESSED OUTPUT</div>", unsafe_allow_html=True)
            st.markdown(f'<div class="transcript-box"><span class="transcript-proc">{t["processed"]}</span></div>', unsafe_allow_html=True)
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

with tab4:
    alerts = st.session_state.agent_reasoning.get("Strategy Agent", "")
    # Also show any alerts from live feed
    critical_alerts = [e for e in st.session_state.live_feed if "⚠️" in e or "REROUTE" in e or "ESCALAT" in e or "NO AVAILABLE" in e]
    if critical_alerts:
        st.markdown('<div class="section-hdr">🚨 System Alerts</div>', unsafe_allow_html=True)
        for alert in critical_alerts[:10]:
            color = "#FF2D55" if "ESCALAT" in alert or "NO AVAILABLE" in alert or "REROUTE" in alert else "#FF9500"
            st.markdown(f'<div style="font-family:JetBrains Mono,monospace;font-size:12px;color:{color};background:rgba(255,45,85,0.05);border:1px solid {color}33;border-radius:4px;padding:8px;margin-bottom:6px;">{alert}</div>', unsafe_allow_html=True)
    if alerts:
        st.markdown('<div class="section-hdr" style="margin-top:12px;">🧠 Strategy Agent Assessment</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="terminal-box">{alerts}</div>', unsafe_allow_html=True)
    if not critical_alerts and not alerts:
        st.info("No alerts. System operating normally.")

# ── Auto-refresh + Live Simulation ──
try:
    from streamlit_autorefresh import st_autorefresh
    if st.session_state.auto_mode:
        st_autorefresh(interval=3000, limit=None, key="sim_refresh")
    else:
        st_autorefresh(interval=10000, limit=None, key="auto_refresh")
except ImportError:
    pass

# ── Live Simulation Logic ──
if st.session_state.auto_mode and st.session_state.backend_online:
    try:
        mock_calls_cache = getattr(st.session_state, "_mock_calls_cache", None)
        if mock_calls_cache is None:
            mock_resp = requests.get(f"{st.session_state.base_url}/mock-calls", timeout=2)
            if mock_resp.status_code == 200:
                mock_calls_cache = mock_resp.json().get("calls", [])
                st.session_state._mock_calls_cache = mock_calls_cache

        if mock_calls_cache:
            idx = st.session_state.sim_index % len(mock_calls_cache)
            call = mock_calls_cache[idx]
            st.session_state.sim_index = idx + 1

            r = requests.post(
                f"{st.session_state.base_url}/process-call",
                json={"transcript": call},
                timeout=30,
            )
            if r.status_code == 200:
                data = r.json()
                st.session_state.incidents = data.get("incidents", st.session_state.incidents)
                st.session_state.dispatch_log = data.get("dispatch_log", st.session_state.dispatch_log)
                st.session_state.resources = data.get("resources", st.session_state.resources)
                if data.get("agent_reasoning"):
                    st.session_state.agent_reasoning = data["agent_reasoning"]
                st.session_state.live_feed = data.get("live_feed", [])
                latest_id = st.session_state.incidents[-1]["id"] if st.session_state.incidents else "N/A"
                st.session_state.transcripts.append({
                    "original": f"[SIM {idx+1}] {call[:120]}...",
                    "processed": f"Auto-dispatched via LangGraph pipeline. Incident: {latest_id}",
                    "incident_id": latest_id,
                })
    except Exception:
        pass
