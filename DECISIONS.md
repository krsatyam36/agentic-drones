# Architectural Decisions

## Platform & Domain
**Decision**: Drone (Multirotor)
**Reason**: PX4 SITL is the most robust, industry-standard simulation environment for multirotors, making it ideal for demonstrating the core pipeline (Prompt -> LLM -> JSON -> Executor -> Flight).

## Scope Tier
**Decision**: Direct-Offer
**Reason**: The goal is to build a highly robust core pipeline combined with depth across the three major challenges (Vision, SLAM, Swarm), satisfying the highest level of the rubric.

## The Pinned Stack
**Decision**: Ubuntu 24.04 (via Docker), ROS 2 Humble, PX4 Autopilot v1.15.4, Python 3.10
**Reason**: Using a strictly pinned Docker environment guarantees 100% reproducibility on the examiner's Linux machine, eliminating "works on my machine" failures.

## Challenge Allocation (Deep vs. Write-up)
**Decision**: 
*   **Deep Build**: Challenge 3 (Vision AI target detection + follow)
*   **Working Partials**: Challenge 1 (Swarm formations) and Challenge 2 (SLAM navigation)
**Reason**: A flawless, deeply implemented vision tracking node proves end-to-end integration of sensor data into the deterministic executor, while working partials for Swarm and SLAM demonstrate architectural scalability without compromising the stability of the core simulation.
