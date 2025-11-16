import json
import xml.etree.ElementTree as ET
import os
from datetime import datetime, timedelta, timezone
import argparse
from typing import Dict, List, Any

MINSK_TIMEZONE: timezone = timezone(timedelta(hours=3))

# Maps the verdict from the XML file to the standard CLICS judgement_type_id
VERDICT_MAP: Dict[str, str] = {
    'OK': 'AC',   'WA': 'WA',   'PE': 'PE',
    'TL': 'TLE',  'ML': 'MLE',  'RT': 'RTE',
}

# Standard CLICS judgement types that provide scoring rules
STANDARD_JUDGEMENT_TYPES: List[Dict[str, Any]] = [
    {"id": "AC", "name": "Accepted", "penalty": False, "solved": True},
    {"id": "WA", "name": "Wrong Answer", "penalty": True, "solved": False},
    {"id": "TLE", "name": "Time Limit Exceeded", "penalty": True, "solved": False},
    {"id": "RTE", "name": "Run-Time Error", "penalty": True, "solved": False},
    {"id": "MLE", "name": "Memory Limit Exceeded", "penalty": True, "solved": False},
    {"id": "PE", "name": "Presentation Error", "penalty": True, "solved": False},
    {"id": "CE", "name": "Compiler Error", "penalty": False, "solved": False},
]

# --- Helper Functions ---
def format_hms_sss(delta: timedelta) -> str:
    """Formats a timedelta to H:MM:SS.sss for event feed durations.

    Args:
        delta: A timedelta object representing the duration.

    Returns:
        A string in H:MM:SS.sss format.
    """
    total_seconds = delta.total_seconds()
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours)}:{int(minutes):02d}:{seconds:06.3f}"

def write_event(file_handle: Any, event_type: str, data: Dict[str, Any]) -> None:
    """Writes a single, correctly-formatted event to the ndjson file.

    Args:
        file_handle: The file handle to write to.
        event_type: The type of event (e.g., 'contests').
        data: The data dictionary for the event.
    """
    token = f"{event_type}-{data['id']}-{datetime.now().isoformat()}"
    event = {"type": event_type, "op": "create", "data": data, "token": token}
    file_handle.write(json.dumps(event, ensure_ascii=False) + '\n')

def write_update_event(file_handle: Any, event_type: str, data: Dict[str, Any]) -> None:
    """Writes an update event to the ndjson file.

    Args:
        file_handle: The file handle to write to.
        event_type: The type of event (e.g., 'state').
        data: The data dictionary for the event.
    """
    token = f"{event_type}-{data['id']}-update-{datetime.now().isoformat()}"
    event = {"type": event_type, "op": "update", "data": data, "token": token}
    file_handle.write(json.dumps(event, ensure_ascii=False) + '\n')

# --- Main Script ---
def create_icpc_package(xml_file_path: str, output_dir: str) -> None:
    """Creates an ICPC contest package from an XML file.

    Args:
        xml_file_path: Path to the input XML file.
        output_dir: Path to the output directory.
    """
    os.makedirs(output_dir, exist_ok=True)
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
    except (FileNotFoundError, ET.ParseError) as e:
        print(f"Error: Could not process '{xml_file_path}': {e}")
        return

    contest_info = root
    start_time_dt = datetime.strptime(
        contest_info.get('start_time'), '%Y/%m/%d %H:%M:%S'
    ).replace(tzinfo=MINSK_TIMEZONE)
    duration_delta = timedelta(seconds=int(contest_info.get("duration")))
    freeze_delta = timedelta(seconds=int(contest_info.get("fog_time")))

    # Generate the event-feed.ndjson with a complete state
    with open(os.path.join(output_dir, 'event-feed.ndjson'), 'w', encoding='utf-8') as f:
        print("Writing complete contest definition to event feed...")
        
        # CORRECTED: Create a single, comprehensive contest event with all parameters
        contest_data = {
            "id": contest_info.get('contest_id'),
            "name": contest_info.find('name').text,
            "start_time": start_time_dt.isoformat(),
            "duration": format_hms_sss(duration_delta),
            "scoreboard_freeze_duration": format_hms_sss(freeze_delta),
            "penalty_time": 20
        }
        write_event(f, "contests", contest_data)
        
        # Write all other metadata events
        for jt in STANDARD_JUDGEMENT_TYPES:
            write_event(f, "judgement-types", jt)
            
        for lang in root.find('languages').findall('language'):
            write_event(f, "languages", {"id": lang.get("id"), "name": lang.get("long_name")})

        organizations, groups = {}, {}
        for user in root.find('users').findall('user'):
            team_name = user.get('name')
            org_name = team_name.split(':')[0].strip()
            if org_name not in organizations:
                organizations[org_name] = {'id': org_name, 'name': org_name}
                write_event(f, "organizations", organizations[org_name])
            
            group_id = "Guest" if "Guest team" in team_name else org_name
            if group_id not in groups:
                groups[group_id] = {'id': group_id, 'name': group_id}
                write_event(f, "groups", groups[group_id])
            
            write_event(f, "teams", {
                "id": user.get("id"),
                "name": team_name,
                "organization_id": org_name,
                "group_ids": [group_id]
            })

        for prob in root.find('problems').findall('problem'):
            write_event(f, "problems", {
                "id": prob.get("id"),
                "label": prob.get("short_name"),
                "name": prob.get("long_name")
            })
        
        print("Writing submissions and judgements...")
        for run in root.find('runs').findall('run'):
            run_id = run.get('run_id')
            time_from_start = timedelta(seconds=int(run.get('time')))
            absolute_time = start_time_dt + time_from_start
            
            write_event(f, "submissions", {
                "id": run_id, "team_id": run.get('user_id'), "problem_id": run.get('prob_id'),
                "language_id": run.get('lang_id'), "time": absolute_time.isoformat(),
                "contest_time": format_hms_sss(time_from_start),
            })

            write_event(f, "judgements", {
                "id": run_id,
                "submission_id": run_id,
                "judgement_type_id": VERDICT_MAP.get(run.get('status'), 'CE'),
                "start_time": absolute_time.isoformat(),
                "start_contest_time": format_hms_sss(time_from_start),
                "end_time": absolute_time.isoformat(),
                "end_contest_time": format_hms_sss(time_from_start),
            })
            
        # Final State Event
        print("Writing final contest state...")
        end_time_iso = (start_time_dt + duration_delta).isoformat()
        write_update_event(f, "state", {
            "id": contest_info.get('contest_id'),
            "ended": end_time_iso,
            "finalized": end_time_iso,
        })

    print(f"\nSuccessfully created compliant ICPC Contest Package in '{output_dir}'.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert ejudge XML to ICPC package')
    parser.add_argument('input_file', help='Path to the input XML file')
    parser.add_argument('output_dir', help='Path to the output directory')
    args = parser.parse_args()
    create_icpc_package(args.input_file, args.output_dir)
