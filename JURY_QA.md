# PRAGATI: Jury Q&A Defense Cheat Sheet
**Team PRELUDE | Problem Statement ID: 26178 | Smart India Hackathon**

---

### Q1: "Why not just use a weather app or IMD rainfall forecast?"
> **Answer:**  
> Rainfall tells you what falls from the sky, but it cannot tell municipal operators how water flows across complex urban terrain, where drainage bottlenecks occur, or which roads become impassable. PRAGATI couples rainfall forcing with a terrain-aware graph neural network to predict localized inundation depth and translates that directly into pump and boat deployment strategies.

---

### Q2: "What happens if your AI model makes a wrong prediction?"
> **Answer:**  
> That is precisely why conventional black-box AI fails in disaster management and why we built AETHER as an explicit circuit breaker. If an event is out-of-distribution, models disagree, or physical mass conservation is violated, AETHER refuses to automate, triggers a physics-based surrogate simulation, or immediately abstains and alerts human operators rather than making unsafe recommendations.

---

### Q3: "Where is the actual hardware sensor in this project?"
> **Answer:**  
> Our edge hardware node utilizes an ESP32 paired with an industrial waterproof ultrasonic transducer (JSN-SR04T) mounted over a calibrated stormwater tank datum. For this command center demonstration, telemetry is streamed via real-time WebSockets, showing exactly how physical field water-level changes immediately propagate into the intelligence and dispatch pipeline.

---

### Q4: "What is novel about this compared to existing flood warning systems?"
> **Answer:**  
> Existing systems are either purely observational gauge networks or slow, offline numerical hydrologic simulations that cannot operate interactively during a cloudburst. PRAGATI introduces three key scientific novelties: a physics-guided spatio-temporal GNN enforcing continuity constraints, a multi-signal reliability gate (AETHER) that prevents silent AI failure, and an MILP optimizer that models pumps and rescue boats as physically distinct operational assets.

---

### Q5: "Why should a municipal command centre trust this system?"
> **Answer:**  
> Because PRAGATI was built with the core philosophy of **Predict → Trust → Act**, ensuring that AI never holds autonomous dispatch authority over emergency assets. Every forecast exposes its full provenance—latent OOD distance, ensemble variance, and physics residuals—and requires explicit two-factor Human-in-the-Loop authorization before any physical pump or rescue boat can be dispatched.
