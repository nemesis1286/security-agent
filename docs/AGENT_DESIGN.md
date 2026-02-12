# Travel Anomaly Triage Agent — Design Document

## Overview

The **Travel Anomaly Triage Agent** automatically investigates atypical and impossible
travel alerts from Microsoft Defender and Sentinel. It runs a series of enrichment checks
to determine whether the alert is a false positive or requires analyst attention.

## Target Users

- **SOC Analysts** performing alert triage in Microsoft Defender / Sentinel.

## Integrated Products

- **Microsoft Defender for Identity** — source of atypical/impossible travel alerts.
- **Microsoft Sentinel** — sign-in log queries, incident correlation.
- **Microsoft Entra ID** — device compliance, user properties.
- **Microsoft Graph API** — Out of Office status, mailbox settings.

## Success Metrics

- Reduced mean time to triage (MTTT) for travel-related alerts.
- Reduction in false positive escalations to Tier 2.
- Analyst confidence in automated triage verdicts.

---

## Agent Workflow

```
┌─────────────────────────────────────┐
│  Trigger: Atypical / Impossible     │
│  Travel Alert                       │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Step 1: Extract Alert Context      │
│  - User principal name (UPN)        │
│  - Source & destination IPs/locations│
│  - Device ID                        │
│  - Timestamp                        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Step 2: Device Compliance Check    │
│  (Entra / Intune)                   │
│                                     │
│  Was the sign-in from a company-    │
│  managed, compliant device?         │
│  → YES = strong FP indicator        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Step 3: Out of Office Check        │
│  (Graph API / Exchange)             │
│                                     │
│  Does the user have OOO configured? │
│  If so, what dates and message?     │
│  → OOO active = user likely         │
│    traveling (supports FP)          │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Step 4: Sign-In History Analysis   │
│  (Sentinel KQL — last 30 days)      │
│                                     │
│  - Distinct IPs and geolocations    │
│  - Frequency of location changes    │
│  - Whether destination IP/location  │
│    has been seen before             │
│  → Known location = supports FP     │
│  → Never-seen location = anomaly    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Step 5: Correlate & Verdict        │
│  (GPT reasoning skill)             │
│                                     │
│  Combine all signals:               │
│  - Device compliance result         │
│  - OOO status                       │
│  - IP history analysis              │
│                                     │
│  Produce:                           │
│  - Verdict: FP / Suspicious / TP    │
│  - Confidence: High / Medium / Low  │
│  - Evidence summary                 │
│  - Recommended next steps           │
└─────────────────────────────────────┘
```

---

## Skills (Tools)

### Skill 1: ExtractAlertContext (GPT)

- **Type**: GPT
- **Purpose**: Parse the incoming alert and extract the user principal name, source/
  destination IPs, locations, device ID, and timestamps.
- **Input**: Raw alert data from Defender / Sentinel incident.
- **Output**: Structured context object.

### Skill 2: CheckDeviceCompliance (API)

- **Type**: API (Microsoft Graph)
- **Endpoint**: `GET /devices` filtered by device ID, then check `isCompliant` and
  `isManaged` properties.
- **Auth**: On-behalf-of (OBO).
- **Purpose**: Determine if the sign-in device is company-issued and compliant.
- **Output**: `{ isManaged: bool, isCompliant: bool, deviceName: string }`.

### Skill 3: CheckOutOfOffice (API)

- **Type**: API (Microsoft Graph)
- **Endpoint**: `GET /users/{upn}/mailboxSettings` — read `automaticRepliesSetting`.
- **Auth**: On-behalf-of (OBO).
- **Purpose**: Check if the user has Out of Office / automatic replies enabled.
- **Output**: `{ oooEnabled: bool, scheduledStartDateTime: string,
  scheduledEndDateTime: string, externalReplyMessage: string }`.

### Skill 4: AnalyzeSignInHistory (KQL)

- **Type**: KQL
- **Data source**: `SigninLogs` table in Sentinel / Defender.
- **Purpose**: Query the last 30 days of sign-in logs for the user to build a location
  profile and detect anomalies.
- **Output**: Table of distinct IPs, locations, frequency, and whether the alert's
  destination was previously seen.

### Skill 5: CorrelateAndVerdict (GPT)

- **Type**: GPT
- **Purpose**: Reason over all collected evidence and produce a final triage verdict.
- **Input**: Outputs from Skills 1–4.
- **Output**: Verdict (False Positive / Suspicious / True Positive), confidence level,
  evidence summary, and recommended analyst actions.

---

## Verdict Logic

| Device Compliant | OOO Active | Destination IP Seen Before | Verdict | Confidence |
|:---:|:---:|:---:|---|---|
| Yes | Yes | Yes | **False Positive** | High |
| Yes | Yes | No  | **False Positive** | Medium |
| Yes | No  | Yes | **False Positive** | Medium |
| Yes | No  | No  | **Suspicious** | Medium |
| No  | Yes | Yes | **False Positive** | Medium |
| No  | Yes | No  | **Suspicious** | Medium |
| No  | No  | Yes | **Suspicious** | Low |
| No  | No  | No  | **True Positive** | High |

The GPT reasoning skill uses this matrix as a baseline but also considers additional
context such as impossible travel speed, sign-in frequency patterns, and OOO date
alignment with the alert timestamp.

---

## Estimated SCU Consumption

| Component | Estimated SCUs per Run |
|-----------|----------------------|
| Alert parsing (GPT) | ~1 SCU |
| Graph API calls (device + OOO) | ~0.5 SCU |
| KQL query (sign-in history) | ~1 SCU |
| Correlation & verdict (GPT) | ~1.5 SCU |
| **Total per incident** | **~4 SCU** |

---

## Responsible AI Considerations

- The agent provides a **recommendation**, not an automatic closure. Human approval is
  required for final disposition.
- All evidence is presented transparently so the analyst can verify the verdict.
- No user data is stored in agent memory beyond the session.
- The agent does not take remediation actions (block user, revoke session) without explicit
  analyst approval.

---

## File Structure

```
security-agent/
├── docs/
│   └── AGENT_DESIGN.md              # This document
├── manifest/
│   ├── AgentManifest.yaml            # Agent manifest
│   └── skills/
│       ├── openapispec_1.yaml        # Graph API — device compliance
│       ├── openapispec_2.yaml        # Graph API — OOO check
│       └── kql/
│           └── analyze_signin_history.kql
├── MS_SECURITY_STORE_REQUIREMENTS.md
└── README.md
```
