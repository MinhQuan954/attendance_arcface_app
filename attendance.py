# attendance.py
from pathlib import Path
from datetime import datetime
import csv
from config import REPORTS_DIR

REPORTS_DIR.mkdir(parents=True, exist_ok=True)

def today_csv_path() -> Path:
    return REPORTS_DIR / (datetime.now().strftime("attendance_%Y%m%d.csv"))

def log_event(person: str, status: str):
    path = today_csv_path()
    new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["timestamp", "name", "status"])  # status: IN / OUT
        w.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), person, status])

def daily_stats():
    path = today_csv_path()
    if not path.exists():
        return {"count": 0, "in": 0, "out": 0, "unique": 0}
    seen = set()
    cnt = 0
    ins = outs = 0
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            cnt += 1
            seen.add(row["name"])
            if row["status"].upper() == "IN":
                ins += 1
            elif row["status"].upper() == "OUT":
                outs += 1
    return {"count": cnt, "in": ins, "out": outs, "unique": len(seen)}

def user_attendance_stats():
    """Get attendance statistics by user for today"""
    path = today_csv_path()
    if not path.exists():
        return {}
    
    user_stats = {}
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            name = row["name"]
            status = row["status"].upper()
            
            if name not in user_stats:
                user_stats[name] = {"in": 0, "out": 0, "total": 0}
            
            user_stats[name]["total"] += 1
            if status == "IN":
                user_stats[name]["in"] += 1
            elif status == "OUT":
                user_stats[name]["out"] += 1
    
    return user_stats

def can_attend_today(person: str) -> tuple[bool, str]:
    """
    Check if a person can attend today (no limit, alternating IN/OUT)
    Returns: (can_attend, message)
    """
    # No limit on attendance - allow unlimited alternating IN/OUT
    return True, ""

def get_next_attendance_status(person: str) -> str:
    """
    Get the next attendance status for a person (IN or OUT)
    Returns "IN" if person hasn't attended today, "OUT" if they've done IN
    """
    user_stats = user_attendance_stats()
    if person not in user_stats:
        return "IN"
    
    stats = user_stats[person]
    if stats["in"] == 0:
        return "IN"
    elif stats["in"] > stats["out"]:
        return "OUT"
    else:
        return "IN"  # This shouldn't happen if can_attend_today is checked first

def get_detailed_attendance_data():
    """
    Get detailed attendance data for table display
    Returns list of dicts with: name, date, time_in, time_out
    """
    from datetime import datetime
    import os
    
    data = []
    attendance_dir = REPORTS_DIR
    
    if not attendance_dir.exists():
        return data
    
    # Get all CSV files
    csv_files = list(attendance_dir.glob("*.csv"))
    csv_files.sort()  # Sort by date
    
    for csv_file in csv_files:
        date_str = csv_file.stem  # filename without extension
        try:
            # Parse date from filename (format: attendance_YYYYMMDD)
            if date_str.startswith("attendance_"):
                date_part = date_str[11:]  # Remove "attendance_" prefix
                date_obj = datetime.strptime(date_part, "%Y%m%d").date()
            else:
                # Fallback for other formats
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            with open(csv_file, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                daily_records = list(reader)
            
            # Group by person and show all attendance records
            person_records = {}
            for record in daily_records:
                name = record["name"]
                if name not in person_records:
                    person_records[name] = []
                
                status = record["status"].upper()
                time_str = record["timestamp"]
                
                person_records[name].append({
                    "status": status,
                    "time": time_str
                })
            
            # Add to data - show all attendance records
            for name, records in person_records.items():
                # Sort records by time
                records.sort(key=lambda x: x["time"])
                
                # Group consecutive IN/OUT pairs
                i = 0
                while i < len(records):
                    current_record = records[i]
                    if current_record["status"] == "IN":
                        # Look for corresponding OUT
                        time_in = current_record["time"]
                        time_out = ""
                        
                        # Find next OUT record
                        for j in range(i + 1, len(records)):
                            if records[j]["status"] == "OUT":
                                time_out = records[j]["time"]
                                i = j + 1  # Skip the OUT record
                                break
                        else:
                            i += 1  # No OUT found, just IN
                        
                        data.append({
                            "name": name,
                            "date": date_obj.strftime("%d/%m/%Y"),
                            "time_in": time_in,
                            "time_out": time_out
                        })
                    else:
                        # OUT without corresponding IN (shouldn't happen with new logic)
                        i += 1
                
        except ValueError:
            # Skip invalid date formats
            continue
    
    # Sort by date (newest first), then by name
    data.sort(key=lambda x: (x["date"], x["name"]), reverse=True)
    return data
