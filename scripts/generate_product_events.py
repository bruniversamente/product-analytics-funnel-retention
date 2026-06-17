"""Generate synthetic product analytics data."""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "generated"
OUT.mkdir(parents=True, exist_ok=True)

CHANNELS = ["Organic", "Paid Search", "Social", "Referral"]
PLATFORMS = ["iOS", "Android", "Web"]
PERSONAS = ["Host", "Guest"]
REGIONS = ["South", "Southeast", "Northeast"]
CATEGORIES = ["Sports", "Music", "Games", "Education", "Wellness"]
FUNNEL = ["app_open", "signup_completed", "profile_completed", "search_performed", "opportunity_viewed", "invitation_sent", "booking_confirmed"]
STEP_PROB = [1.00, 0.92, 0.72, 0.58, 0.46, 0.29, 0.16]


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    users = []
    events = []
    actions = []
    start = datetime(2026, 1, 1)
    event_id = 1
    opportunity_id = 1

    for idx in range(1, 501):
        signup = start + timedelta(days=random.randint(0, 120))
        user = {
            "user_id": f"U{idx:05d}",
            "signup_date": signup.date().isoformat(),
            "persona": random.choice(PERSONAS),
            "region": random.choice(REGIONS),
            "acquisition_channel": random.choice(CHANNELS),
            "platform": random.choice(PLATFORMS),
        }
        users.append(user)

        current_time = signup + timedelta(hours=random.randint(7, 22), minutes=random.randint(0, 59))
        session_id = f"S{event_id:06d}"
        opportunity = ""
        category = ""
        invitation_time = ""
        confirmation_time = ""

        for step, probability in zip(FUNNEL, STEP_PROB):
            if random.random() > probability:
                break
            if step in ["search_performed", "opportunity_viewed", "invitation_sent", "booking_confirmed"] and not opportunity:
                opportunity = f"OP{opportunity_id:06d}"
                category = random.choice(CATEGORIES)
                opportunity_id += 1
            if step == "invitation_sent":
                invitation_time = current_time
            if step == "booking_confirmed":
                current_time = current_time + timedelta(hours=random.randint(1, 72))
                confirmation_time = current_time
            events.append({
                "event_id": f"E{event_id:07d}",
                "user_id": user["user_id"],
                "event_timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                "event_name": step,
                "session_id": session_id,
                "platform": user["platform"],
                "acquisition_channel": user["acquisition_channel"],
                "opportunity_id": opportunity,
                "category": category,
            })
            event_id += 1
            current_time = current_time + timedelta(minutes=random.randint(1, 8))

        if opportunity:
            status = "Search Only"
            if invitation_time and not confirmation_time:
                status = "Pending"
            if confirmation_time:
                status = "Confirmed"
            actions.append({
                "opportunity_id": opportunity,
                "category": category,
                "created_at": signup.strftime("%Y-%m-%d %H:%M:%S"),
                "host_user_id": user["user_id"] if user["persona"] == "Host" else "",
                "guest_user_id": user["user_id"] if user["persona"] == "Guest" else "",
                "invitation_sent_at": invitation_time.strftime("%Y-%m-%d %H:%M:%S") if invitation_time else "",
                "booking_confirmed_at": confirmation_time.strftime("%Y-%m-%d %H:%M:%S") if confirmation_time else "",
                "status": status,
            })

        for day_offset, probability in [(1, 0.42), (7, 0.28), (30, 0.16)]:
            if random.random() < probability:
                repeat_time = signup + timedelta(days=day_offset, hours=random.randint(0, 3))
                events.append({
                    "event_id": f"E{event_id:07d}",
                    "user_id": user["user_id"],
                    "event_timestamp": repeat_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "event_name": "app_open",
                    "session_id": f"S{event_id:06d}",
                    "platform": user["platform"],
                    "acquisition_channel": user["acquisition_channel"],
                    "opportunity_id": "",
                    "category": "",
                })
                event_id += 1

    write_csv(OUT / "users.csv", users)
    write_csv(OUT / "events.csv", events)
    write_csv(OUT / "marketplace_actions.csv", actions)
    print(f"Users: {len(users)} | Events: {len(events)} | Opportunities: {len(actions)}")


if __name__ == "__main__":
    main()
