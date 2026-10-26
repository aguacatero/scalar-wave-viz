# Two-project Antigravity fresh-session scheduler

**Not yet active on your Mac.** This PR adds repository-side code/tests but cannot configure the user's local Antigravity authentication, model quota, local working copies, or macOS launch agents.

## Allocation and limits

- Scalar Wave Viz and Septuagint Diaspora Book are independently capped at **35% each** of a *manually configured* five-hour token budget. They share a **single local SQLite ledger**.
- Combined scheduled usage cannot reserve more than **70%**, leaving **30%** unallocated for at least two other projects (for example, two at 15%). Other projects are not scheduled or measured by this script.
- Each invocation starts an independent NEW AGY headless conversation from its own project working directory. No --continue or /resume. GitHub AGENTS instructions, roadmap/current queue, reviews and latest handoffs provide recovery context.
- Every ten minutes, a local launchd job tests eligibility. As a project approaches its cap, cooldown grows from 10 to 20, 40 and 75 minutes, shortening automatically when older usage rolls out of the five-hour window.
- Both projects must explicitly select the **same Gemini model**. It does not intentionally use Claude, Codex or Anthropic models.
- **Provider quota caveat:** The documented AGY headless CLI reports per-run token usage in stream-json, but the documented /usage quota viewer is interactive. The 35% applies only to YOUR CONFIGURED token budget, not automatically detected Google account limits. Manual work, other devices and other tools aren't counted. No universal number of quota tokens per five hours can be assumed. If token capacity is unknown, the scheduler fails closed.
- The scheduler reserves estimated tokens and attempts to interrupt when observed stream usage reaches the reserved limit. Reporting may arrive late, so a run can exceed its allowance; it records overruns. Crashes/missing usage conservatively charge the full reservation. This is not a provider-enforced hard cap.

## Setup once on the Mac

1. Clone/pull BOTH repos on the same Mac. Authenticate the Antigravity CLI interactively. Verify agy models and agy -p "hello" --output-format stream-json. Review actual CLI permissions before unattended use.
2. Copy docs/agy-autopilot.example.json to ~/.config/agy-autopilot/config.json (chmod 600). Set absolute clone paths for BOTH projects, the same model slug from agy models, and a conservative known token_budget_per_5h. If you know only request-based quota, do not silently invent a token conversion.
3. From EITHER checkout preview: python3 scripts/agy_autopilot.py status; python3 scripts/agy_autopilot.py tick --project scalar-wave-viz (dry-run); python3 scripts/install_agy_launchd.py --config ~/.config/agy-autopilot/config.json (dry-run).
4. Run python3 -m unittest discover -s tests -p 'test_agy_autopilot.py' -v. On macOS, activate with: python3 scripts/install_agy_launchd.py --config ~/.config/agy-autopilot/config.json --install
5. Check live jobs with launchctl list | grep io.aguacatero.agy-autopilot and python3 scripts/agy_autopilot.py status. Local logs and usage database are written under ~/.local/state/agy-autopilot, not committed to GitHub.
6. To stop, run launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/io.aguacatero.agy-autopilot.scalar-wave-viz.plist and repeat for the septuagint-diaspora-book plist; remove the two plist files. Running the scheduler on another Mac without a shared ledger would void these caps.
7. Observe at least two actual launches and verify distinct conversations, usage accounting and correct GitHub handoffs. No automated merges or evidence promotion. If host checks are incomplete, report NOT ENABLED/UNVERIFIED.

The Scalar scientific baseline PR and the book's staged-research review gates remain authoritative. Agents must stop at a safe checkpoint and wait for authorized independent approval.

References: https://www.antigravity.google/docs/cli/headless/ and https://www.antigravity.google/docs/cli/commands/usage
