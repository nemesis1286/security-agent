#!/usr/bin/env python3
"""
Pre-flight validation for the Travel Anomaly Triage Agent.

Architecture:
  - AgentManifest.yaml     — Agent entrypoint (AGENT) + GPT + KQL skills
  - ApiPluginManifest.yaml — Separate API plugin (uploaded first as custom plugin)
  - openapispec_1.yaml     — OpenAPI spec for device compliance
  - openapispec_2.yaml     — OpenAPI spec for Out of Office
"""

import sys
import os
import json
import yaml

AGENT_MANIFEST = "manifest/AgentManifest.yaml"
API_PLUGIN_MANIFEST = "manifest/ApiPluginManifest.yaml"
OPENAPI_SPECS = [
    "manifest/skills/openapispec_1.yaml",
    "manifest/skills/openapispec_2.yaml",
]
KQL_FILES = [
    "manifest/skills/kql/analyze_signin_history.kql",
]
SAMPLE_ALERTS = [
    "tests/sample_alerts/atypical_travel.json",
    "tests/sample_alerts/impossible_travel.json",
]

errors = []
warnings = []


def check(label, condition, msg):
    if not condition:
        errors.append(f"  FAIL: {label} — {msg}")
        return False
    print(f"  PASS: {label}")
    return True


def warn(label, msg):
    warnings.append(f"  WARN: {label} — {msg}")


def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)


def validate_agent_manifest():
    print("\n=== Agent Manifest ===")
    print(f"  File: {AGENT_MANIFEST}")

    if not os.path.exists(AGENT_MANIFEST):
        errors.append(f"  FAIL: File not found — {AGENT_MANIFEST}")
        return

    try:
        manifest = load_yaml(AGENT_MANIFEST)
    except yaml.YAMLError as e:
        errors.append(f"  FAIL: YAML syntax error — {e}")
        return

    check("YAML parses successfully", manifest is not None, "Empty manifest")

    # Top-level keys
    check("Descriptor key exists", "Descriptor" in manifest, "Missing 'Descriptor'")
    check("SkillGroups key exists", "SkillGroups" in manifest, "Missing 'SkillGroups'")
    check("AgentDefinitions key exists", "AgentDefinitions" in manifest, "Missing 'AgentDefinitions'")

    # Descriptor
    desc = manifest.get("Descriptor", {})
    check("Descriptor.Name present", "Name" in desc, "Missing 'Name'")
    check("Descriptor.DisplayName present", "DisplayName" in desc, "Missing 'DisplayName'")
    check("Descriptor.Description present", "Description" in desc, "Missing 'Description'")

    display_name = desc.get("DisplayName", "")
    if len(display_name) >= 30:
        warn("DisplayName length", f"'{display_name}' is {len(display_name)} chars (recommend < 30)")
    else:
        check(f"DisplayName < 30 chars ({len(display_name)})", True, "")

    # SkillGroups
    skill_groups = manifest.get("SkillGroups", [])
    formats_found = set()
    all_skill_names = []
    agent_entrypoint = None

    for group in skill_groups:
        fmt = group.get("Format", "")
        formats_found.add(fmt)
        check(f"SkillGroup format '{fmt}' is valid", fmt in ("GPT", "KQL", "AGENT"), f"Unknown or misplaced format: {fmt}")

        for skill in group.get("Skills", []):
            all_skill_names.append(skill.get("Name", ""))
            check(f"Skill '{skill.get('Name', '?')}' has Name", "Name" in skill, "Missing 'Name'")
            check(f"Skill '{skill.get('Name', '?')}' has Description", "Description" in skill, "Missing 'Description'")

            if fmt == "AGENT":
                agent_entrypoint = skill
                check(f"AGENT skill has Interfaces", "Interfaces" in skill, "Missing 'Interfaces'")
                interfaces = skill.get("Interfaces", [])
                check(
                    f"AGENT skill declares Agent interface",
                    "Agent" in interfaces or "InteractiveAgent" in interfaces,
                    f"Interfaces {interfaces} must include 'Agent' or 'InteractiveAgent'"
                )
                settings = skill.get("Settings", {})
                check(f"AGENT skill has Settings.Model", "Model" in settings, "Missing")
                check(f"AGENT skill has Settings.Instructions", "Instructions" in settings, "Missing")
                check(f"AGENT skill has Settings.ChildSkills", "ChildSkills" in settings, "Missing")

            if fmt == "KQL":
                settings = skill.get("Settings", {})
                check(f"KQL skill has Target", "Target" in settings, "Missing Settings.Target")
                template = settings.get("Template", "")
                check(f"KQL skill has inline Template", bool(template) and "SigninLogs" in template, "Missing/empty")

    check("Format: AGENT exists", "AGENT" in formats_found, "Missing — this is the 'agent tool' Copilot requires")
    check("No Format: API in agent manifest", "API" not in formats_found, "API skills must be in a separate plugin manifest")

    print(f"\n  Skill formats: {', '.join(sorted(formats_found))}")
    print(f"  Skills in agent manifest: {len(all_skill_names)}")

    # AgentDefinitions
    agent_defs = manifest.get("AgentDefinitions", [])
    check("Exactly one AgentDefinition", len(agent_defs) == 1, f"Found {len(agent_defs)}")

    if agent_defs:
        agent = agent_defs[0]
        check("Agent.Name present", "Name" in agent, "Missing")
        check("Agent.Description present", "Description" in agent, "Missing")
        check("Agent.Triggers present", "Triggers" in agent, "Missing")
        check("Agent.RequiredSkillsets present", "RequiredSkillsets" in agent, "Missing")

        skillset_name = desc.get("Name", "")
        required = agent.get("RequiredSkillsets", [])
        check(f"RequiredSkillsets includes own skillset '{skillset_name}'", skillset_name in required, "Missing")
        check(
            "RequiredSkillsets includes API plugin",
            "TravelAnomalyTriageApiPlugin" in required,
            "Missing 'TravelAnomalyTriageApiPlugin' — needed for API skills"
        )

        triggers = agent.get("Triggers", [])
        if triggers:
            trigger = triggers[0]
            check("Trigger has Name", "Name" in trigger, "Missing")
            process_skill = trigger.get("ProcessSkill", "")
            check("Trigger has ProcessSkill", bool(process_skill), "Missing")
            if agent_entrypoint:
                expected = f"{skillset_name}.{agent_entrypoint['Name']}"
                check(f"ProcessSkill = '{expected}'", process_skill == expected, f"Got '{process_skill}'")

    return manifest


