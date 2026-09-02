# Topology: 2-Spine / 3-Leaf Data Center Fabric

```mermaid
graph TB
    subgraph Spine Layer
        S1[Spine-1<br/>Nexus 9336C-FX2]
        S2[Spine-2<br/>Nexus 9336C-FX2]
    end

    subgraph Leaf Layer - vPC Pair A
        L1[Leaf-1<br/>Nexus 93180YC-EX]
        L2[Leaf-2<br/>Nexus 93180YC-EX]
    end

    subgraph Leaf Layer - Standalone
        L3[Leaf-3<br/>Nexus 93180YC-EX]
    end

    S1 ---|40G| L1
    S1 ---|40G| L2
    S1 ---|40G| L3
    S2 ---|40G| L1
    S2 ---|40G| L2
    S2 ---|40G| L3

    L1 <-.->|vPC Peer-Link<br/>Po10, 2x40G| L2
    L1 -.->|Peer-Keepalive<br/>mgmt0| L2

    H1[Server Rack A<br/>Dual-homed via vPC]
    H2[Server Rack B<br/>Dual-homed via vPC]
    H3[Server Rack C]

    L1 ---|vPC| H1
    L2 ---|vPC| H1
    L1 ---|vPC| H2
    L2 ---|vPC| H2
    L3 --- H3
```

## Design summary

| Layer | Role | Redundancy model |
|---|---|---|
| Spine | L3 transit only, no server-facing ports | ECMP across both spines via OSPF underlay |
| Leaf (vPC pair) | Server/rack-facing, active-active dual-homing | vPC domain 10, peer-link + peer-keepalive |
| Leaf (standalone) | Lower-redundancy racks / non-critical workloads | Single-homed, relies on spine ECMP only |

- Every leaf connects to **every** spine (full mesh leaf↔spine) — this is what makes it a spine-leaf (Clos) fabric rather than a traditional 3-tier design.
- Spines never connect to each other directly — all spine-to-spine traffic transits through a leaf, which is intentional in a Clos fabric.
- vPC is used at the leaf pair (not the spine) so that dual-homed servers/racks get active-active links with no blocked ports and no STP dependency for the access-facing side.
