import os
from datetime import datetime

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'generated_files')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def generate_timeslots(start_time, end_time, slot_duration):
    current_time = start_time
    slots = []
    while current_time < end_time:
        slot_start = current_time
        slot_end = current_time + slot_duration
        slots.append((slot_start, slot_end))
        current_time = slot_end
    return slots

import os

def create_ical(timeslots, filename="timeslots.ics"):
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'generated_files')  # Map voor gegenereerde bestanden
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Zorg dat de map bestaat
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    try:
        with open(filepath, "w") as file:
            file.write("BEGIN:VCALENDAR\nVERSION:2.0\n")
            for i, (start, end) in enumerate(timeslots):
                file.write("BEGIN:VEVENT\n")
                file.write(f"UID:{i}@example.com\n")
                file.write(f"DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%SZ')}\n")
                file.write(f"DTSTART:{start.strftime('%Y%m%dT%H%M%SZ')}\n")
                file.write(f"DTEND:{end.strftime('%Y%m%dT%H%M%SZ')}\n")
                file.write(f"SUMMARY:Time Slot {i + 1}\n")
                file.write(f"DESCRIPTION:Time slot from {start} to {end}\n")
                file.write("END:VEVENT\n")
            file.write("END:VCALENDAR\n")
    except Exception as e:
        print(f"Error creating iCalendar file: {e}")
        return None

    if os.path.exists(filepath):
        return filepath
    else:
        return None