def validate_api_plugin_manifest():
    print("\n=== API Plugin Manifest ===")
    print(f"  File: {API_PLUGIN_MANIFEST}")

    if not os.path.exists(API_PLUGIN_MANIFEST):
        errors.append(f"  FAIL: File not found — {API_PLUGIN_MANIFEST}")
        return

    try:
        plugin = load_yaml(API_PLUGIN_MANIFEST)
    except yaml.YAMLError as e:
        errors.append(f"  FAIL: YAML syntax error — {e}")
        return

    check("YAML parses successfully", plugin is not None, "Empty")

    # Descriptor
    desc = plugin.get("Descriptor", {})
    check("Descriptor.Name present", "Name" in desc, "Missing")
    check("Descriptor.Name = 'TravelAnomalyTriageApiPlugin'",
          desc.get("Name") == "TravelAnomalyTriageApiPlugin",
          f"Got '{desc.get('Name')}' — must match RequiredSkillsets in agent manifest")
    check("Descriptor.DisplayName present", "DisplayName" in desc, "Missing")
    check("Descriptor.Description present", "Description" in desc, "Missing")

    # Must NOT have AgentDefinitions (this is a plugin, not an agent)
    check("No AgentDefinitions (plugin only)", "AgentDefinitions" not in plugin,
          "A plugin manifest must not contain AgentDefinitions")

    # SkillGroups — should only contain API format
    skill_groups = plugin.get("SkillGroups", [])
    check("Has SkillGroups", len(skill_groups) > 0, "Empty")

    api_skill_names = []
    for group in skill_groups:
        fmt = group.get("Format", "")
        check(f"SkillGroup format is API", fmt == "API", f"Got '{fmt}' — plugin should only have API skills")

        for skill in group.get("Skills", []):
            name = skill.get("Name", "?")
            api_skill_names.append(name)
            check(f"API skill '{name}' has Name", "Name" in skill, "Missing")
            check(f"API skill '{name}' has Description", "Description" in skill, "Missing")

            settings = skill.get("Settings", {})
            check(f"API skill '{name}' has OpenApiSpecUrl", "OpenApiSpecUrl" in settings, "Missing")
            check(f"API skill '{name}' has EndpointUrl", "EndpointUrl" in settings, "Missing")

    print(f"\n  API skills: {', '.join(api_skill_names)}")

    # Verify agent manifest ChildSkills reference these API skills
    if os.path.exists(AGENT_MANIFEST):
        agent_manifest = load_yaml(AGENT_MANIFEST)
        for group in agent_manifest.get("SkillGroups", []):
            if group.get("Format") != "AGENT":
                continue
            for skill in group.get("Skills", []):
                child_skills = skill.get("Settings", {}).get("ChildSkills", [])
                for api_name in api_skill_names:
                    check(
                        f"Agent ChildSkills references '{api_name}'",
                        api_name in child_skills,
                        f"'{api_name}' not in ChildSkills — agent won't be able to call it"
                    )


