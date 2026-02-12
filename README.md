# Travel Anomaly Triage Agent

A Microsoft Security Copilot agent that automatically investigates **atypical travel**
and **impossible travel** alerts from Microsoft Defender and Sentinel.

## What It Does

When triggered with a travel anomaly alert, the agent runs a 5-step investigation:

1. **Extract Alert Context** — Parses the alert for user, device, IPs, locations, and
   timestamps.
2. **Check Device Compliance** — Queries Microsoft Graph to determine if the sign-in
   was from a company-managed, compliant device.
3. **Check Out of Office** — Queries Microsoft Graph for the user's automatic replies
   status and scheduled dates.
4. **Analyze Sign-In History** — Runs a KQL query against Sentinel for the user's last
   30 days of sign-in activity to build a location profile.
5. **Correlate & Verdict** — Combines all evidence to produce a triage verdict:
   **False Positive**, **Suspicious**, or **True Positive** with a confidence level.

Steps 2–4 run in parallel. The agent does not auto-close alerts — analysts approve
the final disposition.

## Project Structure

```
security-agent/
├── manifest/
│   ├── AgentManifest.yaml            # Security Copilot agent manifest
│   └── skills/
│       ├── openapispec_1.yaml        # Graph API — device compliance
│       ├── openapispec_2.yaml        # Graph API — Out of Office
│       └── kql/
│           └── analyze_signin_history.kql
├── tests/
│   ├── TESTING_GUIDE.md              # Step-by-step testing instructions
│   └── sample_alerts/
│       ├── atypical_travel.json      # Sample: expected False Positive
│       └── impossible_travel.json    # Sample: expected True Positive
├── scripts/
│   └── package.sh                    # Build .zip for Security Store
├── docs/
│   └── AGENT_DESIGN.md              # Architecture and design decisions
├── MS_SECURITY_STORE_REQUIREMENTS.md # Security Store publishing requirements
├── package.json                      # Version and metadata
└── README.md
```

## Prerequisites

- Security Copilot workspace with SCU capacity
- Microsoft Sentinel workspace with `SigninLogs` table
- Microsoft Graph API permissions:
  - `Device.Read.All`
  - `MailboxSettings.Read`

## Quick Start

### 1. Upload to Security Copilot

1. Open Security Copilot standalone experience.
2. Go to agent management and select **Upload a YAML**.
3. Upload `manifest/AgentManifest.yaml`.

### 2. Test

See `tests/TESTING_GUIDE.md` for detailed test cases and expected results.

Example prompt:

```
Investigate this atypical travel alert:
User jdoe@contoso.com signed in from New York (203.0.113.50) at 06:30 UTC,
then from London (198.51.100.23) at 09:00 UTC. Device ID:
d8e8fca2-dc0f-11e6-bf26-cec0c932ce01. Estimated travel speed: 2,228 km/h.
```

### 3. Package for Security Store

```bash
./scripts/package.sh 1.0.0
```

This produces `build/TravelAnomalyTriageAgent-1.0.0.zip` ready for Partner Center
submission.

## Estimated SCU Consumption

~4 SCU per incident run.

| Component | SCUs |
|-----------|------|
| Alert parsing (GPT) | ~1 |
| Graph API calls (device + OOO) | ~0.5 |
| KQL query (sign-in history) | ~1 |
| Correlation & verdict (GPT) | ~1.5 |

## Security Store Publishing

See `MS_SECURITY_STORE_REQUIREMENTS.md` for the full requirements checklist.
See `docs/AGENT_DESIGN.md` for the architecture and verdict logic.
