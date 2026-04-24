"""Mock data for CrisisGrid AI Dashboard."""
import datetime

DELHI_LOCATIONS = {
    "Connaught Place": (28.6315, 77.2167),
    "Karol Bagh": (28.6514, 77.1907),
    "Lajpat Nagar": (28.5700, 77.2400),
    "ITO": (28.6285, 77.2410),
    "Chandni Chowk": (28.6506, 77.2300),
    "Dwarka": (28.5921, 77.0460),
    "Rohini": (28.7495, 77.0565),
    "Saket": (28.5244, 77.2066),
    "Nehru Place": (28.5491, 77.2533),
    "Rajouri Garden": (28.6492, 77.1219),
    "Vasant Kunj": (28.5195, 77.1570),
    "Janakpuri": (28.6219, 77.0815),
}

EDGES = [
    ("Connaught Place", "Karol Bagh", 4.2),
    ("Connaught Place", "ITO", 2.8),
    ("Connaught Place", "Chandni Chowk", 3.5),
    ("Connaught Place", "Lajpat Nagar", 6.1),
    ("Karol Bagh", "Rajouri Garden", 5.0),
    ("Karol Bagh", "Chandni Chowk", 4.8),
    ("Lajpat Nagar", "Nehru Place", 3.2),
    ("Lajpat Nagar", "Saket", 4.5),
    ("ITO", "Chandni Chowk", 3.0),
    ("ITO", "Lajpat Nagar", 5.5),
    ("Dwarka", "Janakpuri", 6.0),
    ("Janakpuri", "Rajouri Garden", 4.5),
    ("Rohini", "Chandni Chowk", 12.0),
    ("Saket", "Vasant Kunj", 4.0),
    ("Nehru Place", "ITO", 5.8),
    ("Rajouri Garden", "Janakpuri", 4.5),
    ("Dwarka", "Vasant Kunj", 8.5),
    ("Rohini", "Karol Bagh", 10.2),
]

MOCK_INCIDENTS = [
    {
        "id": "INC-2026-0417",
        "location": "Karol Bagh",
        "type": "Fire",
        "severity": "CRITICAL",
        "timestamp": "2026-04-24 17:32:10",
        "description": "Major fire in residential building, people trapped on upper floors",
        "calls_merged": 4,
        "status": "ACTIVE",
    },
    {
        "id": "INC-2026-0418",
        "location": "ITO",
        "type": "Accident",
        "severity": "CRITICAL",
        "timestamp": "2026-04-24 17:45:22",
        "description": "Multi-vehicle collision near ITO intersection, multiple casualties",
        "calls_merged": 3,
        "status": "ACTIVE",
    },
    {
        "id": "INC-2026-0419",
        "location": "Connaught Place",
        "type": "Flood",
        "severity": "MEDIUM",
        "timestamp": "2026-04-24 18:01:05",
        "description": "Waterlogging in basement areas, people stranded",
        "calls_merged": 2,
        "status": "ACTIVE",
    },
    {
        "id": "INC-2026-0420",
        "location": "Dwarka",
        "type": "Earthquake",
        "severity": "LOW",
        "timestamp": "2026-04-24 18:15:33",
        "description": "Minor tremor reported, structural cracks in old building",
        "calls_merged": 1,
        "status": "MONITORING",
    },
    {
        "id": "INC-2026-0421",
        "location": "Lajpat Nagar",
        "type": "Fire",
        "severity": "MEDIUM",
        "timestamp": "2026-04-24 18:22:47",
        "description": "Fire in market area shop, spreading to adjacent units",
        "calls_merged": 2,
        "status": "ACTIVE",
    },
]

