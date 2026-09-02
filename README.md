# Data Center Spine-Leaf Fabric with vPC

A documented, lab-validated design for a modern data center network fabric: 2 spines, 3 leaves (one vPC pair + one standalone), OSPF underlay, and an automated post-change validation script.

Built to reflect real DC design and migration work — moving away from traditional 3-tier/STP-blocked designs toward an ECMP-routed Clos fabric, the kind of modernization involved in migrating legacy chassis switching (e.g. ASR1006) onto a Nexus fabric.

## Why this exists

Most portfolio "network labs" show a couple of routers running a routing protocol. This goes further: a realistic DC fabric topology, full device configs, documented design rationale (including trade-offs, not just "how"), and — critically — an **automated validation script** instead of manual `show` command checking after every change.

## Topology

See [`topology/topology-diagram.md`](topology/topology-diagram.md) for the full Mermaid diagram (renders directly on GitHub).

```
         SPINE-1              SPINE-2
        /   |   \            /   |   \
       /    |    \          /    |    \
   LEAF-1 LEAF-2 LEAF-3 <--full mesh--> (every leaf to every spine)
      \    /        \
       vPC pair    standalone
      (Rack A)      (Rack C)
```

- **Spines**: pure L3 transit, OSPF underlay, ECMP across both spines
- **Leaf-1 / Leaf-2**: vPC pair, active-active dual-homing for Server Rack A
- **Leaf-3**: standalone leaf for a lower-redundancy rack

Full design rationale — including why spine-leaf over 3-tier, why OSPF over BGP for the underlay, and why vPC is scoped to the leaf layer only — is in [`docs/design-decisions.md`](docs/design-decisions.md).

## Device configs

Real, deployable Nexus NX-OS configuration for every device in the fabric:

| File | Device | Role |
|---|---|---|
| [`configs/spine1.cfg`](configs/spine1.cfg) | Spine-1 | OSPF underlay, L3 transit |
| [`configs/spine2.cfg`](configs/spine2.cfg) | Spine-2 | OSPF underlay, L3 transit |
| [`configs/leaf1.cfg`](configs/leaf1.cfg) | Leaf-1 | vPC primary, HSRP active |
| [`configs/leaf2.cfg`](configs/leaf2.cfg) | Leaf-2 | vPC secondary, HSRP standby |
| [`configs/leaf3.cfg`](configs/leaf3.cfg) | Leaf-3 | Standalone, single-homed rack |

## Automated fabric validation

Instead of manually checking `show ip ospf neighbor` and `show vpc` on every device after a maintenance window, `validation/validate_fabric.py` runs all the checks in one pass and gives a clear pass/fail summary:

- OSPF adjacencies are `FULL` on every expected uplink
- vPC peer status is healthy and no vPCs are down
- Peer-link and server-facing port-channels are up

```bash
cd validation
python3 validate_fabric.py
```

Runs in demo mode by default against bundled mock device output (no lab hardware required) — and **intentionally includes one injected fault** (an OSPF neighbor stuck in `2WAY` instead of `FULL`) so you can see the script actually catch a real problem instead of always printing green checkmarks:

```
❌ 1 issue(s) found:
   [SPINE-2] OSPF adjacency: Neighbor LEAF-3 via Eth1/3 is in state 2WAY, expected FULL
```

For real hardware, the script is structured to run against a [pyATS](https://developer.cisco.com/pyats/) testbed:

```bash
python3 validate_fabric.py --live testbed.yaml
```

(see the docstring in `validate_fabric.py` for the pyATS/Genie wiring — requires `pip install pyats[full] genie` and a real testbed YAML with device credentials)

## Project structure

```
dc-spine-leaf-fabric/
├── topology/
│   └── topology-diagram.md      # Mermaid diagram + design summary table
├── configs/
│   ├── spine1.cfg
│   ├── spine2.cfg
│   ├── leaf1.cfg
│   ├── leaf2.cfg
│   └── leaf3.cfg
├── validation/
│   └── validate_fabric.py       # automated post-change health check
└── docs/
    └── design-decisions.md      # rationale + trade-offs behind every major choice
```

## Roadmap / possible extensions

- [ ] Add VXLAN/EVPN overlay for multi-tenancy and L2 extension across racks
- [ ] Migrate underlay from OSPF to BGP for larger-scale ECMP
- [ ] Add QoS policy for latency-sensitive workloads
- [ ] Wire up the `--live` validation path against a real GNS3/EVE-NG or physical lab
- [ ] Add a second vPC pair and a third rack to test full ECMP fan-out

## Background

Built by a network engineer with hands-on experience migrating data center switching fabrics (including an ASR1006-to-Nexus 7010 migration) and working in Cisco ACI environments for high-availability, scalable DC networking.
