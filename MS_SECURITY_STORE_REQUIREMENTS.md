# Microsoft Security Store — Agent Publishing Requirements

This document summarizes the requirements for building and publishing a Security Copilot
agent in the Microsoft Security Store, based on current Microsoft documentation (as of
early 2026).

---

## 1. Partner Prerequisites

### 1.1 Partner Center Account

- Create a [Microsoft Partner Center](https://partner.microsoft.com/) account.
- During signup, select both the **Partner** and **Build** options.
- Validation and legal contract processing can take up to two weeks for new accounts.

### 1.2 Microsoft AI Cloud Partner Program (MAICPP)

- Enroll in **MAICPP** through Partner Center.
- On approval you receive a **Microsoft Partner Network ID (MPN ID)**.
- Optionally apply for the **ISV Success Program** for additional support.

### 1.3 Security Store Preview Registration

- Fill out the preview registration form at https://securitystore.microsoft.com/partners
- Accept the addendum to the Microsoft Publisher Agreement.
- Wait for the product team to review and grant access.

### 1.4 Account Requirements

- Must use a **work account** (not a personal Microsoft account).
- Legal business name, address, and primary contact required.
- Authority to sign agreements on behalf of the organization.
- Business verification documents must be ready.

---

## 2. What Can Be Published

Eligible solution types for the Security Store:

| Type | Notes |
|------|-------|
| **Security Copilot agents** | Published as a SaaS offer |
| **Microsoft Sentinel connectors** | Data connectors |
| **Linked SaaS solutions** | Required by a Copilot agent or Sentinel connector; must share the same publisher |
| **MISA-approved API integrations** | SaaS with qualified integrations into Defender, Intune, Entra, or Purview |
| **MXDR-certified Professional Services** | Managed detection & response services |

Only **transactable SaaS** solutions are supported. The offer type in Partner Center is
always **Software as a Service** — even for agents.

---

## 3. Agent Definition Requirements

### 3.1 What Qualifies as an Agent

An agent is defined as a **goal-oriented system that can autonomously generate a
multistep plan**. The core value is its ability to use **reasoning, memory, and tools** to
create a sequence of actions to meet an objective.

The agent's plan may require **human approval** for final execution.

### 3.2 What Gets Rejected

- **LLM wrappers** are rejected as ineligible. An LLM wrapper responds to a single prompt
  with information that a predefined instruction produces but does not generate a multistep
  plan. If you can get the same output by running the instruction as a prompt in Copilot,
  it is not an agent.
- Agents that deviate from user intent or the stated purpose.
- Agents that do not comply with Responsible AI (RAI) standards.

### 3.3 Agent Capability Categories

| Category | Examples |
|----------|----------|
| **Cognitive** | Classify alerts, summarize incidents, correlate signals |
| **Conversational** | Interpret user prompts, generate clear explanations |
| **Operational** | Trigger workflows, call APIs, retrieve logs/documents |

---

## 4. Agent Manifest (YAML/JSON)

The agent manifest file (e.g., `manifest.yaml`) defines the agent and its tools.

### 4.1 Top-Level Keys

| Key | Purpose | Required |
|-----|---------|----------|
| `Descriptor` | Agent metadata: `Name`, `Description`, `DisplayName` | Yes |
| `SkillGroups` | Tool/skill definitions | Yes |
| `AgentDefinitions` | Agent blueprint: name, triggers, required skillsets, settings | Yes |

There can only be **one** `AgentDefinition` per manifest.

### 4.2 Descriptor

```yaml
Descriptor:
  Name: MySecurityAgent
  DisplayName: My Security Agent
  Description: >
    Triages Defender incidents by correlating threat intelligence
    and recommending remediation.
```

- `DisplayName` should be **< 30 characters** to avoid truncation in the Security Copilot UX.

### 4.3 SkillGroups

Supported formats:

| Format | Use Case |
|--------|----------|
| `API` | Call external REST APIs via OpenAPI spec |
| `KQL` | Run Kusto Query Language queries |
| `GPT` | Natural-language reasoning / prompt-based skills |
| `AGENT` | Reference another agent as a sub-skill |

Skills defined in the same manifest are referenced via `ChildSkills`. Skills from other
manifests are referenced via `RequiredSkillsets`.

`FetchSkill` and `ProcessSkill` must be namespaced: `SkillsetName.SkillName`.

### 4.4 AgentDefinitions

```yaml
AgentDefinitions:
  - Name: IncidentTriageAgent
    Publisher: ContosoSecurity
    Product: TriageBot
    RequiredSkillsets:
      - MySecurityAgent
    Triggers:
      - Type: Interactive
    Settings:
      ModelOptions:
        Temperature: 0.2
```

### 4.5 Authentication

Security Copilot supports several authentication schemes for tools:

- **On-behalf-of (OBO)** — default; uses the signed-in user's identity.
- **Plugin-managed auth** — the plugin determines its own authentication flow.

---

## 5. Package Structure for Publishing

The deployment package is a **`.zip`** file with a structured folder layout.

### 5.1 Required Files

| File | Description |
|------|-------------|
| `AgentManifest.yaml` | The agent manifest (one per package) |
| `openapispec_<N>.yaml` / `.json` | OpenAPI specs for API plugins |
| `template_<N>.txt` | Templates for GPT or KQL plugins |
| `.job.yaml` + notebook | For Sentinel Data Lake Notebook jobs |
| `mainTemplate.json` | (Optional) ARM template for Azure resource deployment |

### 5.2 Versioning

- Follow **semantic versioning**: `X.Y.Z` (major.minor.patch).
- Security Copilot agents are **always automatically updated** to the latest version.

### 5.3 Security Scanning

Packages must pass scans for:
- Malware
- Anti-virus
- Agent vulnerability scanning

---

## 6. Certification Requirements

### 6.1 Functional & Quality Tests

- Successful deployment, setup, and run aligned with the agent description.
- Agent must use Security Copilot platform capabilities appropriately.

### 6.2 Integration Criteria

- **Relevance**: Agent description and function must align with the personas and use cases
  of the integrated Microsoft Security product.
- **Integration**: Must integrate with at least one Microsoft Security product (Defender,
  Sentinel, Entra, Purview, Intune) via Copilot skill, custom plugin, MCP, etc.
- **Customer value**: Must enhance the customer experience with Microsoft Security products.

### 6.3 Microsoft Defender Portal Criteria (if targeting Defender)

- Must align with Defender / Sentinel personas: SOC analysts, threat hunters, IT admins,
  incident responders, or compliance officers.
- Must enable SOC operations, threat hunting, exposure reduction, identity risk mitigation,
  or compliance.
- Description must specify how the agent works with Defender (inputs, tasks, outputs).

### 6.4 Responsible AI (RAI)

- Must comply with Microsoft RAI standards.
- Must not contain instructions that deviate from user intent or stated purpose.
- Must enable users to verify information sources.
- Must clearly communicate what data is stored in memory and how it is used.
- Must show how decisions were made.

### 6.5 Compliance Attestation

- Optional self-attestation for alignment with **NIST CSF 2.0** framework.
- Any certifications attested must use valid URLs.

---

## 7. Listing & Description Requirements

### 7.1 Naming

- Agent name: **< 30 characters** (to avoid truncation).

### 7.2 Description

Must clearly state:

- **Inputs**: What data the agent consumes (e.g., Defender incidents, TI data).
- **Tasks**: What the agent does (e.g., look up entities, correlate threat intelligence).
- **Outputs**: What the agent produces (e.g., triage result with confidence level and
  remediation plan).

### 7.3 SCU Consumption

- The plan description **must** specify estimated **Security Compute Unit (SCU)**
  consumption, relating it to inputs, tasks, and outputs.

### 7.4 Marketing Link

- Partners must add a link to their marketing or product page in the **Links** section of
  Partner Center.
- The linked page must provide instructions to install/use the agent and link back to the
  Security Store.

---

## 8. Licensing & Pricing

### 8.1 Pricing Model

- Only **contract (by subscription)** pricing is supported when Microsoft manages licenses.
- Billing can be **monthly** or **annual**.
- Even free agents require a price entry — set to **$0 USD**.

### 8.2 SCU Costs

- SCU costs for third-party agents are currently included, but this may change as Security
  Copilot inclusion rolls out more broadly.
- Customers need a Security Copilot workspace provisioned with SCU capacity.

### 8.3 Offer Linking

- If your agent requires a companion SaaS solution, the two offers must be **linked** during
  publishing.
- Linked offers must have valid offer IDs owned by the **same publisher**.

---

## 9. Publishing Workflow (Step by Step)

1. **Create Partner Center account** — select Partner + Build options.
2. **Enroll in MAICPP** — obtain MPN ID.
3. **Register for Security Store preview** — fill out form, accept publisher agreement
   addendum.
4. **Create SaaS offer** in Partner Center — offer type = Software as a Service.
   - When asked "Would you like to sell through Microsoft?" — select **Yes**.
5. **Configure Offer Setup** — check the box for Microsoft Security integration.
   - If not hosted on Azure: select "SaaS isn't hosted on Azure" and note it is for the
     Security Store.
6. **Integrate with SaaS APIs** — landing page, webhook, lifecycle events, metering.
7. **Fill out Security Store metadata** — integration type, prerequisites, agent inclusion,
   compliance certifications.
8. **Package the agent** — create `.zip` with manifest, specs, and templates.
9. **Test via preview audience** — preview and end-to-end test before go-live.
10. **Submit for review** — Microsoft sends approval email; click **Go live** in Partner
    Center.

---

## 10. Development Planning Phases

### Phase 1: Planning & Design

- Identify target users (SOC analysts, IT admins, compliance officers, developers).
- Define success metrics (reduced triage time, improved detection accuracy, etc.).
- Map data sources (Defender, Sentinel, Microsoft Graph, external APIs).
- Determine capability type: cognitive, conversational, or operational.

### Phase 2: Environment & Integration Setup

- Configure Azure subscription and Entra ID.
- Set up RBAC and conditional access policies.
- Identify data sources and API endpoints.
- Plan state management via agent memories.

### Phase 3: Build & Manifest Creation

- Author the YAML manifest with `Descriptor`, `SkillGroups`, and `AgentDefinitions`.
- Implement tools (API, KQL, GPT, or AGENT skills).
- Use VS Code with GitHub Copilot and Sentinel MCP tools for development.

### Phase 4: Testing

- Deploy to Security Copilot standalone experience.
- Validate deployment, setup, and run experiences.
- Test against the description's stated inputs, tasks, and outputs.
- Verify RAI compliance.

### Phase 5: Publishing & Deployment

- Package into `.zip` per schema requirements.
- Submit via Partner Center.
- Pass certification (functional, quality, security scanning).
- Monitor via Copilot Control System in Microsoft 365 admin center.

---

## 11. Key Resources

| Resource | URL |
|----------|-----|
| Security Store Overview | https://learn.microsoft.com/en-us/copilot/security/security-store-integration |
| Plan Your Publication | https://learn.microsoft.com/en-us/security/store/plan-your-publication-for-security-store |
| Publish an Agent | https://learn.microsoft.com/en-us/security/store/publish-a-security-copilot-agent-or-analytics-solution-in-security-store |
| Security Store Certification | https://learn.microsoft.com/en-us/security/store/security-store-certification |
| Partner Listing Guide | https://learn.microsoft.com/en-us/security/store/security-store-partner-listing-guide |
| Agent Manifest Reference | https://learn.microsoft.com/en-us/copilot/security/developer/agent-manifest |
| Manifest Best Practices | https://learn.microsoft.com/en-us/copilot/security/developer/manifest-best-practices |
| Agent Components | https://learn.microsoft.com/en-us/copilot/security/developer/agent-components |
| Agent Development Planning Guide | https://learn.microsoft.com/en-us/copilot/security/developer/planning-guide |
| Build Agent via YAML | https://learn.microsoft.com/en-us/copilot/security/developer/build-agent-manifest |
| Custom Plugins Overview | https://learn.microsoft.com/en-us/copilot/security/custom-plugins |
| Azure/Security-Copilot GitHub | https://github.com/Azure/Security-Copilot |
| Security Store Partner Registration | https://securitystore.microsoft.com/partners |
