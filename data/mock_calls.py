"""Mock emergency call transcripts for CrisisGrid AI.

SCENARIO SEQUENCE (for /run-scenario endpoint):
1. Fire (CRITICAL) — Connaught Place
2. Duplicate fire call (should merge with #1)
3. Accident (CRITICAL) — Rohini
4. Medical (LOW) — Dwarka
5. Another CRITICAL when resources low — Industrial explosion
"""

MOCK_CALLS = [

    # ── SCENARIO: Mandatory test sequence ────────────────────────────────

    # Call 1: Fire — CRITICAL
    "Hello 112? Yahan Connaught Place mein ek building mein aag lagi hai! "
    "Bahut dhuan aa raha hai, log andar phase hue hain! Teen-chaar manzil ki building hai, "
    "jaldi fire brigade bhejo!",

    # Call 2: Duplicate fire (same location, different caller) — triggers merge + escalation
    "Emergency! There is a fire at Connaught Place. Heavy smoke and people are trapped inside. "
    "Send fire trucks immediately! The fire is spreading to the next floor!",

    # Call 3: Third fire call — 3 reports → auto-escalation to CRITICAL
    "Bhai CP mein aag lagi hai, pura building smoke se bhar gaya hai, log fas gaye hain upar! "
    "Kitne log hain pata nahi, bohot badi aag hai!",

    # Call 4: Accident — CRITICAL (independent incident)
    "Rohini Sector 7 mein bahut bada accident ho gaya hai. Do gaadiyan takra gayi hain critical condition mein, "
    "log injured hain. Ambulance bhejo jaldi! Ek bande ka bahut khoon beh raha hai!",

    # Call 5: Medical — LOW priority
    "Dwarka mein ek bujurg aadmi ko chakkar aa gaya, shayad weakness hai. "
    "Serious nahi lagta but ambulance aa jaaye toh achha hoga.",

    # Call 6: CRITICAL when resources scarce — Industrial explosion
    "EMERGENCY! Industrial area mein blast hua hai! Bahut badi explosion! "
    "Multiple workers injured, fire spreading fast, chemicals involved! "
    "Send all available fire trucks and ambulances immediately! "
    "This is a mass casualty event!",

    # ── Additional mock calls for live simulation ─────────────────────────

    # Duplicate accident call (same as call 4)
    "Major accident in Rohini Sector 7. Two vehicles collided, multiple injured. "
    "One person bleeding heavily. Send ambulance now!",

    # Theft — police needed
    "Dwarka Sector 12 mein abhi chain snatching hui hai. Do ladke bike pe aaye aur chain le gaye. "
    "Police bhejo jaldi!",

    # Gas leak — medium
    "Hello! There is a gas leak in a restaurant in Saket. Strong smell everywhere, "
    "people evacuated. Send fire department quickly!",

    # Building collapse — critical
    "Lajpat Nagar mein ek building gir gayi hai! Log andar fase hue hain, "
    "awaaz aa rahi hai, jaldi help bhejo! At least 5-6 log trapped hain!",

    # Flood — medium
    "ITO ke paas paani bhar gaya hai, log road pe phase hue hain, "
    "gaadiyaan band ho gayi hain. Rescue team chahiye!",

    # Medical emergency
    "Karol Bagh mein ek aadmi behosh ho gaya hai, shayad heart attack hai. "
    "Ambulance bhejo jaldi! Woh saans nahi le raha properly.",

    # Industrial fire duplicate (triggers escalation with prior call)
    "Explosion reported in industrial area. There is fire and smoke, workers injured. "
    "Send multiple fire units and ambulances! Hazmat situation possible.",

]

# ── Structured test scenario for /run-scenario endpoint ──────────────────
TEST_SCENARIO = [
    {
        "call": MOCK_CALLS[0],
        "expected_type": "fire",
        "expected_severity": "critical",
        "description": "Call 1: Initial fire at Connaught Place (CRITICAL)"
    },
    {
        "call": MOCK_CALLS[1],
        "expected_type": "fire",
        "expected_severity": "critical",
        "description": "Call 2: Duplicate fire call — should merge with Call 1"
    },
    {
        "call": MOCK_CALLS[2],
        "expected_type": "fire",
        "expected_severity": "critical",
        "description": "Call 3: Third fire call — 3 reports → auto-escalate to CRITICAL"
    },
    {
        "call": MOCK_CALLS[3],
        "expected_type": "accident",
        "expected_severity": "critical",
        "description": "Call 4: Independent CRITICAL accident at Rohini"
    },
    {
        "call": MOCK_CALLS[4],
        "expected_type": "medical",
        "expected_severity": "low",
        "description": "Call 5: LOW priority medical in Dwarka"
    },
    {
        "call": MOCK_CALLS[5],
        "expected_type": "fire",
        "expected_severity": "critical",
        "description": "Call 6: CRITICAL explosion when resources scarce — tests re-routing"
    },
]
