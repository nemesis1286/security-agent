#!/usr/bin/env python3
"""
Pre-flight validation for the Travel Anomaly Triage Agent manifest and skills.
Checks YAML syntax, manifest structure, OpenAPI specs, and KQL template references.
"""

import sys
import os
import json
import yaml

MANIFEST_PATH = "manifest/AgentManifest.yaml"
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


def validate_manifest():
    print("\n=== Agent Manifest ===")
    print(f"  File: {MANIFEST_PATH}")

    if not os.path.exists(MANIFEST_PATH):
        errors.append(f"  FAIL: Manifest file not found at {MANIFEST_PATH}")
        return

    with open(MANIFEST_PATH) as f:
        try:
            manifest = yaml.safe_load(f)
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
        warn("DisplayName length", f"'{display_name}' is {len(display_name)} chars (recommend < 30 to avoid truncation)")
    else:
        check(f"DisplayName < 30 chars ({len(display_name)})", True, "")

    # AgentDefinitions
    agent_defs = manifest.get("AgentDefinitions", [])
    check("Exactly one AgentDefinition", len(agent_defs) == 1, f"Found {len(agent_defs)}, expected 1")

    if agent_defs:
        agent = agent_defs[0]
        check("Agent.Name present", "Name" in agent, "Missing 'Name'")
        check("Agent.Instructions present", "Instructions" in agent, "Missing 'Instructions'")
        check("Agent.ChildSkills present", "ChildSkills" in agent, "Missing 'ChildSkills'")
        check("Agent.Triggers present", "Triggers" in agent, "Missing 'Triggers'")

        # Verify all child skills reference valid skill names
        child_skills = agent.get("ChildSkills", [])
        all_skill_names = []
        for group in manifest.get("SkillGroups", []):
            for skill in group.get("Skills", []):
                all_skill_names.append(skill.get("Name", ""))

        skillset_name = desc.get("Name", "")
        for cs in child_skills:
            # ChildSkills format: SkillsetName.SkillName
            parts = cs.split(".")
            if len(parts) == 2:
                skill_name = parts[1]
                check(
                    f"ChildSkill '{cs}' references valid skill",
                    skill_name in all_skill_names,
                    f"Skill '{skill_name}' not found in SkillGroups"
                )
                check(
                    f"ChildSkill '{cs}' uses correct skillset prefix",
                    parts[0] == skillset_name,
                    f"Expected prefix '{skillset_name}', got '{parts[0]}'"
                )

    # SkillGroups
    skill_groups = manifest.get("SkillGroups", [])
    formats_found = set()
    for group in skill_groups:
        fmt = group.get("Format", "")
        formats_found.add(fmt)
        check(f"SkillGroup format '{fmt}' is valid", fmt in ("GPT", "API", "KQL", "AGENT"), f"Unknown format: {fmt}")

        for skill in group.get("Skills", []):
            check(f"Skill '{skill.get('Name', '?')}' has Name", "Name" in skill, "Missing 'Name'")
            check(f"Skill '{skill.get('Name', '?')}' has Description", "Description" in skill, "Missing 'Description'")

            # Check API skills reference OpenAPI spec files
            if fmt == "API":
                spec_file = skill.get("Settings", {}).get("OpenApiSpecFile", "")
                check(
                    f"API skill '{skill['Name']}' references spec file",
                    bool(spec_file),
                    "Missing Settings.OpenApiSpecFile"
                )

            # Check KQL skills reference template files
            if fmt == "KQL":
                template = skill.get("Settings", {}).get("Template", "")
                check(
                    f"KQL skill '{skill['Name']}' references template",
                    bool(template),
                    "Missing Settings.Template"
                )

    print(f"\n  Skill formats used: {', '.join(sorted(formats_found))}")
    print(f"  Total skills: {sum(len(g.get('Skills', [])) for g in skill_groups)}")


