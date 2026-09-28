"""
Universal stdio-to-HTTP bridge for 21st.dev MCP Server.
Allows any stdio MCP client (Antigravity, Claude, Cursor, Windsurf, VS Code)
to speak directly with 21st.dev streamable HTTP endpoint.
"""
import sys
import json
import httpx

API_URL = "https://21st.dev/api/mcp"
API_KEY = "21st_sk_7dbea11646cad7aaa11e3f215928f6a25806a85c3e9f0d50abca57c4cc8d0167"

headers = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}

def main():
    client = httpx.Client(timeout=60.0)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req_data = json.loads(line)
            res = client.post(API_URL, headers=headers, json=req_data)
            sys.stdout.write(res.text + "\n")
            sys.stdout.flush()
        except Exception as e:
            err_res = {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)},
                "id": req_data.get("id") if "req_data" in locals() and isinstance(req_data, dict) else None
            }
            sys.stdout.write(json.dumps(err_res) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
