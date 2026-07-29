"""A clean fixture. The scan wall MUST pass this — no findings on any layer.

Paired with the malicious fixture so scanner-selftest.yml proves a version bump keeps
the wall both quiet on good code and loud on bad. Deliberately boring.
"""

from axolotl.integrations.base import BasePlugin


class BenignPlugin(BasePlugin):
    def register(self, cfg):
        return None
