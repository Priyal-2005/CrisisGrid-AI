"""CrisisGrid AI — Emergency Dispatch Dashboard."""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import requests, json, math
from datetime import datetime, timezone, timedelta

BASE_URL = "http://localhost:8000"
IST = timezone(timedelta(hours=5, minutes=30))

# ── Import mock data ──
from mock_data import (
    DELHI_LOCATIONS, EDGES, MOCK_INCIDENTS, MOCK_RESOURCES,
    MOCK_DISPATCH_LOG, MOCK_TRANSCRIPTS, AGENT_REASONING, DISPATCH_ROUTES,
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
<div><div class="logo">🚨 CRISISGRID AI</div><div class="logo-sub">Autonomous Multi-Agent Emergency Dispatch</div></div>
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
                    if data.get("incidents"):
                        st.session_state.incidents = data["incidents"]
                    if data.get("dispatch_log"):
                        st.session_state.dispatch_log = data["dispatch_log"]
                    if data.get("resources"):
                        st.session_state.resources = data["resources"]
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
                new_inc = {
                    "id": f"INC-{len(st.session_state.incidents)+1:03d}",
                    "location": "Chandni Chowk",
                    "type": "Fire" if "aag" in transcript_input.lower() else "Accident" if "accident" in transcript_input.lower() else "Flood" if "pani" in transcript_input.lower() else "Earthquake",
                    "severity": "CRITICAL" if any(w in transcript_input.lower() for w in ["jaldi","critical","fas","trapped"]) else "MEDIUM",
                    "time": now_ist.strftime("%H:%M:%S"),
                    "description": "New incident from 112 call",
                    "calls_merged": 1,
                    "status": "ACTIVE",
                    "units": [],
                }
                st.session_state.incidents.append(new_inc)
                st.session_state.transcripts.append({"original": transcript_input, "processed": f"EMERGENCY: {new_inc['type']} at {new_inc['location']}. Severity: {new_inc['severity']}.", "incident_id": new_inc["id"]})
                st.info("📡 Backend offline — processed with mock pipeline")
            st.rerun()
    st.markdown("---")
    st.markdown('<div class="section-hdr">Quick Actions</div>', unsafe_allow_html=True)
    if st.button("🔄 Refresh Data", use_container_width=True):
        check_backend()
        st.rerun()
    st.markdown("---")
    st.markdown('<div class="section-hdr">System Info</div>', unsafe_allow_html=True)
    st.markdown(f"""<div style="font-family:'JetBrains Mono',monospace;font-size:11px;color:#8E9BB5;line-height:1.8;">
    Agents: 4 (Triage/Fusion/Dispatch/Strategy)<br>
    Resources: {len(st.session_state.resources)} units<br>
    Coverage: Delhi NCR<br>
    API: {st.session_state.base_url}<br>
    Last sync: {now_ist.strftime("%H:%M:%S")} IST
    </div>""", unsafe_allow_html=True)

# ── MAIN 3-COL LAYOUT ──
col_left, col_center, col_right = st.columns([1, 2, 1])

# ── LEFT: Incident Feed ──
with col_left:
    st.markdown('<div class="section-hdr">🔴 Live Incident Feed</div>', unsafe_allow_html=True)
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
        st.markdown(f"""<div class="incident-card {sev_class}" style="{border_extra}">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
        <span style="font-family:'JetBrains Mono',monospace;font-size:12px;color:#00D4FF;">{inc['id']}</span>
        {sev_badge(inc.get('severity','LOW'))}
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
            st.rerun()

# ── CENTER: City Map ──
with col_center:
    st.markdown('<div class="section-hdr">🗺️ Delhi Emergency Grid — Live Map</div>', unsafe_allow_html=True)
    fig = go.Figure()
    # Draw edges
    for src, dst, dist in EDGES:
        x0, y0 = DELHI_LOCATIONS[src][1], DELHI_LOCATIONS[src][0]
        x1, y1 = DELHI_LOCATIONS[dst][1], DELHI_LOCATIONS[dst][0]
        fig.add_trace(go.Scattergl(x=[x0, x1], y=[y0, y1], mode="lines", line=dict(color="#1E2D4A", width=1), hoverinfo="skip", showlegend=False))
    # Highlight dispatch routes
    sel = st.session_state.selected_incident
    active_routes = DISPATCH_ROUTES.get(sel, []) if sel else []
    if not active_routes:
        for routes in DISPATCH_ROUTES.values():
            active_routes.extend(routes)
    for src, dst in active_routes:
        if src in DELHI_LOCATIONS and dst in DELHI_LOCATIONS:
            x0, y0 = DELHI_LOCATIONS[src][1], DELHI_LOCATIONS[src][0]
            x1, y1 = DELHI_LOCATIONS[dst][1], DELHI_LOCATIONS[dst][0]
            fig.add_trace(go.Scattergl(x=[x0, x1], y=[y0, y1], mode="lines", line=dict(color="#00D4FF", width=3), hoverinfo="skip", showlegend=False))
    # Draw nodes
    inc_locations = {}
    for inc in st.session_state.incidents:
        if inc["location"] in DELHI_LOCATIONS:
            inc_locations[inc["location"]] = inc
    node_x, node_y, node_color, node_size, node_text, node_border = [], [], [], [], [], []
    for loc, (lat, lon) in DELHI_LOCATIONS.items():
        node_x.append(lon)
        node_y.append(lat)
        if loc in inc_locations:
            inc = inc_locations[loc]
            c = {"CRITICAL": "#FF2D55", "MEDIUM": "#FF9500", "LOW": "#30D158"}.get(inc["severity"], "#8E9BB5")
            node_color.append(c)
            node_size.append(18 if inc["severity"] == "CRITICAL" else 14)
            node_text.append(f"<b>{loc}</b><br>{type_icon(inc['type'])} {inc['type']}<br>Severity: {inc['severity']}<br>{inc['description'][:60]}")
            node_border.append(c)
        else:
            node_color.append("#1E2D4A")
            node_size.append(10)
            node_text.append(f"<b>{loc}</b><br>No active incidents")
            node_border.append("#8E9BB5")
    fig.add_trace(go.Scattergl(x=node_x, y=node_y, mode="markers+text", marker=dict(size=node_size, color=node_color, line=dict(width=2, color=node_border)), text=[loc for loc in DELHI_LOCATIONS.keys()], textposition="top center", textfont=dict(size=9, color="#8E9BB5", family="Inter"), hovertext=node_text, hoverinfo="text", showlegend=False))
    # Resource markers
    for res in st.session_state.resources:
        if res["status"] == "DISPATCHED" and res["location"] in DELHI_LOCATIONS:
            lat, lon = DELHI_LOCATIONS[res["location"]]
            icon = {"Ambulance": "🚑", "Fire Truck": "🚒", "Police Van": "🚔"}.get(res["type"], "🚗")
            fig.add_annotation(x=lon, y=lat - 0.008, text=f"{icon}{res['id']}", showarrow=False, font=dict(size=8, color="#00D4FF", family="JetBrains Mono"), bgcolor="rgba(15,22,41,0.8)", bordercolor="#1E2D4A", borderwidth=1, borderpad=2)
    fig.update_layout(plot_bgcolor="#0A0E1A", paper_bgcolor="#0A0E1A", margin=dict(l=0, r=0, t=0, b=0), height=460, xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[76.95, 77.35]), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[28.48, 28.80], scaleanchor="x"), hoverlabel=dict(bgcolor="#0F1629", bordercolor="#1E2D4A", font=dict(family="JetBrains Mono", size=11, color="#fff")))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

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
tab1, tab2, tab3 = st.tabs(["📋 Dispatch Log", "🧠 Agent Reasoning", "📞 Raw Transcripts"])

with tab1:
    if st.session_state.dispatch_log:
        df = pd.DataFrame(st.session_state.dispatch_log)
        df.columns = [c.upper() for c in df.columns]
        st.dataframe(df, use_container_width=True, hide_index=True, height=280)

with tab2:
    for agent, reasoning in st.session_state.agent_reasoning.items():
        icon = {"Triage Agent": "🔍", "Fusion Agent": "🔗", "Dispatch Agent": "🚀", "Strategy Agent": "🧠"}.get(agent, "⚙️")
        with st.expander(f"{icon} {agent}", expanded=(agent == "Triage Agent")):
            st.markdown(f'<div class="terminal-box">{reasoning}</div>', unsafe_allow_html=True)

with tab3:
    for t in st.session_state.transcripts:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"<div style='font-size:11px;color:#8E9BB5;margin-bottom:4px;'>ORIGINAL — {t['incident_id']}</div>", unsafe_allow_html=True)
            st.markdown(f'<div class="transcript-box"><span class="transcript-orig">{t["original"]}</span></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div style='font-size:11px;color:#8E9BB5;margin-bottom:4px;'>PROCESSED OUTPUT</div>", unsafe_allow_html=True)
            st.markdown(f'<div class="transcript-box"><span class="transcript-proc">{t["processed"]}</span></div>', unsafe_allow_html=True)
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

# ── Auto-refresh ──
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=10000, limit=None, key="auto_refresh")
except ImportError:
    pass
