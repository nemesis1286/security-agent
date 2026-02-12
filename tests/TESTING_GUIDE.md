# Testing Guide — Travel Anomaly Triage Agent

## Prerequisites

- Access to a **Security Copilot workspace** with SCU capacity provisioned.
- **Microsoft Sentinel** workspace with `SigninLogs` table populated.
- **Microsoft Graph API** permissions:
  - `Device.Read.All` — for device compliance checks.
  - `MailboxSettings.Read` — for Out of Office checks.
- Test users with known sign-in history in your tenant.

---

## Step 1: Upload the Manifest

1. Open **Security Copilot** standalone experience.
2. Navigate to agent management.
3. Select **Upload a YAML**.
4. Upload `manifest/AgentManifest.yaml`.
5. Verify the agent builder displays:
   - 5 skills (ExtractAlertContext, CheckDeviceCompliance, CheckOutOfOffice,
     AnalyzeSignInHistory, CorrelateAndVerdict)
   - Agent overview matching the manifest description.

---

## Step 2: Test with Sample Alerts

### Test Case 1: Atypical Travel — Expected False Positive

**File**: `tests/sample_alerts/atypical_travel.json`

**Scenario**: Jane Doe signs in from New York, then from London 2.5 hours later.
Same company device (`CONTOSO-JD-LT01`) used in both sign-ins.

**Expected skill results**:

| Skill | Expected Outcome |
|-------|-----------------|
| ExtractAlertContext | UPN: jdoe@contoso.com, Device: d8e8fca2-..., NY → London |
| CheckDeviceCompliance | `isManaged: true, isCompliant: true` (company laptop) |
| CheckOutOfOffice | Depends on tenant config — test with OOO enabled |
| AnalyzeSignInHistory | London IP may/may not be in 30-day history |
| CorrelateAndVerdict | **False Positive** (Medium–High) — compliant device is strong signal |

**Prompt to test in Copilot**:
```
Investigate this atypical travel alert:
User jdoe@contoso.com signed in from New York (203.0.113.50) at 06:30 UTC,
then from London (198.51.100.23) at 09:00 UTC on the same day. Device ID:
d8e8fca2-dc0f-11e6-bf26-cec0c932ce01. Estimated travel speed: 2,228 km/h.
```

---

### Test Case 2: Impossible Travel — Expected True Positive

**File**: `tests/sample_alerts/impossible_travel.json`

**Scenario**: Bob Smith signs in from Chicago, then from Tokyo 15 minutes later.
No device ID in either sign-in. Different browsers and operating systems.

**Expected skill results**:

| Skill | Expected Outcome |
|-------|-----------------|
| ExtractAlertContext | UPN: bsmith@contoso.com, No device ID, Chicago → Tokyo |
| CheckDeviceCompliance | No device found / not managed (no device ID) |
| CheckOutOfOffice | Depends on tenant config — test with OOO disabled |
| AnalyzeSignInHistory | Tokyo IP likely not in 30-day history |
| CorrelateAndVerdict | **True Positive** (High) — no device, no OOO, unknown location, impossible speed |

**Prompt to test in Copilot**:
```
Investigate this impossible travel alert:
User bsmith@contoso.com signed in from Chicago (192.0.2.100) at 14:00 UTC,
then from Tokyo (203.0.113.200) at 14:15 UTC on the same day. No device ID
available. Different browsers used (Chrome on macOS vs Firefox on Linux).
Estimated travel speed: 40,580 km/h.
```

---

## Step 3: Validate Individual Skills

Test each skill independently before running the full agent workflow.

### ExtractAlertContext (GPT)

Paste raw alert JSON and verify structured fields are extracted correctly.

### CheckDeviceCompliance (API)

```
Check device compliance for device ID: d8e8fca2-dc0f-11e6-bf26-cec0c932ce01
```

Verify it returns `isManaged`, `isCompliant`, `displayName`, and `trustType`.

### CheckOutOfOffice (API)

```
Check Out of Office status for jdoe@contoso.com
```

Verify it returns `status`, `scheduledStartDateTime`, `scheduledEndDateTime`,
and reply messages.

### AnalyzeSignInHistory (KQL)

Run the KQL query directly in Sentinel to validate:

```kql
SigninLogs
| where TimeGenerated > ago(30d)
| where UserPrincipalName =~ "jdoe@contoso.com"
| summarize count() by IPAddress, tostring(LocationDetails.city)
| sort by count_ desc
```

Compare with the agent's `AnalyzeSignInHistory` output.

---

## Step 4: End-to-End Validation

1. Trigger the full agent with a test prompt.
2. Verify the agent executes all 5 steps in order.
3. Confirm the verdict aligns with the expected outcome.
4. Check that evidence is presented transparently.
5. Verify the agent does **not** auto-close or auto-remediate.

---

## Step 5: Edge Cases to Test

| Scenario | Expected Behavior |
|----------|------------------|
| Device ID missing from alert | Agent notes "device not found", skips compliance signal |
| User has no mailbox (service account) | OOO check returns error, agent continues with other signals |
| No sign-in history (new user) | Agent notes "insufficient history", lowers confidence |
| VPN IP detected | Agent should note the IP belongs to a known VPN range if applicable |
| Same city, different IP | Should lean toward False Positive |
| Alert already resolved | Agent still triages and provides verdict for validation |

---

## Step 6: SCU Consumption Check

After running several test cases, review SCU consumption in the Security Copilot
admin dashboard. Expected consumption: **~4 SCU per incident**. Document any
deviation for the Security Store plan description.
