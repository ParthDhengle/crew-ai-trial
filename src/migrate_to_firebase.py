import os
import json
from datetime import datetime
from common_functions.Find_project_root import find_project_root
from firebase_client import set_user_profile, add_kb_entry, add_task, add_project, add_summary, add_document

PROJECT_ROOT = find_project_root()

def safe_load_json(path, default=None):
    """Safely load JSON file, return default if empty or invalid."""
    default = default or []
    try:
        if os.path.exists(path) and os.path.getsize(path) > 0:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
        print(f"Warning: {path} is empty or does not exist. Skipping.")
        return default
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {path}: {e}. Skipping.")
        return default
    except Exception as e:
        print(f"Error loading {path}: {e}. Skipping.")
        return default

# Migrate user_profile.json
profile_path = os.path.join(PROJECT_ROOT, "knowledge", "user_profile.json")
if os.path.exists(profile_path):
    with open(profile_path, "r", encoding="utf-8") as f:
        profile = safe_load_json(profile_path, {})
    if profile:
        set_user_profile(
            name=profile.get("Name", ""),
            email=profile.get("email", ""),
            timezone="Asia/Kolkata" if profile.get("Location") == "India" else "UTC",
            focus_hours=[profile.get("Productive Time", "")] if profile.get("Productive Time") else [],
            integrations={"email": profile.get("email")} if profile.get("email") else {}
        )
        print("✅ Migrated user profile to Firestore.")
    else:
        print("Warning: No valid profile data to migrate.")

# Migrate extracted_facts.json
facts_path = os.path.join(PROJECT_ROOT, "knowledge", "memory", "long_term", "extracted_facts.json")
if os.path.exists(facts_path):
    facts = safe_load_json(facts_path, [])
    for fact in facts:
        add_kb_entry(
            title="Extracted Fact",
            content_md=fact.get("fact", ""),
            tags=["fact"],
            references=[fact.get("source", "")] if fact.get("source") else []
        )
    print("✅ Migrated facts to knowledge_base.")

# Migrate projects_and_tasks.json
pt_path = os.path.join(PROJECT_ROOT, "knowledge", "memory", "long_term", "projects_and_tasks.json")
if os.path.exists(pt_path):
    pt = safe_load_json(pt_path, {})
    for proj in pt.get("projects", []):
        add_project(
            name=proj.get("name", ""),
            description=proj.get("goal", ""),
            members=[proj.get("owner", "")]
        )
    for task in pt.get("tasks", []):
        add_task(
            title=task.get("title", ""),
            description=task.get("description", ""),
            due_date=task.get("due", "")
        )
    print("✅ Migrated projects and tasks to Firestore.")

# Migrate mood_logs.json
moods_path = os.path.join(PROJECT_ROOT, "knowledge", "memory", "narrative", "mood_logs.json")
if os.path.exists(moods_path):
    moods = safe_load_json(moods_path, [])
    for mood in moods:
        add_document(
            "mood_logs",
            {"mood": mood.get("mood", ""), "date": mood.get("date", datetime.now().isoformat())}
        )
    print("✅ Migrated mood logs to mood_logs.")

# Migrate summaries.json
summaries_path = os.path.join(PROJECT_ROOT, "knowledge", "memory", "narrative", "summaries.json")
if os.path.exists(summaries_path):
    summaries = safe_load_json(summaries_path, [])
    for summary in summaries:
        add_summary(
            date_=summary.get("date", datetime.now().isoformat()),
            summary_text=summary.get("summary", ""),
            metrics=summary.get("metrics", {})
        )
    print("✅ Migrated summaries to summaries.")

print("Migration complete! Remove old files manually: Remove-Item -Path .\\knowledge\\user_profile.json .\\knowledge\\memory\\long_term\\* .\\knowledge\\memory\\narrative\\* .\\knowledge\\memory\\cache\\* -Recurse")