MOCK_RESOURCES = [
    {"id": "AMB-01", "type": "Ambulance", "status": "DISPATCHED", "location": "ITO", "eta": "4 min", "incident": "INC-2026-0418"},
    {"id": "AMB-02", "type": "Ambulance", "status": "DISPATCHED", "location": "Karol Bagh", "eta": "6 min", "incident": "INC-2026-0417"},
    {"id": "AMB-03", "type": "Ambulance", "status": "AVAILABLE", "location": "Saket", "eta": "-", "incident": "-"},
    {"id": "AMB-04", "type": "Ambulance", "status": "AVAILABLE", "location": "Rohini", "eta": "-", "incident": "-"},
    {"id": "AMB-05", "type": "Ambulance", "status": "DISPATCHED", "location": "Lajpat Nagar", "eta": "8 min", "incident": "INC-2026-0421"},
    {"id": "FT-01", "type": "Fire Truck", "status": "DISPATCHED", "location": "Karol Bagh", "eta": "3 min", "incident": "INC-2026-0417"},
    {"id": "FT-02", "type": "Fire Truck", "status": "DISPATCHED", "location": "Lajpat Nagar", "eta": "7 min", "incident": "INC-2026-0421"},
    {"id": "FT-03", "type": "Fire Truck", "status": "AVAILABLE", "location": "Janakpuri", "eta": "-", "incident": "-"},
    {"id": "PV-01", "type": "Police Van", "status": "DISPATCHED", "location": "ITO", "eta": "5 min", "incident": "INC-2026-0418"},
    {"id": "PV-02", "type": "Police Van", "status": "AVAILABLE", "location": "Connaught Place", "eta": "-", "incident": "-"},
    {"id": "PV-03", "type": "Police Van", "status": "DISPATCHED", "location": "Connaught Place", "eta": "10 min", "incident": "INC-2026-0419"},
    {"id": "PV-04", "type": "Police Van", "status": "AVAILABLE", "location": "Dwarka", "eta": "-", "incident": "-"},
]

MOCK_DISPATCH_LOG = [
    {"time": "17:33:15", "incident": "INC-2026-0417", "unit": "FT-01", "route": "Rajouri Garden → Karol Bagh", "eta": "3 min", "status": "EN ROUTE"},
    {"time": "17:34:02", "incident": "INC-2026-0417", "unit": "AMB-02", "route": "Connaught Place → Karol Bagh", "eta": "6 min", "status": "EN ROUTE"},
    {"time": "17:46:30", "incident": "INC-2026-0418", "unit": "AMB-01", "route": "Lajpat Nagar → ITO", "eta": "4 min", "status": "EN ROUTE"},
    {"time": "17:47:05", "incident": "INC-2026-0418", "unit": "PV-01", "route": "Connaught Place → ITO", "eta": "5 min", "status": "EN ROUTE"},
    {"time": "18:02:44", "incident": "INC-2026-0419", "unit": "PV-03", "route": "Chandni Chowk → Connaught Place", "eta": "10 min", "status": "EN ROUTE"},
    {"time": "18:23:55", "incident": "INC-2026-0421", "unit": "FT-02", "route": "Nehru Place → Lajpat Nagar", "eta": "7 min", "status": "EN ROUTE"},
    {"time": "18:24:30", "incident": "INC-2026-0421", "unit": "AMB-05", "route": "Saket → Lajpat Nagar", "eta": "8 min", "status": "EN ROUTE"},
]

MOCK_TRANSCRIPTS = [
    {
        "original": "Bhai jaldi aao, yahan Karol Bagh mein aag lagi hai, bahut badi, log fas gaye hain upar. Teen-chaar manzil ki building hai, dhuan bahut hai. Jaldi bhejo fire brigade!",
        "processed": "EMERGENCY: Large fire reported in Karol Bagh. Multi-story residential building (3-4 floors). People trapped on upper floors. Heavy smoke. Immediate fire brigade and ambulance required.",
        "incident_id": "INC-2026-0417",
    },
    {
        "original": "Hello 112? Mera naam Priya hai, ITO ke paas accident hua hai, 2-3 gaadiyaan, log ghayel hain. Ek truck aur do cars takrayi hain. Bahut khoon beh raha hai ek bande ka. Please jaldi aao!",
        "processed": "EMERGENCY: Multi-vehicle accident near ITO junction. 1 truck and 2 cars involved. Multiple injured persons. One person with severe bleeding. Requires ambulance and police immediately.",
        "incident_id": "INC-2026-0418",
    },
    {
        "original": "Connaught Place mein pani bhar gaya, basement mein log phanse hain, jaldi bhejo kuch. Underground parking mein paani ghus gaya, 10-15 log andar hain, light bhi chali gayi hai.",
        "processed": "EMERGENCY: Severe waterlogging at Connaught Place. Underground parking/basement flooded. 10-15 people trapped inside. Power outage in affected area. Rescue team and pumps needed.",
        "incident_id": "INC-2026-0419",
    },
]

