# PRAGATI: 5-Minute Ideathon Pitch & Demo Script
**Team PRELUDE | Problem Statement ID: 26178 | Smart India Hackathon**

---

### [Minute 0:00 – 1:00] The Problem: Urban Flooding & The Hazard of Blind AI
*(Stand tall, clear voice, confident delivery. Look directly at the judges.)*

"Respected judges, every monsoon season, Indian metropolitan cities like Mumbai, Chennai, and Bengaluru come to a devastating standstill due to urban waterlogging and flash floods. Roads turn into rivers, emergency vehicles get stranded, and municipal command centres are forced to react blindly after casualties and economic losses have already occurred.

When engineers try to solve this with standard AI, they run into a dangerous trap: black-box neural networks that predict flood depths but hallucinate or fail silently during unprecedented cloudbursts or sensor glitches. In disaster management, **an unvetted prediction is far more dangerous than no prediction at all.** 

That is why our team PRELUDE built **PRAGATI: Predictive Resilience & Adaptive Governance Intelligence**."

---

### [Minute 1:00 – 2:00] The Solution: Predict → Trust → Act
*(Point to the dashboard screen displaying the dark-mode Command Center.)*

"PRAGATI changes the paradigm from reactive rescue to proactive disaster prevention using three core pillars: **Predict, Trust, and Act.**

1. **Predict:** We ingest live IoT ultrasonic water telemetry, rainfall data, and elevation terrain maps into an Uber H3 spatial grid. Our Physics-Guided Spatio-Temporal Graph Neural Network (PG-STGNN) learns water flow across downhill topological slopes while strictly enforcing water mass conservation.
2. **Trust:** Before any prediction reaches decision-makers, it must pass through **AETHER**—our patent-architecture reliability gate that audits model disagreement, out-of-distribution shifts, and sensor telemetry health.
3. **Act:** Only verified, trustworthy predictions are converted into actionable resource allocations using constrained mathematical optimization. Let me show you this running live right now."

---

### [Minute 2:00 – 3:00] Live Walkthrough: Map, Grid & Real-time Telemetry
*(Interact with the UI. Point to the left 60% of the screen.)*

"On the left, you are viewing the live PRAGATI Command Center, currently tracking an urban ward divided into terrain-indexed hexagonal cells. Notice the top right indicator: we have an active, bidirectional **1-Hertz WebSocket stream** connecting our backend physics simulation to the frontend.

Each hexagon is dynamically styled according to physical water accumulation:
- **Blue** represents safe, nominal drainage below 0.1 meters.
- **Yellow** represents warning levels up to 0.4 meters.
- **Red** indicates critical inundation.

Notice how water naturally oscillates and drains based on topographic slope. On the right, our live sensor depth currently reads **0.15 meters**, and AETHER currently displays **RELEASE** with **92% trust confidence**. Because the weather is nominal, the AI confirms that downstream automation is safe."

---

### [Minute 3:00 – 4:00] The "WOW" Moment: Injecting Anomaly & AETHER Circuit Breaker
*(Slowly drag the rainfall slider to 65 mm/hr, then pause for effect.)*

"Now watch what happens when severe monsoon conditions strike. I'll increase rainfall forcing to **65 mm/hr**. Look at the map: hexagonal cells rapidly transition from blue to yellow and red as runoff accumulates. AETHER immediately senses the rising uncertainty and shifts from **RELEASE** to **REFINE**, triggering secondary surrogate checks.

*(Now hover over the big red button)*

Now, judges, here is the defining question: *What happens if a sensor gets submerged, sends corrupted noise, or experiences an unprecedented cloudburst?* 

In any other system, the AI would generate garbage predictions and deploy vehicles to the wrong areas. In PRAGATI, I click **'Inject Sensor Anomaly'** right now.

*(Click the button! The card pulses RED: ABSTAIN)*

Look at AETHER! Instantly, the reliability score plummets to **15%**. The Latent OOD metric spikes to **3.8**, sensor quality drops, and the system **ABSTAINS**. It immediately halts automated dispatch and issues an urgent operator alert. PRAGATI is the first disaster system that knows **when to say 'I don't know'**."

---

### [Minute 4:00 – 5:00] Resource Deployment, Governance & Closing
*(Clear anomaly, toggle Human Dispatch Authority, click Deploy Pump)*

"Once the anomaly clears, we move to the final stage: **ACT**.

Urban flood response requires heterogeneous resources. You cannot use a boat where a pump is needed, and you cannot use a pump where people are marooned. PRAGATI models:
- **Dewatering Pumps** to directly lower water depth ($\Delta d$).
- **Rescue Boats** to maximize rescue reachability into cutoff sectors.

Most importantly, notice this safety toggle: **Human Dispatch Authority**. If an operator hasn't authenticated, the deploy buttons are disabled. Once authorized, I click **'Deploy Pump'**—instantly, our OR-Tools engine dispatches Pump Unit #1, and you can see the water depth dropping in real-time.

Respected judges, PRAGATI does not replace human governance; it empowers command centres with transparent, trustworthy intelligence. 

We don't just predict disasters. **We Predict, We Trust, We Act.** Thank you!"
