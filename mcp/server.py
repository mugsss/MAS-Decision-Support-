"""
Local MCP server (JSON-RPC 2.0 over stdio).
Reads PDM vehicle data from data/pdm_vehicles.json.
Handles: initialize, tools/list, tools/call
"""

import json
import sys
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "pdm_vehicles.json"

def load_vehicles() -> list[dict]:
    return json.loads(DATA_PATH.read_text())


TOOLS = [
    {
        "name": "get_vehicle_config",
        "description": "Get full configuration for a vehicle by vehicle_id. Returns platform, model year, project code, and all ECUs.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vehicle_id": {"type": "string", "description": "Vehicle identifier (e.g. VIN-0001-TEST)"}
            },
            "required": ["vehicle_id"],
        },
    },
    {
        "name": "get_ecu_assignments",
        "description": "Get all ECU assignments for a vehicle. Returns ECU IDs, types, part numbers, HW/SW versions, and suppliers.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vehicle_id": {"type": "string", "description": "Vehicle identifier"}
            },
            "required": ["vehicle_id"],
        },
    },
    {
        "name": "search_parts",
        "description": "Search for parts across all vehicles by part number prefix or ECU type.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Part number prefix or ECU type to search for"}
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_software_versions",
        "description": "Get current software versions for all ECUs in a vehicle, or for a specific ECU type across all vehicles.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vehicle_id": {"type": "string", "description": "Vehicle identifier (optional)"},
                "ecu_type": {"type": "string", "description": "ECU type filter (optional)"},
            },
        },
    },
    {
        "name": "update_sw_version",
        "description": "Update the software version of an ECU. WRITE ACTION — requires human approval.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ecu_id": {"type": "string", "description": "ECU identifier"},
                "new_version": {"type": "string", "description": "New software version string"},
            },
            "required": ["ecu_id", "new_version"],
        },
    },
]


def handle_get_vehicle_config(args: dict) -> dict:
    vehicles = load_vehicles()
    vid = args["vehicle_id"]
    for v in vehicles:
        if v["vehicle_id"] == vid:
            return {"vehicle": v}
    return {"error": f"Vehicle {vid} not found"}


def handle_get_ecu_assignments(args: dict) -> dict:
    vehicles = load_vehicles()
    vid = args["vehicle_id"]
    for v in vehicles:
        if v["vehicle_id"] == vid:
            return {"vehicle_id": vid, "ecus": v["ecus"]}
    return {"error": f"Vehicle {vid} not found"}


def handle_search_parts(args: dict) -> dict:
    vehicles = load_vehicles()
    query = args["query"].upper()
    results = []
    for v in vehicles:
        for ecu in v["ecus"]:
            if query in ecu["part_number"].upper() or query in ecu["ecu_type"].upper():
                results.append({
                    "vehicle_id": v["vehicle_id"],
                    "ecu_id": ecu["ecu_id"],
                    "ecu_type": ecu["ecu_type"],
                    "part_number": ecu["part_number"],
                    "sw_version": ecu["sw_version"],
                })
    return {"results": results, "count": len(results)}


def handle_get_software_versions(args: dict) -> dict:
    vehicles = load_vehicles()
    vid = args.get("vehicle_id")
    ecu_type = args.get("ecu_type")
    results = []
    for v in vehicles:
        if vid and v["vehicle_id"] != vid:
            continue
        for ecu in v["ecus"]:
            if ecu_type and ecu["ecu_type"].upper() != ecu_type.upper():
                continue
            results.append({
                "vehicle_id": v["vehicle_id"],
                "ecu_id": ecu["ecu_id"],
                "ecu_type": ecu["ecu_type"],
                "sw_version": ecu["sw_version"],
                "last_flashed": ecu["last_flashed"],
            })
    return {"versions": results, "count": len(results)}


def handle_update_sw_version(args: dict) -> dict:
    vehicles = load_vehicles()
    ecu_id = args["ecu_id"]
    new_version = args["new_version"]
    for v in vehicles:
        for ecu in v["ecus"]:
            if ecu["ecu_id"] == ecu_id:
                old_version = ecu["sw_version"]
                ecu["sw_version"] = new_version
                DATA_PATH.write_text(json.dumps(vehicles, indent=2))
                return {
                    "status": "updated",
                    "ecu_id": ecu_id,
                    "old_version": old_version,
                    "new_version": new_version,
                }
    return {"error": f"ECU {ecu_id} not found"}


HANDLERS = {
    "get_vehicle_config": handle_get_vehicle_config,
    "get_ecu_assignments": handle_get_ecu_assignments,
    "search_parts": handle_search_parts,
    "get_software_versions": handle_get_software_versions,
    "update_sw_version": handle_update_sw_version,
}


def handle_request(request: dict) -> dict:
    method = request.get("method", "")
    req_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "automotive-pdm-mcp", "version": "1.0.0"},
            },
        }

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": TOOLS},
        }

    if method == "tools/call":
        params = request.get("params", {})
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})

        handler = HANDLERS.get(tool_name)
        if not handler:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
            }

        try:
            result = handler(tool_args)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
                    "isError": False,
                },
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
                    "isError": True,
                },
            }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue

        response = handle_request(request)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
