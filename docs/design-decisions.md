# Design Decisions

## Why spine-leaf instead of traditional 3-tier (core/agg/access)?

Traditional 3-tier designs rely on Spanning Tree to block redundant links, which means roughly half of your available bandwidth sits idle in a blocking state. Spine-leaf (Clos) fabrics use L3 routing (OSPF/BGP) between spine and leaf instead of L2/STP, so **every** link is active and traffic load-balances across all available paths via ECMP.

Trade-off: spine-leaf requires more cabling (every leaf to every spine) and a routing protocol running deeper into the fabric than a typical 3-tier design. For a fabric this size that's a worthwhile trade for the bandwidth and failure-domain benefits; at very small scale (a handful of racks, no East-West traffic growth expected) a traditional design may still be simpler to justify.

## Why OSPF for the underlay (not BGP)?

Both are valid choices for a Clos underlay. OSPF was chosen here because:
- Fast convergence on point-to-point links with no DR/BDR overhead needed
- Simpler operationally for a single-site fabric of this size
- Team familiarity — most enterprise NOC/support staff read OSPF adjacency states faster than BGP session states

BGP (typically eBGP with per-device AS numbers) becomes the stronger choice at larger scale (many spines, multiple pods, or eventual EVPN/VXLAN overlay), since BGP handles massive ECMP fan-out and policy control better than OSPF at that scale. This design intentionally stays at OSPF for a 2-spine/3-leaf single-site fabric; noted in the roadmap as a future BGP underlay migration if the fabric grows.

## Why vPC only on the leaf pair, not the spine?

vPC exists to give **dual-homed downstream devices** (servers, or in larger designs downstream switches) active-active links without relying on STP. Spines in this design don't connect to any downstream device that needs that redundancy model — they're pure L3 transit — so running vPC there would add complexity (peer-link, peer-keepalive, domain config) with no benefit. This mirrors why vPC is applied selectively rather than fabric-wide in real deployments.

## Why `peer-gateway` on the vPC domain?

Without `peer-gateway`, traffic destined to the *peer's* HSRP MAC address (not your own) has to traverse the vPC peer-link to reach the correct gateway, adding unnecessary latency and peer-link load. `peer-gateway` lets each vPC peer locally process traffic destined to either peer's gateway MAC, which is standard best practice on any vPC domain running HSRP/VRRP on top.

## Why is Leaf-3 standalone (no vPC)?

Not every rack needs the same redundancy tier. Leaf-3 represents a lower-priority rack (e.g., dev/test workloads) where the cost/complexity of a second switch and vPC pairing isn't justified. This is a common real-world pattern — redundancy tiers matched to workload criticality rather than a uniform design across the whole fabric.

## Known simplifications in this lab

This is a portfolio/lab design, not a production build. Things intentionally simplified or omitted:
- No VXLAN/EVPN overlay (would be the next step for multi-tenancy or L2 extension across racks)
- No out-of-band management network design (mgmt0 addressing shown is illustrative)
- No QoS policy
- Single VLAN per leaf shown for clarity; a real deployment would have several