AGENT_REASONING = {
    "Triage Agent": """[17:32:15] PROCESSING incoming 112 call transcript...
[17:32:16] Language detected: Hinglish (Hindi-English mix)
[17:32:16] Extracting structured data from unstructured call...

EXTRACTION RESULTS:
- Location: Karol Bagh (confidence: 0.96)
- Incident Type: FIRE (keywords: "aag lagi", "dhuan")
- Severity: CRITICAL (people trapped = automatic CRITICAL escalation)
- Resources Needed: Fire Brigade (primary), Ambulance (secondary)
- Caller Distress Level: HIGH (repeated urgency markers: "jaldi", "bhai")

[17:32:17] Structured incident object created → forwarding to Fusion Agent
[17:32:17] NOTE: Caller mentioned "3-4 manzil" — multi-story building
           increases rescue complexity. Flagging for Strategy review.""",

    "Fusion Agent": """[17:32:18] Received structured incident from Triage Agent
[17:32:18] Checking against active incident database...

DUPLICATE CHECK:
- Comparing with 4 active incidents in system
- Location match found: 3 previous calls from Karol Bagh area
- Incident type match: All report FIRE
- Time proximity: All within 8-minute window

FUSION DECISION: MERGE with existing INC-2026-0417
- Merged call count: 4 → confirms genuine large-scale incident
- Conflicting info resolved: Call #2 said "2 floors", Call #4 says "3-4 floors"
  → Using MAXIMUM estimate (3-4 floors) for safety
- New information added: "People trapped on upper floors" (from Call #4)

[17:32:19] Master incident INC-2026-0417 updated → forwarding to Dispatch""",

    "Dispatch Agent": """[17:32:20] Received updated incident INC-2026-0417 (CRITICAL - FIRE)
[17:32:20] Querying resource database...

AVAILABLE RESOURCES:
- Fire Trucks: FT-01 (Rajouri Garden), FT-03 (Janakpuri) — 2 available
- Ambulances: AMB-02 (Connaught Place), AMB-03 (Saket) — 2 available

ROUTING CALCULATION (NetworkX shortest path):
- FT-01: Rajouri Garden → Karol Bagh = 5.0 km, ETA 3 min ✓ OPTIMAL
- FT-03: Janakpuri → Rajouri Garden → Karol Bagh = 9.5 km, ETA 8 min
- AMB-02: Connaught Place → Karol Bagh = 4.2 km, ETA 6 min ✓ DISPATCHING

DISPATCH ORDERS:
1. FT-01 → Karol Bagh (ETA: 3 min) — PRIMARY fire response
2. AMB-02 → Karol Bagh (ETA: 6 min) — Medical standby for trapped persons

[17:32:21] Resources marked DISPATCHED. Routes highlighted on city map.""",

    "Strategy Agent": """[17:32:22] Reviewing dispatch decisions for INC-2026-0417...

STRATEGIC ASSESSMENT:
- Current system load: 5 active incidents, 7/12 units dispatched
- Reserve capacity: 5 units remaining (2 AMB, 1 FT, 2 PV)
- Risk level: ELEVATED — one more CRITICAL incident would strain reserves

TRADE-OFF ANALYSIS:
- FT-01 dispatched to Karol Bagh leaves Rajouri Garden uncovered
- Nearest backup fire truck (FT-03 in Janakpuri) can cover Rajouri in 4.5 min
- ACCEPTABLE RISK: Rajouri Garden has no active incidents

RECOMMENDATION: APPROVE dispatch as planned
- Rationale: CRITICAL fire with trapped persons takes absolute priority
- Contingency: If new CRITICAL fire emerges, FT-03 from Janakpuri is 
  available. Consider requesting mutual aid from neighboring district.
- Alert: System approaching 60% resource utilization. Recommending 
  standby alert to off-duty units if utilization exceeds 75%.

[17:32:23] Decision logged. Transparency report generated.""",
}

DISPATCH_ROUTES = {
    "INC-2026-0417": [("Rajouri Garden", "Karol Bagh"), ("Connaught Place", "Karol Bagh")],
    "INC-2026-0418": [("Lajpat Nagar", "ITO"), ("Connaught Place", "ITO")],
    "INC-2026-0419": [("Chandni Chowk", "Connaught Place")],
    "INC-2026-0421": [("Nehru Place", "Lajpat Nagar"), ("Saket", "Lajpat Nagar")],
}
