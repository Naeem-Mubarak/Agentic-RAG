from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

server_path = PROJECT_ROOT / "file_system_server.py"

print(server_path)
