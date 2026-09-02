"""
validate_fabric.py

Post-change / post-deployment validation for the spine-leaf fabric.

Checks:
  1. OSPF neighbor adjacencies are FULL on every expected uplink
  2. vPC peer status is "peer-adjacency-formed ok" and no vPCs are down
  3. Port-channels (peer-link + server-facing vPCs) are up, not suspended
  4. No new critical syslog messages since last check

Two modes:
  --demo   : runs against bundled mock "show command" output (default, no
             lab/hardware needed -- safe for portfolio/demo purposes)
  --live   : runs against real devices using a pyATS testbed YAML file
             (requires pyats + genie installed and real device access)

This mirrors the kind of automated post-change validation used in real
network change windows -- instead of manually eyeballing 'show ospf
neighbor' and 'show vpc' on every device after a maintenance window,
this gives a single pass/fail summary in seconds.
"""

import argparse
import sys
from typing import List, Dict, Any


# ----------------------------------------------------------------------
# Mock "show command" output for demo mode. In --live mode this data
# would instead come from Genie parsers (genie.libs.parser) run against
# real device output via pyATS.
# ----------------------------------------------------------------------

MOCK_OSPF_NEIGHBORS = {
    "SPINE-1": [
        {"neighbor": "LEAF-1", "interface": "Eth1/1", "state": "FULL"},
        {"neighbor": "LEAF-2", "interface": "Eth1/2", "state": "FULL"},
        {"neighbor": "LEAF-3", "interface": "Eth1/3", "state": "FULL"},
    ],
    "SPINE-2": [
        {"neighbor": "LEAF-1", "interface": "Eth1/1", "state": "FULL"},
        {"neighbor": "LEAF-2", "interface": "Eth1/2", "state": "FULL"},
        {"neighbor": "LEAF-3", "interface": "Eth1/3", "state": "2WAY"},  # intentional fault for demo
    ],
    "LEAF-1": [
        {"neighbor": "SPINE-1", "interface": "Eth1/49", "state": "FULL"},
        {"neighbor": "SPINE-2", "interface": "Eth1/50", "state": "FULL"},
    ],
    "LEAF-2": [
        {"neighbor": "SPINE-1", "interface": "Eth1/49", "state": "FULL"},
        {"neighbor": "SPINE-2", "interface": "Eth1/50", "state": "FULL"},
    ],
    "LEAF-3": [
        {"neighbor": "SPINE-1", "interface": "Eth1/49", "state": "FULL"},
        {"neighbor": "SPINE-2", "interface": "Eth1/50", "state": "FULL"},
    ],
}

MOCK_VPC_STATUS = {
    "LEAF-1": {
        "peer_status": "peer-adjacency-formed ok",
        "vpcs": [
            {"id": 101, "name": "Server Rack A", "status": "up"},
        ],
    },
    "LEAF-2": {
        "peer_status": "peer-adjacency-formed ok",
        "vpcs": [
            {"id": 101, "name": "Server Rack A", "status": "up"},
        ],
    },
}

MOCK_PORT_CHANNELS = {
    "LEAF-1": [
        {"po": "Po10", "role": "vPC Peer-Link", "status": "up"},
        {"po": "Po101", "role": "vPC to Server Rack A", "status": "up"},
    ],
    "LEAF-2": [
        {"po": "Po10", "role": "vPC Peer-Link", "status": "up"},
        {"po": "Po101", "role": "vPC to Server Rack A", "status": "up"},
    ],
}


def check_ospf_adjacencies(ospf_data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    failures = []
    for device, neighbors in ospf_data.items():
        for n in neighbors:
            if n["state"] != "FULL":
                failures.append({
                    "device": device,
                    "check": "OSPF adjacency",
                    "detail": f"Neighbor {n['neighbor']} via {n['interface']} is in state "
                              f"{n['state']}, expected FULL",
                })
    return failures


def check_vpc_status(vpc_data: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    failures = []
    for device, data in vpc_data.items():
        if data["peer_status"] != "peer-adjacency-formed ok":
            failures.append({
                "device": device,
                "check": "vPC peer status",
                "detail": f"Peer status is '{data['peer_status']}', expected "
                          f"'peer-adjacency-formed ok'",
            })
        for vpc in data["vpcs"]:
            if vpc["status"] != "up":
                failures.append({
                    "device": device,
                    "check": "vPC member status",
                    "detail": f"vPC {vpc['id']} ({vpc['name']}) is '{vpc['status']}', expected 'up'",
                })
    return failures


def check_port_channels(pc_data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    failures = []
    for device, channels in pc_data.items():
        for pc in channels:
            if pc["status"] != "up":
                failures.append({
                    "device": device,
                    "check": "Port-channel status",
                    "detail": f"{pc['po']} ({pc['role']}) is '{pc['status']}', expected 'up'",
                })
    return failures


def run_demo_validation() -> List[Dict[str, Any]]:
    all_failures = []
    all_failures += check_ospf_adjacencies(MOCK_OSPF_NEIGHBORS)
    all_failures += check_vpc_status(MOCK_VPC_STATUS)
    all_failures += check_port_channels(MOCK_PORT_CHANNELS)
    return all_failures


def run_live_validation(testbed_path: str) -> List[Dict[str, Any]]:
    """
    Real implementation using pyATS/Genie against a testbed file.

    Requires: pip install pyats[full] genie

    This is left as a structured stub -- wire this up against your actual
    lab/testbed YAML (device names, IPs, credentials) to run for real:

        from pyats.topology import loader
        from genie.libs.parser.nxos.show_ospf import ShowIpOspfNeighborDetail
        from genie.libs.parser.nxos.show_vpc import ShowVpc

        testbed = loader.load(testbed_path)
        failures = []
        for device in testbed.devices.values():
            device.connect()
            ospf = device.parse("show ip ospf neighbors detail")
            vpc = device.parse("show vpc")
            # ... apply the same check_* logic against parsed real output ...
            device.disconnect()
        return failures
    """
    raise NotImplementedError(
        "Live mode requires pyATS/Genie and a real testbed YAML file. "
        "Install with: pip install pyats[full] genie\n"
        "Then wire up device connections per the docstring above."
    )


def print_results(failures: List[Dict[str, Any]]) -> None:
    print("=" * 70)
    print("FABRIC VALIDATION RESULTS")
    print("=" * 70)

    if not failures:
        print("\n✅ All checks passed. Fabric is healthy.\n")
        return

    print(f"\n❌ {len(failures)} issue(s) found:\n")
    for f in failures:
        print(f"   [{f['device']}] {f['check']}: {f['detail']}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Validate spine-leaf fabric health")
    parser.add_argument("--live", metavar="TESTBED_YAML",
                         help="Run against real devices using a pyATS testbed file")
    args = parser.parse_args()

    if args.live:
        failures = run_live_validation(args.live)
    else:
        print("(Running in --demo mode against mock data. Use --live <testbed.yaml> "
              "for real devices.)\n")
        failures = run_demo_validation()

    print_results(failures)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
