MOCK_CALLS = [
    # ═══ CLUSTER 1: Fire at Karol Bagh (3 duplicate calls, conflicting details) ═══

    # Call 1 — Hinglish, panicked
    "Bhai jaldi aao, yahan Karol Bagh mein aag lagi hai! Bahut badi aag hai, 2 log injured hain. Building ka 2nd floor jal raha hai, dhuan bahut hai. Fire brigade bhejo!",

    # Call 2 — Hinglish, conflicting info (says 5 unconscious)
    "Hello 112? Karol Bagh mein main building jal rahi hai! Pura dhuaan hai idhar. Maine 5 logon ko behosh dekha hai, bahut serious hai, jaldi fire brigade aur ambulance bhejo!",

    # Call 3 — Broken English, vague panic
    "Hello? Please come fast! Fire in Karol Bagh, smoke everywhere, people stuck inside, I don't know what to do! Please send help!",

    # ═══ CLUSTER 2: Accident at ITO (2 duplicate calls) ═══

    # Call 4 — Mixed Hinglish-English
    "Bhai accident ho gaya near ITO intersection, one truck and two cars crashed. Ek bande ka bahut khoon nikal raha hai. Ambulance aur police jaldi bhejo!",

    # Call 5 — Pure English, calmer
    "I'm reporting a multi-vehicle collision at ITO junction. There are at least 3 vehicles involved including a truck. Multiple people appear injured. Please send ambulance and police immediately.",

    # ═══ CLUSTER 3: Flood at Connaught Place (2 duplicate calls) ═══

    # Call 6 — Hinglish
    "Connaught Place mein paani bhar gaya hai, underground parking mein log phanse hain! Light bhi chali gayi hai, 10-15 log andar hain. Rescue team bhejiye jaldi!",

    # Call 7 — Panic English
    "Water is flooding into the basement at Connaught Place! People are trapped, no electricity, we can't see anything. Send rescue boats or pumps right now!",

    # ═══ STANDALONE INCIDENTS ═══

    # Call 8 — Medical Emergency at Lajpat Nagar (Pure English, calm)
    "Hello, I need an ambulance at Lajpat Nagar market. An elderly man has collapsed near gate number 2. He seems to be having a heart attack, he's not breathing properly. Please hurry.",

    # Call 9 — Explosion at Dwarka (Hinglish, urgent)
    "Dwarka Sector 12 mein ek godown mein blast hua hai! Bahut bada explosion tha, aag bhi lag gayi hai. Multiple fire trucks chahiye, area bahut bada hai!",

    # Call 10 — Accident at Rohini (short, urgent)
    "Rohini main road pe bus palat gayi hai! Bahut log andar hain, kuch ghayel hain. Police ambulance sab bhejo jaldi!",

    # Call 11 — Medical Emergency at Saket (English, structured)
    "Reporting a medical emergency at Saket Mall, ground floor food court. A young woman has fainted and is having seizures. We need an ambulance immediately. She is not responding.",

    # Call 12 — Fire at Nehru Place (Hinglish, moderate urgency)
    "Nehru Place mein ek office building ki 3rd floor pe aag lag gayi hai. Abhi smoke dikh raha hai, log neeche bhaag rahe hain. Fire truck bhejiye please.",

    # Call 13 — Flood at Rajouri Garden (English, calm)
    "There is severe waterlogging on Rajouri Garden main road. A car has gotten stuck in the water with passengers inside. The water level is rising. Please send help.",

    # Call 14 — Accident at Janakpuri (Hinglish, very panicked)
    "Janakpuri mein flyover ke neeche ek tempo ne scooter ko takkar maar di! Ladka gir gaya hai, hil nahi raha, bahut khoon hai. Ambulance jaldi bhejo yaar, please!",

    # Call 15 — Medical Emergency at Vasant Kunj (broken English)
    "Hello please help, my father fell down stairs in Vasant Kunj, B block. He is old man, leg is broken maybe, cannot move. Need ambulance fast please.",
]
