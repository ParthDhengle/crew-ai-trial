import os
import json
import warnings


def parse_preferences(prefs_path: str) -> dict:
    """Parse user_profile.json into a dict."""
    if os.path.exists(prefs_path):
        try:
            with open(prefs_path, "r") as f:
                return json.load(f)
        except Exception as e:
            warnings.warn(f"Error parsing preferences: {e}")
    return {}


def collect_preferences(prefs_path: str, get_user_input):
    """Collect missing user preferences interactively, updating the file."""
    print("\n🛠️ Personalizing your experience! Filling in missing preferences.")

    # Define all keys and their choice options (None for free text)
    pref_definitions = {
        "Name": None,  # Free text
        "Role": [
            "Student", "Professional (Engineer/Developer)",
            "Creative/Designer", "Manager/Entrepreneur", "Other"
        ],
        "Location": None,
        "Productive Time": ["Morning", "Afternoon", "Evening", "Late Night"],
        "Reminder Type": [
            "Gentle notification", "Phone call / Voice prompt",
            "Email / Message"
        ],
        "Top Task Type": [
            "Learning / Study", "Coding / Development",
            "Writing / Content Creation", "Management / Planning",
            "Personal Growth / Health"
        ],
        "Missed Task Handling": [
            "Auto-reschedule to next free slot",
            "Ask me before moving",
            "Skip if missed"
        ],
        "Top Motivation": [
            "Checking things off a list",
            "Friendly competition / Leaderboards",
            "Music + Encouragement",
            "Supportive reminders (like a friend)"
        ],
        "AI Tone": [
            "Calm & Professional", "Friendly & Casual",
            "Motivational & Pushy", "Fun & Humorous"
        ],
        "Break Reminder": [
            "Every 25 min (Pomodoro style)",
            "Every 1 hour", "Every 2 hours", "Never remind me"
        ],
        "Mood Check": [
            "Yes, ask me once a day",
            "Only if I look unproductive",
            "No, skip this"
        ],
        "Current Focus": [
            "Finish studies", "Grow career skills",
            "Build side projects", "Explore & learn",
            "Health & balance"
        ]  # Optional
    }

    existing_prefs = parse_preferences(prefs_path)
    updated_prefs = existing_prefs.copy()

    # Fill missing preferences
    for key, options in pref_definitions.items():
        if key not in existing_prefs or not existing_prefs[key]:
            if options:
                print(f"\n{key}?")
                for i, opt in enumerate(options, 1):
                    print(f"{i}. {opt}")
                while True:
                    try:
                        choice = int(get_user_input("Choose a number: "))
                        if 1 <= choice <= len(options):
                            value = options[choice - 1]
                            if value == "Other":
                                value = get_user_input("Please specify: ").strip()
                            updated_prefs[key] = value
                            break
                        else:
                            print("Invalid choice. Try again.")
                    except ValueError:
                        print("Please enter a number.")
            else:
                value = get_user_input(f"{key}? ").strip()
                if value:
                    updated_prefs[key] = value

    # Optional "Current Focus"
    if "Current Focus" not in updated_prefs or not updated_prefs["Current Focus"]:
        set_goals = get_user_input("\nWould you like to set a long-term goal? (yes/no): ").strip().lower()
        if set_goals == "yes":
            options = pref_definitions["Current Focus"]
            print("\nWhat’s your current focus?")
            for i, opt in enumerate(options, 1):
                print(f"{i}. {opt}")
            while True:
                try:
                    choice = int(get_user_input("Choose a number: "))
                    if 1 <= choice <= len(options):
                        updated_prefs["Current Focus"] = options[choice - 1]
                        break
                    else:
                        print("Invalid choice. Try again.")
                except ValueError:
                    print("Please enter a number.")

    # Write back only if changes
    if updated_prefs != existing_prefs:
        try:
            os.makedirs(os.path.dirname(prefs_path), exist_ok=True)
            with open(prefs_path, "w") as f:
                json.dump(updated_prefs, f, indent=4)
            print("\n✅ Preferences updated! You can change them anytime by telling me new info.")
        except Exception as e:
            warnings.warn(f"Error saving preferences: {e}")
    else:
        print("\n✅ All preferences already set. No changes needed.")
