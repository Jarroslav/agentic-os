#!/usr/bin/env python3
"""T3 (role matrix, static): check on the Tier-1 marker-prior table (SKILL.md
Phase 1 step 4) — every profile it names in order actually exists,
generic-fallback and stack-discovery.md exist, and no curated profile file is
silently absent from the ordered list (a 7th profile added without updating
SKILL.md would otherwise never be tried by Tier 1)."""
import re
import sys
from pathlib import Path

PLUGIN = Path(sys.argv[1])
SKILL = PLUGIN / "skills/agentic-init/SKILL.md"
PROFILES_DIR = PLUGIN / "generators/stack-profiles"

skill_text = SKILL.read_text()
# Match the whole Tier-1 bullet (up to the "Tier 2 —" bullet that follows it),
# not exact prose around "first match wins" — resilient to wording edits.
m = re.search(
    r"Tier 1 — marker prior.*?(?=Tier 2 —)",
    skill_text, re.S,
)
fail = 0
if not m:
    print("  could not find the Tier-1 marker-prior section in SKILL.md"); sys.exit(1)

order_line = m.group(0)
named = re.findall(r"`([a-z0-9-]+\.md)`", order_line)
if not named:
    print("  parsed zero profile filenames out of the Tier-1 order line:", order_line)
    fail = 1

for fname in named:
    if not (PROFILES_DIR / fname).exists():
        print("  Tier-1 names %s but it does not exist under generators/stack-profiles/" % fname)
        fail = 1

curated = {p.name for p in PROFILES_DIR.glob("*.md") if p.name != "generic-fallback.md"}
missing_from_order = curated - set(named)
if missing_from_order:
    print("  curated profile(s) exist but are not in the Tier-1 order:", sorted(missing_from_order))
    fail = 1

if not (PROFILES_DIR / "generic-fallback.md").exists():
    print("  generic-fallback.md missing"); fail = 1

if not (PLUGIN / "generators/stack-discovery.md").exists():
    print("  generators/stack-discovery.md missing"); fail = 1

sys.exit(fail)