def validate_openapi_specs():
    print("\n=== OpenAPI Specs ===")
    for spec_path in OPENAPI_SPECS:
        print(f"\n  File: {spec_path}")
        if not os.path.exists(spec_path):
            errors.append(f"  FAIL: File not found — {spec_path}")
            continue

        with open(spec_path) as f:
            try:
                spec = yaml.safe_load(f)
            except yaml.YAMLError as e:
                errors.append(f"  FAIL: YAML syntax error — {e}")
                continue

        check("YAML parses successfully", spec is not None, "Empty spec")
        check("openapi version present", "openapi" in spec, "Missing 'openapi' key")
        check("info present", "info" in spec, "Missing 'info' key")
        check("paths present", "paths" in spec, "Missing 'paths' key")
        check("servers present", "servers" in spec, "Missing 'servers' key")

        # Check servers point to Graph API
        servers = spec.get("servers", [])
        if servers:
            url = servers[0].get("url", "")
            check("Server URL is Graph API", "graph.microsoft.com" in url, f"Unexpected server: {url}")

        # Check paths have operations
        paths = spec.get("paths", {})
        for path, methods in paths.items():
            for method, op in methods.items():
                if method in ("get", "post", "put", "patch", "delete"):
                    check(
                        f"{method.upper()} {path} has operationId",
                        "operationId" in op,
                        "Missing operationId"
                    )
                    check(
                        f"{method.upper()} {path} has responses",
                        "responses" in op,
                        "Missing responses"
                    )


def validate_kql():
    print("\n=== KQL Templates ===")
    for kql_path in KQL_FILES:
        print(f"\n  File: {kql_path}")
        if not os.path.exists(kql_path):
            errors.append(f"  FAIL: File not found — {kql_path}")
            continue

        with open(kql_path) as f:
            content = f.read()

        check("File is not empty", len(content.strip()) > 0, "Empty KQL file")
        check("Contains SigninLogs table reference", "SigninLogs" in content, "No reference to SigninLogs")
        check("Contains UserPrincipalName parameter", "{{UserPrincipalName}}" in content, "Missing {{UserPrincipalName}} placeholder")
        check("Contains DestinationIP parameter", "{{DestinationIP}}" in content, "Missing {{DestinationIP}} placeholder")
        check("Contains DestinationLocation parameter", "{{DestinationLocation}}" in content, "Missing {{DestinationLocation}} placeholder")
        check("Uses 30-day lookback", "30d" in content, "No 30d lookback period found")

        # Check for common KQL syntax elements
        check("Uses summarize operator", "summarize" in content, "No 'summarize' operator")
        check("Uses where operator", "where" in content, "No 'where' operator")
        check("Uses extend operator", "extend" in content, "No 'extend' operator")


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

        check("JSON parses successfully", alert is not None, "Empty alert")
        check("Has alertType", "alertType" in alert, "Missing 'alertType'")
        check("Has userPrincipalName", "userPrincipalName" in alert, "Missing 'userPrincipalName'")
        check("Has sourceSignIn", "sourceSignIn" in alert, "Missing 'sourceSignIn'")
        check("Has destinationSignIn", "destinationSignIn" in alert, "Missing 'destinationSignIn'")
        check("Has travelDetails", "travelDetails" in alert, "Missing 'travelDetails'")

        # Validate source sign-in structure
        src = alert.get("sourceSignIn", {})
        check("sourceSignIn has ipAddress", "ipAddress" in src, "Missing sourceSignIn.ipAddress")
        check("sourceSignIn has location", "location" in src, "Missing sourceSignIn.location")

        dst = alert.get("destinationSignIn", {})
        check("destinationSignIn has ipAddress", "ipAddress" in dst, "Missing destinationSignIn.ipAddress")
        check("destinationSignIn has location", "location" in dst, "Missing destinationSignIn.location")


def validate_package_structure():
    print("\n=== Package Structure ===")
    check("AgentManifest.yaml exists", os.path.exists(MANIFEST_PATH), "Missing")
    check("openapispec_1.yaml exists", os.path.exists(OPENAPI_SPECS[0]), "Missing")
    check("openapispec_2.yaml exists", os.path.exists(OPENAPI_SPECS[1]), "Missing")
    check("KQL template exists", os.path.exists(KQL_FILES[0]), "Missing")
    check("package.sh exists", os.path.exists("scripts/package.sh"), "Missing")
    check("package.sh is executable", os.access("scripts/package.sh", os.X_OK), "Not executable")


if __name__ == "__main__":
    os.chdir(os.path.join(os.path.dirname(__file__), ".."))

    print("=" * 60)
    print("  Travel Anomaly Triage Agent — Pre-flight Validation")
    print("=" * 60)

    validate_manifest()
    validate_openapi_specs()
    validate_kql()
    validate_sample_alerts()
    validate_package_structure()

    # Summary
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
        print("  Ready to upload manifest/AgentManifest.yaml to Security Copilot")
        sys.exit(0)
