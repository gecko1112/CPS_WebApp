# P13 Web App — User Input Questionnaire

This is the source text for a Google Form sent to the ~30 students across all CPS project groups. Goal: gather concrete input on what the web app should show (simple vs. advanced view), how it should notify users, and what each group could specifically contribute. Responses feed the usability reflection in the final report (issue #14) and the simple/advanced view toggle design (issue #10).

**How to use:** copy the sections below into Google Forms. Most questions work as checkboxes / radio / linear scale; the open-ended ones are short answer or paragraph. Suggested form length: ~8–12 minutes per respondent.

---

## Form intro (paste at top of the Google Form)

> Hi! I'm building the P13 web app — the user-facing dashboard for our balcony plant watering CPS. The app needs to work for both **non-expert users** (someone who just wants to know "is my plant okay?") and **expert users** (CPS students like you who might want to debug what's going on). This form takes ~8 minutes and helps me design the right interface. Your group's perspective matters because you know best what your component produces and what you'd want to see from it. Thank you!

---

## Section 1 — About you (1 min)

**1.1 Which project group are you in?**
*Multiple choice — one option per group*

- P01 Soil Moisture Sensing & Calibration
- P02 Pump / Valve Actuation
- P03 Environmental Sensing
- P04 MQTT Communication Infrastructure
- P05 Watering Controller
- P06 Data Logging & Visualisation
- P07 Weather API Integration
- P08 Anomaly Detection & Fault Diagnosis
- P09 Cybersecurity & System Hardening
- P10 System Integration & Deployment
- P11 Water Tank Level Monitoring
- P12 Solar Power & Battery System
- P13 Web App (us)
- P14 Weatherproof Enclosure
- P15 Digital Twin
- P16 Plant Health Model
- P17 OTA Update & Remote Config
- P18 Multi-Zone Scalability
- Not in a group

**1.2 In one sentence, what does your group do?** *(short answer, optional — for context)*

---

## Section 2 — As a future user (3 min)

**2.1 Imagine you just opened the web app on your phone. Pick the THREE things you'd most want visible right away.**
*Checkboxes, limit 3*

- Current soil moisture
- When the system last watered
- Tank fill level (water remaining)
- Battery / power status
- Weather forecast (rain expected?)
- Plant health score
- Active alerts / anomalies
- Controller state (idle / watering / suppressed)
- Last command issued
- Time-to-next-watering estimate
- Time-to-empty estimate for the tank
- Other (specify)

**2.2 When something goes wrong, how would you want to be notified?**
*Checkboxes, multiple allowed*

- In-app banner (only when I have the page open)
- Browser push notification (popup even when the tab is closed)
- Email
- I'd rather check the app myself — no notifications

**2.3 How comfortable would you be with the system watering autonomously without asking you first?**
*Linear scale 1–5: 1 = "Always ask me" → 5 = "Just do its thing, I don't want to be bothered"*

**2.4 What's one piece of information you would NOT want shown to a non-expert (because it would confuse or worry them)?** *(short answer)*

---

## Section 3 — Advanced / expert view (2 min)

**3.1 The app will have a "simple" view (everyday user) and an "advanced" view (CPS-aware user). What extra info would you want in the advanced view?**
*Checkboxes, multiple allowed*

- Raw sensor values (ADC counts, voltages, distances in mm)
- Live MQTT topic activity (rolling message log)
- Sequence numbers / Sparkplug B internals
- Per-node birth/death status (which components are online)
- Historical anomaly log with severity and component
- Controller state-machine transitions
- Watering history (timestamps, durations, triggers)
- Network/broker stats (message rate, drops)
- Manual command sender (for testing)
- Other (specify)

**3.2 If you were debugging YOUR group's component using only this web app, what would you most want to see?** *(short answer)*

---

## Section 4 — What can your group contribute? (3–4 min)

These four questions help me design the integration with your group specifically. Even a one-line answer helps.

**4.1 What data, signals, or features does your group produce that you think would be valuable to show in the web app?** *(paragraph)*

**4.2 Are there any thresholds, calibrations, or configurable parameters you think the user (operator) should be able to adjust via the web app?** *(paragraph)*

**4.3 Are there error states or status flags from your group that the web app should make visible?** *(paragraph)*

**4.4 Would you like the web app to send commands TO your component? If yes, what kind?** *(short answer)*

---

## Section 5 — Open feedback (1 min)

**5.1 Anything else you'd like to see (or NOT see) in the web app?** *(paragraph)*

**5.2 Would you be willing to spend ~10 minutes giving feedback on the prototype once it's ready for testing?**
*Radio:*

- Yes, please ping me
- Maybe, depending on timing
- No thanks

**5.3 If yes/maybe, leave your TU Berlin email or preferred contact** *(short answer, optional)*

---

## Setup notes (for me, not for the form)

- Title: "P13 Web App — Help me design the user interface"
- Description (the intro paragraph above)
- Collect email addresses: optional (leave off so it's anonymous unless they opt in via 5.3)
- Mandatory questions: 1.1 only — keep everything else optional so people aren't blocked by sections that don't apply
- Share link in the course Slack/Mattermost/whatever the group uses
- Target: 20–30 responses (full coverage of all groups would be ideal)
- Close the form after ~1 week
- Export responses as CSV → analyse and feed insights into issues #10 (simple/advanced split), #14 (usability reflection), #15 (notifications), and potentially new issues if patterns emerge