def validate_openapi_specs():
    print("\n=== OpenAPI Specs ===")
    for spec_path in OPENAPI_SPECS:
        print(f"\n  File: {spec_path}")
        if not os.path.exists(spec_path):
            errors.append(f"  FAIL: File not found — {spec_path}")
            continue

        try:
            spec = load_yaml(spec_path)
        except yaml.YAMLError as e:
            errors.append(f"  FAIL: YAML syntax error — {e}")
            continue

        check("YAML parses successfully", spec is not None, "Empty")
        check("openapi version present", "openapi" in spec, "Missing 'openapi'")
        check("info present", "info" in spec, "Missing 'info'")
        check("paths present", "paths" in spec, "Missing 'paths'")
        check("servers present", "servers" in spec, "Missing 'servers'")

        servers = spec.get("servers", [])
        if servers:
            url = servers[0].get("url", "")
            check("Server URL is Graph API", "graph.microsoft.com" in url, f"Got: {url}")

        paths = spec.get("paths", {})
        for path, methods in paths.items():
            for method, op in methods.items():
                if method in ("get", "post", "put", "patch", "delete"):
                    check(f"{method.upper()} {path} has operationId", "operationId" in op, "Missing")
                    check(f"{method.upper()} {path} has responses", "responses" in op, "Missing")


def validate_kql_standalone():
    print("\n=== KQL Templates (standalone) ===")
    for kql_path in KQL_FILES:
        print(f"\n  File: {kql_path}")
        if not os.path.exists(kql_path):
            errors.append(f"  FAIL: File not found — {kql_path}")
            continue

        with open(kql_path) as f:
            content = f.read()

        check("Not empty", len(content.strip()) > 0, "Empty")
        check("SigninLogs", "SigninLogs" in content, "Missing")
        check("{{UserPrincipalName}}", "{{UserPrincipalName}}" in content, "Missing")
        check("{{DestinationIP}}", "{{DestinationIP}}" in content, "Missing")
        check("{{DestinationLocation}}", "{{DestinationLocation}}" in content, "Missing")
        check("30d lookback", "30d" in content, "Missing")
        check("summarize", "summarize" in content, "Missing")
        check("where", "where" in content, "Missing")
        check("extend", "extend" in content, "Missing")


