# Physical droid (student budget)

Same droid as the simulation: about 20 x 15 x 10 cm, two driven wheels, rear caster, front rotating brush.

| Item | Qty | Est. price (USD) |
|---|---|---|
| Geared DC motor + wheel | 2 | 4 – 6 |
| Arduino Nano (clone) | 1 | 4 – 7 |
| L298N motor driver | 1 | 2 – 3 |
| Small DC motor (brush) | 1 | 1 – 2 |
| Battery holder + 7.4 V batteries | 1 | 4 – 6 |
| Chassis (recycled plastic/wood/cardboard) | 1 | 0 (scrap) |
| Wires, switch, screws, glue | 1 | 0 – 1 |
| **Estimated total** | | **15 – 24** (reuse or borrow parts to stay under 20) |

Build steps: (1) cut a base, fix the two geared motors and wheels, add the caster at the back;
(2) fix the brush motor at the front with a soft brush (nylon or sponge) that touches the panel gently;
(3) wire motors to the L298N, the Nano to the L298N, add battery pack and switch;
(4) test forward/back, brush rotation, and that it cleans without scratching.

Simulation matches the build: wheel separation 0.125 m, wheel radius 0.035 m, brush radius 0.025 m,
see `models/solarbot_droid/model.sdf`.