def validate_kql_inline():
    print("\n=== KQL Template (inlined in manifest) ===")
    manifest = load_yaml(AGENT_MANIFEST)
    for group in manifest.get("SkillGroups", []):
        if group.get("Format") != "KQL":
            continue
        for skill in group.get("Skills", []):
            template = skill.get("Settings", {}).get("Template", "")
            print(f"\n  Skill: {skill.get('Name', '?')}")
            check("Not empty", len(template.strip()) > 0, "Empty")
            check("SigninLogs", "SigninLogs" in template, "Missing")
            check("{{UserPrincipalName}}", "{{UserPrincipalName}}" in template, "Missing")
            check("{{DestinationIP}}", "{{DestinationIP}}" in template, "Missing")
            check("{{DestinationLocation}}", "{{DestinationLocation}}" in template, "Missing")
            check("30d lookback", "30d" in template, "Missing")
            check("summarize", "summarize" in template, "Missing")
            check("where", "where" in template, "Missing")
            check("extend", "extend" in template, "Missing")


def validate_sample_alerts():
    print("\n=== Sample Alerts ===")
    for alert_path in SAMPLE_ALERTS:
        print(f"\n  File: {alert_path}")
        if not os.path.exists(alert_path):
            errors.append(f"  FAIL: File not found — {alert_path}")
            continue

        with open(alert_path) as f:
            try:
                alert = json.load(f)
            except json.JSONDecodeError as e:
                errors.append(f"  FAIL: JSON syntax error — {e}")
                continue

        check("JSON valid", alert is not None, "Empty")
        check("alertType", "alertType" in alert, "Missing")
        check("userPrincipalName", "userPrincipalName" in alert, "Missing")
        check("sourceSignIn", "sourceSignIn" in alert, "Missing")
        check("destinationSignIn", "destinationSignIn" in alert, "Missing")
        check("travelDetails", "travelDetails" in alert, "Missing")

        src = alert.get("sourceSignIn", {})
        check("sourceSignIn.ipAddress", "ipAddress" in src, "Missing")
        check("sourceSignIn.location", "location" in src, "Missing")

        dst = alert.get("destinationSignIn", {})
        check("destinationSignIn.ipAddress", "ipAddress" in dst, "Missing")
        check("destinationSignIn.location", "location" in dst, "Missing")


def validate_package_structure():
    print("\n=== Package Structure ===")
    check("AgentManifest.yaml", os.path.exists(AGENT_MANIFEST), "Missing")
    check("ApiPluginManifest.yaml", os.path.exists(API_PLUGIN_MANIFEST), "Missing")
    check("openapispec_1.yaml", os.path.exists(OPENAPI_SPECS[0]), "Missing")
    check("openapispec_2.yaml", os.path.exists(OPENAPI_SPECS[1]), "Missing")
    check("KQL template", os.path.exists(KQL_FILES[0]), "Missing")
    check("package.sh", os.path.exists("scripts/package.sh"), "Missing")
    check("package.sh executable", os.access("scripts/package.sh", os.X_OK), "Not executable")


if __name__ == "__main__":
    os.chdir(os.path.join(os.path.dirname(__file__), ".."))

    print("=" * 60)
    print("  Travel Anomaly Triage Agent — Pre-flight Validation")
    print("=" * 60)

    validate_agent_manifest()
    validate_api_plugin_manifest()
    validate_openapi_specs()
    validate_kql_standalone()
    validate_kql_inline()
    validate_sample_alerts()
    validate_package_structure()

    print("\n" + "=" * 60)
    if warnings:
        print(f"\n  Warnings ({len(warnings)}):")
        for w in warnings:
            print(w)

    if errors:
        print(f"\n  Errors ({len(errors)}):")
        for e in errors:
            print(e)
        print(f"\n  RESULT: FAILED — {len(errors)} error(s)")
        sys.exit(1)
    else:
        print(f"\n  RESULT: ALL CHECKS PASSED")
        print("\n  Upload order:")
        print("    1. Upload ApiPluginManifest.yaml as a custom PLUGIN first")
        print("    2. Then upload AgentManifest.yaml as the AGENT")
        sys.exit(0)
