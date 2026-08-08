"""
MBC2 Motor Tracking Database Manager
Handles all DB operations for motor registry, sessions, and benchmarks.
"""

import sqlite3
import os
import json
from datetime import datetime
from pathlib import Path


DB_PATH     = Path(__file__).resolve().parent / "mbc2.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_connection() -> sqlite3.Connection:
    """Get a DB connection with row factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _add_column_if_missing(conn, table: str, column: str, decl: str):
    """
    Add a column to an existing table if it isn't there yet.
    This is the required migration path for new columns — never use a
    raw ALTER TABLE ADD COLUMN without this guard (see CLAUDE.md).
    """
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


def _seed_motor_models(conn):
    """Insert canonical motor models if not already present. Safe to run on existing DBs."""
    models = [
        ('Stock (Mabuchi)',   'STK-M', 'Single', 1.0, 1.0, 'Box Stock',                         'Mabuchi variant. High speed bias.'),
        ('Stock (SMC)',       'STK-S', 'Single', 1.0, 1.0, 'Box Stock',                         'SMC variant. High torque bias.'),
        ('Rev-Tuned 2',       'RT2',   'Single', 2.5, 1.0, 'Basic, Tuned, BMax, Advanced, Open', None),
        ('Atomic-Tuned 2',   'AT2',   'Single', 1.5, 1.5, 'Basic, Tuned, BMax, Advanced, Open', None),
        ('Torque-Tuned 2',   'TT2',   'Single', 1.0, 2.5, 'Basic, Tuned, BMax, Advanced, Open', None),
        ('Light-Dash',        'LD',    'Single', 2.5, 2.5, 'Basic, BMax, Advanced, Open',        None),
        ('Hyper-Dash 3',      'HD3',   'Single', 3.0, 3.0, 'BMax, Advanced, Open',               None),
        ('Power-Dash',        'PD',    'Single', 3.0, 3.5, 'BMax, Advanced, Open',               None),
        ('Sprint-Dash',       'SD',    'Single', 4.0, 2.5, 'BMax, Advanced, Open',               None),
        ('Ultra-Dash',        'UD',    'Single', 4.0, 3.5, 'Open',                               None),
        ('Plasma-Dash',       'PLD',   'Single', 4.0, 4.0, 'None',                               'Exhibition/display only. Not competition legal.'),
        ('Stock Dual Shaft',  'STK-D', 'Dual',   1.0, 1.0, 'Box Stock',                         'Included with MA chassis kits.'),
        ('Rev-Tuned 2 PRO',   'RT2-P', 'Dual',   2.5, 1.0, 'Basic, Tuned, BMax, Advanced, Open', 'PRO dual shaft variant.'),
        ('Atomic-Tuned 2 PRO','AT2-P', 'Dual',   1.5, 1.5, 'Basic, Tuned, BMax, Advanced, Open', 'PRO dual shaft variant.'),
        ('Torque-Tuned 2 PRO','TT2-P', 'Dual',   1.0, 2.5, 'Basic, Tuned, BMax, Advanced, Open', 'PRO dual shaft variant.'),
        ('Light-Dash PRO',    'LD-P',  'Dual',   2.5, 2.5, 'Basic, BMax, Advanced, Open',        'PRO dual shaft variant.'),
        ('Hyper-Dash PRO',    'HD3-P', 'Dual',   3.0, 3.0, 'BMax, Advanced, Open',               'PRO dual shaft variant.'),
        ('Mach-Dash PRO',     'MD-P',  'Dual',   3.0, 3.0, 'BMax, Advanced, Open',               'PRO dual shaft variant.'),
        ('Kit Standard',      'KS',    'Single', 1.0, 1.0, 'Box Stock',                         'Single-shaft motor bundled with kit.'),
        ('Kit Standard PRO',  'KS-P',  'Dual',   1.0, 1.0, 'Box Stock',                         'Dual-shaft motor bundled with MA/MS chassis kits.'),
    ]
    conn.executemany("""
        INSERT OR IGNORE INTO motor_models (name, code, shaft_type, speed_stars, torque_stars, legal_classes, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, models)


def init_db():
    """Initialise the database from schema if it doesn't exist, then seed canonical data."""
    if not DB_PATH.exists():
        print(f"Creating new database at {DB_PATH}")
        with get_connection() as conn:
            with open(SCHEMA_PATH, 'r') as f:
                conn.executescript(f.read())
        print("Database initialised successfully.")
    else:
        print(f"Database already exists at {DB_PATH}")

    with get_connection() as conn:
        _seed_motor_models(conn)
        print("Motor models seeded.")


# ============================================================
# MOTOR REGISTRY
# ============================================================

def get_next_motor_identifier(model_code: str, direction: str) -> str:
    """
    Generate the next identifier for a motor e.g. SD-R-01, SD-R-02
    Sequence resets per model code.
    """
    with get_connection() as conn:
        prefix = f"{model_code}-{direction}-"
        rows = conn.execute(
            "SELECT identifier FROM motors WHERE identifier LIKE ?",
            (f"{prefix}%",)
        ).fetchall()

        # Compare suffixes numerically — a string sort puts 100 before 99
        max_num = 0
        for r in rows:
            try:
                max_num = max(max_num, int(r['identifier'].rsplit('-', 1)[-1]))
            except ValueError:
                continue
        return f"{prefix}{str(max_num + 1).zfill(2)}"


def register_motor(model_code: str, direction: str, chassis_ids: list = None, notes: str = None) -> dict:
    """
    Register a new motor. Returns the created motor record.
    
    Args:
        model_code: e.g. 'SD' for Sprint Dash
        direction: 'F' or 'R'
        chassis_ids: list of chassis_id ints this motor is intended for
        notes: optional notes
    """
    with get_connection() as conn:
        # Look up model
        model = conn.execute(
            "SELECT * FROM motor_models WHERE code = ?", (model_code,)
        ).fetchone()
        
        if not model:
            raise ValueError(f"Unknown motor model code: {model_code}")
        
        # Generate identifier
        identifier = get_next_motor_identifier(model_code, direction)
        
        # Insert motor
        cursor = conn.execute("""
            INSERT INTO motors (identifier, model_id, breakin_direction, notes)
            VALUES (?, ?, ?, ?)
        """, (identifier, model['model_id'], direction, notes))
        
        motor_id = cursor.lastrowid
        
        # Assign chassis if provided
        if chassis_ids:
            for chassis_id in chassis_ids:
                conn.execute("""
                    INSERT OR IGNORE INTO motor_chassis_assignments (motor_id, chassis_id)
                    VALUES (?, ?)
                """, (motor_id, chassis_id))
        
        conn.commit()
        return get_motor(motor_id)


def get_motor(motor_id: int) -> dict:
    """Get a motor record with full detail."""
    with get_connection() as conn:
        motor = conn.execute("""
            SELECT v.*, 
                   GROUP_CONCAT(c.name, ', ') as chassis_names
            FROM v_motor_summary v
            LEFT JOIN motor_chassis_assignments mca ON v.motor_id = mca.motor_id
            LEFT JOIN chassis c ON mca.chassis_id = c.chassis_id
            WHERE v.motor_id = ?
            GROUP BY v.motor_id
        """, (motor_id,)).fetchone()
        
        return dict(motor) if motor else None


def get_motor_by_identifier(identifier: str) -> dict:
    """Get a motor by its label identifier e.g. 'SD-R-01'."""
    with get_connection() as conn:
        motor = conn.execute(
            "SELECT motor_id FROM motors WHERE identifier = ?", (identifier,)
        ).fetchone()
        if motor:
            return get_motor(motor['motor_id'])
        return None


def list_motors(status: str = 'Active') -> list:
    """List all motors, optionally filtered by status."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT v.*,
                   GROUP_CONCAT(c.name, ', ') as chassis_names
            FROM v_motor_summary v
            LEFT JOIN motor_chassis_assignments mca ON v.motor_id = mca.motor_id
            LEFT JOIN chassis c ON mca.chassis_id = c.chassis_id
            WHERE (? IS NULL OR v.status = ?)
            GROUP BY v.motor_id
            ORDER BY v.model_code, v.identifier
        """, (status, status)).fetchall()
        return [dict(r) for r in rows]


def update_motor_status(motor_id: int, status: str):
    """Update motor status: Active, Retired, Lost, Damaged."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE motors SET status = ? WHERE motor_id = ?",
            (status, motor_id)
        )
        conn.commit()


# ============================================================
# SESSIONS
# ============================================================

def create_session(motor_id: int, session_type: str, notes: str = None, ambient_temp_c: float = None) -> int:
    """Create a new session record. Returns session_id."""
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO sessions (motor_id, session_type, notes, ambient_temp_c)
            VALUES (?, ?, ?, ?)
        """, (motor_id, session_type, notes, ambient_temp_c))
        conn.commit()
        return cursor.lastrowid


def session_exists(session_id: int) -> bool:
    """Check whether a session record exists."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        return row is not None


def update_session_notes(session_id: int, notes: str):
    """Set the notes/name on an existing session."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE sessions SET notes = ? WHERE session_id = ?",
            (notes, session_id)
        )
        conn.commit()


def log_session_data(session_id: int, rows: list):
    """
    Bulk insert parsed MBC2 data rows into session_data.
    
    Each row dict should contain parsed MBC2 CSV fields.
    The session_id binding is filled in here — rows don't need to carry it.
    """
    rows = [{**r, 'session_id': session_id} for r in rows]
    with get_connection() as conn:
        conn.executemany("""
            INSERT INTO session_data 
            (session_id, timestamp_ms, raw_line, mode, program_step,
             voltage_mv, current_ma, rpm, temp_c, elapsed_sec, rpm_cap, kv_efficiency)
            VALUES 
            (:session_id, :timestamp_ms, :raw_line, :mode, :program_step,
             :voltage_mv, :current_ma, :rpm, :temp_c, :elapsed_sec, :rpm_cap, :kv_efficiency)
        """, rows)
        conn.commit()


def get_session_data(session_id: int) -> list:
    """Get all data rows for a session."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM session_data WHERE session_id = ? ORDER BY timestamp_ms",
            (session_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_sessions() -> list:
    """Get all sessions with motor info and summary stats for the UI."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                s.session_id,
                s.session_type,
                s.session_date,
                s.notes,
                m.identifier    AS motor_identifier,
                mm.name         AS motor_model,
                mm.code         AS motor_code,
                b.peak_rpm,
                b.avg_rpm,
                b.peak_temp_c,
                b.benchmark_type,
                COUNT(sd.data_id) AS row_count
            FROM sessions s
            JOIN motors m ON s.motor_id = m.motor_id
            JOIN motor_models mm ON m.model_id = mm.model_id
            LEFT JOIN benchmarks b ON b.session_id = s.session_id
            LEFT JOIN session_data sd ON sd.session_id = s.session_id
            GROUP BY s.session_id
            ORDER BY s.session_date DESC
        """).fetchall()
        return [dict(r) for r in rows]


def delete_session(session_id: int):
    """Delete a session and all its associated data rows."""
    with get_connection() as conn:
        conn.execute("DELETE FROM session_data WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM benchmarks WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM motor_breakin_log WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        conn.commit()


def export_session_csv(session_id: int):
    """
    Generate a CSV string from session_data rows on demand.
    Returns None if the session does not exist.
    This is the only CSV output path — no files are stored on disk.
    """
    with get_connection() as conn:
        sess = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if not sess:
            return None
        rows = conn.execute(
            "SELECT * FROM session_data WHERE session_id = ? ORDER BY timestamp_ms",
            (session_id,)
        ).fetchall()

    import io
    import csv as csv_mod
    buf = io.StringIO()
    fields = ['timestamp_ms', 'mode', 'program_step', 'voltage_mv',
              'current_ma', 'rpm', 'temp_c', 'elapsed_sec', 'rpm_cap',
              'kv_efficiency', 'raw_line']
    writer = csv_mod.DictWriter(buf, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    for r in rows:
        writer.writerow(dict(r))
    return buf.getvalue()


# ============================================================
# BENCHMARKS
# ============================================================

def get_motor_benchmarks(motor_id: int) -> list:
    """Get all benchmarks for a motor in chronological order."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM v_benchmark_comparison
            WHERE identifier = (SELECT identifier FROM motors WHERE motor_id = ?)
            ORDER BY session_date
        """, (motor_id,)).fetchall()
        return [dict(r) for r in rows]


# ============================================================
# LOOKUP HELPERS
# ============================================================

def get_all_motor_models() -> list:
    """Get all motor models for UI dropdowns."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM motor_models ORDER BY speed_stars, torque_stars"
        ).fetchall()
        return [dict(r) for r in rows]


def get_chassis_for_shaft_type(shaft_type: str) -> list:
    """Get chassis compatible with a given shaft type (Single/Dual)."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT c.*, mt.name as mount_type, mt.default_direction
            FROM chassis c
            JOIN mount_types mt ON c.mount_type_id = mt.mount_type_id
            WHERE mt.shaft_type = ?
            ORDER BY mt.name, c.name
        """, (shaft_type,)).fetchall()
        return [dict(r) for r in rows]


def get_motor_benchmark_trend(motor_id: int) -> dict:
    """
    Get benchmark trend for a motor — RPM improvement over time.
    Returns improvement status: improving / plateaued / declining.
    """
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT b.peak_rpm, b.avg_rpm, b.peak_current_ma, b.avg_current_ma,
                   b.voltage_v, b.final_temp_c, s.session_date
            FROM benchmarks b
            JOIN sessions s ON b.session_id = s.session_id
            WHERE b.motor_id = ?
            ORDER BY s.session_date ASC
        """, (motor_id,)).fetchall()

        benchmarks = [dict(r) for r in rows]
        if len(benchmarks) < 2:
            return {'status': 'insufficient_data', 'benchmarks': benchmarks}

        # Calculate RPM per watt (efficiency) for each benchmark
        for b in benchmarks:
            if b.get('avg_current_ma') and b.get('voltage_v') and b['avg_current_ma'] > 0:
                watts = (b['voltage_v'] * b['avg_current_ma']) / 1000
                b['rpm_per_watt'] = round((b['avg_rpm'] or 0) / watts, 1) if watts > 0 else None
            else:
                b['rpm_per_watt'] = None

        # Compare last two benchmarks
        last = benchmarks[-1]
        prev = benchmarks[-2]
        delta_rpm = (last.get('peak_rpm') or 0) - (prev.get('peak_rpm') or 0)
        pct_change = (delta_rpm / prev['peak_rpm'] * 100) if prev.get('peak_rpm') else 0

        if pct_change > 2:
            status = 'improving'
        elif pct_change < -2:
            status = 'declining'
        else:
            status = 'plateaued'

        return {
            'status': status,
            'delta_rpm': delta_rpm,
            'pct_change': round(pct_change, 1),
            'benchmarks': benchmarks,
            'latest_peak_rpm': last.get('peak_rpm'),
            'latest_rpm_per_watt': last.get('rpm_per_watt'),
        }


def calculate_efficiency_score(motor_id: int) -> dict:
    """
    Calculate motor efficiency score from best benchmark.
    Score = RPM per watt at benchmark voltage.
    Rating: A (top 25%), B (good), C (average), D (retire consideration).
    Thresholds based on Sprint/Power Dash at 3V:
      A: > 13,000 RPM/W  (e.g. 34500 RPM at 0.80A * 3V = 2.4W = 14375)
      B: 11,000-13,000
      C: 9,000-11,000
      D: < 9,000
    """
    with get_connection() as conn:
        best = conn.execute("""
            SELECT b.peak_rpm, b.avg_rpm, b.avg_current_ma, b.voltage_v, s.session_date
            FROM benchmarks b
            JOIN sessions s ON b.session_id = s.session_id
            WHERE b.motor_id = ?
            ORDER BY b.peak_rpm DESC NULLS LAST
            LIMIT 1
        """, (motor_id,)).fetchone()

        if not best:
            return {'score': None, 'rating': 'N/A', 'rpm_per_watt': None}

        best = dict(best)
        rpm_per_watt = None
        if best.get('avg_current_ma') and best.get('voltage_v') and best['avg_current_ma'] > 0:
            watts = (best['voltage_v'] * best['avg_current_ma']) / 1000
            rpm_per_watt = round((best['avg_rpm'] or 0) / watts, 1) if watts > 0 else None

        if rpm_per_watt is None:
            rating = 'N/A'
        elif rpm_per_watt >= 13000:
            rating = 'A'
        elif rpm_per_watt >= 11000:
            rating = 'B'
        elif rpm_per_watt >= 9000:
            rating = 'C'
        else:
            rating = 'D'

        return {
            'score': rpm_per_watt,
            'rating': rating,
            'peak_rpm': best.get('peak_rpm'),
            'avg_rpm': best.get('avg_rpm'),
            'avg_current_ma': best.get('avg_current_ma'),
            'voltage_v': best.get('voltage_v'),
            'session_date': best.get('session_date'),
        }


def get_motor_roster() -> list:
    """
    Get full motor roster with efficiency scores and trend for the comparison view.
    """
    with get_connection() as conn:
        motors = conn.execute("""
            SELECT v.*,
                   GROUP_CONCAT(c.name, ', ') as chassis_names
            FROM v_motor_summary v
            LEFT JOIN motor_chassis_assignments mca ON v.motor_id = mca.motor_id
            LEFT JOIN chassis c ON mca.chassis_id = c.chassis_id
            GROUP BY v.motor_id
            ORDER BY v.status, v.model_code, v.identifier
        """).fetchall()

        result = []
        for m in motors:
            m = dict(m)
            # Add efficiency score
            eff = calculate_efficiency_score(m['motor_id'])
            m['efficiency_score'] = eff.get('score')
            m['rating'] = eff.get('rating', 'N/A')
            m['best_peak_rpm'] = eff.get('peak_rpm') or m.get('best_peak_rpm')
            # Add trend
            trend = get_motor_benchmark_trend(m['motor_id'])
            m['trend'] = trend.get('status', 'insufficient_data')
            m['trend_delta_rpm'] = trend.get('delta_rpm', 0)
            m['total_benchmarks'] = m.get('total_benchmarks', 0)
            result.append(m)
        return result


def record_benchmark_from_session(session_id: int, motor_id: int,
                                   benchmark_type: str, direction: str,
                                   peak_rpm: int, avg_rpm: int,
                                   peak_current_ma: int, avg_current_ma: int,
                                   peak_temp_c: float, final_temp_c: float,
                                   duration_sec: int = 120,
                                   voltage_v: float = 3.0,
                                   notes: str = None) -> int:
    """Store a benchmark with pre-computed summary values."""
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO benchmarks
            (session_id, motor_id, benchmark_type, voltage_v, direction,
             duration_sec, peak_rpm, avg_rpm, peak_current_ma, avg_current_ma,
             peak_temp_c, final_temp_c, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_id, motor_id, benchmark_type, voltage_v, direction,
              duration_sec, peak_rpm, avg_rpm, peak_current_ma, avg_current_ma,
              peak_temp_c, final_temp_c, notes))
        conn.commit()
        return cursor.lastrowid


# ============================================================
# PROGRAM LIBRARY
# ============================================================

def import_programs_from_json(json_path: str) -> int:
    """
    Import profiles/programs/steps from the existing programs.json file.
    Returns number of profiles imported.
    Skips profiles that already exist by name.
    """
    with open(json_path, 'r') as f:
        data = json.load(f)

    imported = 0
    with get_connection() as conn:
        for profile in data.get('profiles', []):
            # Skip if already exists
            existing = conn.execute(
                "SELECT profile_id FROM profiles WHERE name = ?", (profile['name'],)
            ).fetchone()
            if existing:
                print(f"  Skipping existing profile: {profile['name']}")
                continue

            cursor = conn.execute("""
                INSERT INTO profiles (name, motor_model, chassis, class, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (
                profile.get('name'),
                profile.get('motor'),
                profile.get('chassis'),
                profile.get('class'),
                profile.get('notes')
            ))
            profile_id = cursor.lastrowid

            for step_order, prog in enumerate(profile.get('programs', [])):
                pcursor = conn.execute("""
                    INSERT INTO programs (profile_id, name, mbc2_label, step_order, cycles, target_rpm, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    profile_id,
                    prog.get('name'),
                    prog.get('mbc2Label'),
                    step_order,
                    prog.get('cycles', 1),
                    prog.get('targetRpm'),
                    prog.get('notes')
                ))
                program_id = pcursor.lastrowid

                for s_order, step in enumerate(prog.get('steps', [])):
                    # Parse time string "MM:SS" → seconds
                    def parse_time(t):
                        if not t or t == 'Full Cool':
                            return None
                        parts = str(t).split(':')
                        return int(parts[0]) * 60 + int(parts[1]) if len(parts) == 2 else int(t)

                    conn.execute("""
                        INSERT INTO program_steps (program_id, step_order, volts, direction, duration_sec, cool_sec)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        program_id, s_order,
                        step.get('volts'),
                        step.get('dir', 'R'),
                        parse_time(step.get('time')),
                        parse_time(step.get('cool'))
                    ))

            imported += 1
            print(f"  Imported profile: {profile['name']}")

        conn.commit()
    return imported


def get_all_profiles() -> list:
    """Get all profiles with their programs and each program's steps.

    Steps are included because this is what the dashboard builds its whole
    program library from (loadLibrary -> /api/profiles). Without them every
    library program loads with an empty steps array, which silently breaks
    anything that converts a library program into a device program — Push &
    Run wrote a step-less program to the device and started it, so the motor
    ran in MANU instead of the program.
    """
    with get_connection() as conn:
        profiles = conn.execute(
            "SELECT * FROM profiles ORDER BY name"
        ).fetchall()
        result = []
        for p in profiles:
            p = dict(p)
            programs = conn.execute("""
                SELECT program_id, name, mbc2_label, step_order, cycles, target_rpm, notes
                FROM programs WHERE profile_id = ?
                ORDER BY step_order
            """, (p['profile_id'],)).fetchall()
            p['programs'] = []
            for pr in programs:
                pr = dict(pr)
                steps = conn.execute("""
                    SELECT step_id, step_order, volts, direction, duration_sec, cool_sec, notes
                    FROM program_steps WHERE program_id = ?
                    ORDER BY step_order
                """, (pr['program_id'],)).fetchall()
                pr['steps'] = [dict(s) for s in steps]
                p['programs'].append(pr)
            result.append(p)
        return result


def get_profile_with_steps(profile_id: int) -> dict:
    """Get a full profile including all programs and their steps."""
    with get_connection() as conn:
        profile = conn.execute(
            "SELECT * FROM profiles WHERE profile_id = ?", (profile_id,)
        ).fetchone()
        if not profile:
            return None
        profile = dict(profile)
        programs = conn.execute(
            "SELECT * FROM programs WHERE profile_id = ? ORDER BY step_order",
            (profile_id,)
        ).fetchall()
        profile['programs'] = []
        for prog in programs:
            prog = dict(prog)
            steps = conn.execute(
                "SELECT * FROM program_steps WHERE program_id = ? ORDER BY step_order",
                (prog['program_id'],)
            ).fetchall()
            prog['steps'] = [dict(s) for s in steps]
            profile['programs'].append(prog)
        return profile


def log_breakin_run(motor_id: int, program_ids: list, session_id: int = None, notes: str = None):
    """
    Record which programs were run on a motor during registration or a session.
    program_ids: list of program_id ints in the order they were run.
    """
    with get_connection() as conn:
        for program_id in program_ids:
            conn.execute("""
                INSERT INTO motor_breakin_log (motor_id, program_id, session_id, notes)
                VALUES (?, ?, ?, ?)
            """, (motor_id, program_id, session_id, notes))
        conn.commit()


def get_motor_breakin_history(motor_id: int) -> list:
    """Get full break-in program history for a motor."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                mbl.log_id,
                mbl.date_run,
                mbl.notes,
                pr.name     AS profile_name,
                pg.name     AS program_name,
                pg.mbc2_label,
                pg.step_order,
                mbl.session_id
            FROM motor_breakin_log mbl
            JOIN programs pg ON mbl.program_id = pg.program_id
            JOIN profiles pr ON pg.profile_id = pr.profile_id
            WHERE mbl.motor_id = ?
            ORDER BY mbl.date_run, pg.step_order
        """, (motor_id,)).fetchall()
        return [dict(r) for r in rows]


def get_motor_sessions(motor_id: int) -> list:
    """Get all sessions for a motor with summary stats and row count."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                s.session_id,
                s.session_type,
                s.session_date,
                s.notes,
                mbl.program_id,
                pr.name     AS profile_name,
                pg.name     AS program_name,
                pg.mbc2_label,
                b.peak_rpm,
                b.avg_rpm,
                b.peak_temp_c,
                b.benchmark_type,
                COUNT(sd.data_id) AS row_count
            FROM sessions s
            LEFT JOIN motor_breakin_log mbl ON mbl.session_id = s.session_id
            LEFT JOIN programs pg ON mbl.program_id = pg.program_id
            LEFT JOIN profiles pr ON pg.profile_id = pr.profile_id
            LEFT JOIN benchmarks b ON b.session_id = s.session_id
            LEFT JOIN session_data sd ON sd.session_id = s.session_id
            WHERE s.motor_id = ?
            GROUP BY s.session_id
            ORDER BY s.session_date DESC
        """, (motor_id,)).fetchall()
        return [dict(r) for r in rows]


# ============================================================
# CONNECTION TRACKING
# ============================================================

def _ensure_connections_table(conn):
    """Create connections table if missing (migration for existing DBs)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS connections (
            connection_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at          TEXT    NOT NULL DEFAULT (datetime('now')),
            ended_at            TEXT,
            end_reason          TEXT,
            total_sessions      INTEGER NOT NULL DEFAULT 0,
            notes               TEXT
        )
    """)


def _ensure_crash_events_table(conn):
    """Create crash_events table if missing (migration for existing DBs)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS crash_events (
            event_id            INTEGER PRIMARY KEY AUTOINCREMENT,
            logged_at           TEXT    NOT NULL DEFAULT (datetime('now')),
            connection_id       INTEGER REFERENCES connections(connection_id),
            connection_age_sec  INTEGER,
            session_id          INTEGER REFERENCES sessions(session_id),
            session_age_sec     INTEGER,
            rows_captured       INTEGER,
            prog_name           TEXT,
            prog_step           INTEGER,
            last_volts          REAL,
            last_amps           REAL,
            last_rpm            INTEGER,
            last_kv             INTEGER,
            last_temp           REAL,
            motor_id            INTEGER REFERENCES motors(motor_id),
            motor_identifier    TEXT,
            silence_duration_sec INTEGER,
            trigger             TEXT,
            notes               TEXT
        )
    """)


def _ensure_accel_tables(conn):
    """Create the AccelTest tables if missing (migration for existing DBs).

    Two tables because one test runs 1-10 passes (device setting), and each
    pass is a separate direction/repeat with its own numbers.

    Field names deliberately mirror what the device sends rather than what we
    think it means: field5 is probably winding resistance in milliohms and
    field6 is undecoded. See the v0.200 appendix in docs/SERIAL_SPEC.md. The
    raw line is stored alongside so a later decode can be applied to tests
    already recorded.
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS accel_tests (
            accel_test_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            recorded_at     TEXT    NOT NULL DEFAULT (datetime('now')),
            motor_id        INTEGER REFERENCES motors(motor_id),
            motor_identifier TEXT,
            connection_id   INTEGER REFERENCES connections(connection_id),
            test_voltage_mv INTEGER,
            pass_count      INTEGER NOT NULL DEFAULT 0,
            firmware        TEXT,
            raw_lines       TEXT,
            notes           TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS accel_test_passes (
            accel_pass_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            accel_test_id   INTEGER NOT NULL REFERENCES accel_tests(accel_test_id),
            pass_no         INTEGER NOT NULL,
            direction       TEXT,
            no_rpm          INTEGER,
            no_ma           INTEGER,
            lo_rpm          INTEGER,
            lo_ma           INTEGER,
            hi_rpm          INTEGER,
            hi_ma           INTEGER,
            field5          INTEGER,
            field6          INTEGER,
            raw_line        TEXT
        )
    """)


def save_accel_test(payload: dict) -> int:
    """Store one completed AccelTest and its passes. Returns accel_test_id."""
    passes = payload.get('passes') or []
    with get_connection() as conn:
        _ensure_accel_tables(conn)
        cur = conn.execute("""
            INSERT INTO accel_tests
                (motor_id, motor_identifier, connection_id, test_voltage_mv,
                 pass_count, firmware, raw_lines, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payload.get('motor_id'),
            payload.get('motor_identifier'),
            payload.get('connection_id'),
            payload.get('test_voltage_mv'),
            len(passes),
            payload.get('firmware'),
            payload.get('raw_lines'),
            payload.get('notes'),
        ))
        test_id = cur.lastrowid
        for p in passes:
            conn.execute("""
                INSERT INTO accel_test_passes
                    (accel_test_id, pass_no, direction, no_rpm, no_ma,
                     lo_rpm, lo_ma, hi_rpm, hi_ma, field5, field6, raw_line)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                test_id, p.get('pass_no'), p.get('direction'),
                p.get('no_rpm'), p.get('no_ma'),
                p.get('lo_rpm'), p.get('lo_ma'),
                p.get('hi_rpm'), p.get('hi_ma'),
                p.get('field5'), p.get('field6'), p.get('raw_line'),
            ))
        conn.commit()
        return test_id


def get_accel_tests(motor_id: int = None, limit: int = 50) -> list:
    """Recent AccelTests with their passes, newest first."""
    with get_connection() as conn:
        _ensure_accel_tables(conn)
        if motor_id:
            rows = conn.execute(
                "SELECT * FROM accel_tests WHERE motor_id = ? "
                "ORDER BY accel_test_id DESC LIMIT ?", (motor_id, limit)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM accel_tests ORDER BY accel_test_id DESC LIMIT ?",
                (limit,)).fetchall()
        result = []
        for r in rows:
            t = dict(r)
            t['passes'] = [dict(p) for p in conn.execute(
                "SELECT * FROM accel_test_passes WHERE accel_test_id = ? "
                "ORDER BY pass_no", (t['accel_test_id'],)).fetchall()]
            result.append(t)
        return result


def attach_accel_motor(test_id: int, motor_id: int) -> bool:
    """Point an existing AccelTest at a motor.

    A test run with no motor selected is saved unattributed rather than
    discarded, so there has to be a way to claim it afterwards. Passing a
    motor_id of None detaches it again.
    """
    with get_connection() as conn:
        _ensure_accel_tables(conn)
        identifier = None
        if motor_id:
            row = conn.execute(
                "SELECT identifier FROM motors WHERE motor_id = ?",
                (motor_id,)).fetchone()
            if not row:
                return False
            identifier = row['identifier']
        conn.execute(
            "UPDATE accel_tests SET motor_id = ?, motor_identifier = ? "
            "WHERE accel_test_id = ?", (motor_id or None, identifier, test_id))
        conn.commit()
        return True


def delete_accel_test(test_id: int) -> bool:
    """Delete one AccelTest and its passes."""
    with get_connection() as conn:
        _ensure_accel_tables(conn)
        conn.execute("DELETE FROM accel_test_passes WHERE accel_test_id = ?",
                     (test_id,))
        cur = conn.execute("DELETE FROM accel_tests WHERE accel_test_id = ?",
                           (test_id,))
        conn.commit()
        return cur.rowcount > 0


def open_connection() -> int:
    """Record a new serial connection opening. Returns connection_id."""
    with get_connection() as conn:
        _ensure_connections_table(conn)
        cur = conn.execute(
            "INSERT INTO connections (started_at) VALUES (datetime('now'))"
        )
        conn.commit()
        return cur.lastrowid


def close_connection(connection_id: int, end_reason: str = 'normal') -> None:
    """Mark a connection as closed."""
    with get_connection() as conn:
        _ensure_connections_table(conn)
        conn.execute("""
            UPDATE connections
            SET ended_at = datetime('now'), end_reason = ?
            WHERE connection_id = ?
        """, (end_reason, connection_id))
        conn.commit()


def get_connection_sessions(connection_id: int) -> list:
    """Return all sessions that ran on a given connection, with summary stats."""
    with get_connection() as conn:
        _ensure_crash_events_table(conn)
        _ensure_connections_table(conn)
        rows = conn.execute("""
            SELECT
                s.session_id,
                s.session_type,
                s.session_date,
                s.notes,
                m.identifier    AS motor_identifier,
                pg.name         AS program_name,
                b.peak_rpm,
                b.avg_rpm,
                b.peak_temp_c,
                COUNT(sd.data_id) AS row_count
            FROM sessions s
            LEFT JOIN motors m ON s.motor_id = m.motor_id
            LEFT JOIN motor_breakin_log mbl ON mbl.session_id = s.session_id
            LEFT JOIN programs pg ON mbl.program_id = pg.program_id
            LEFT JOIN benchmarks b ON b.session_id = s.session_id
            LEFT JOIN session_data sd ON sd.session_id = s.session_id
            WHERE s.session_id IN (
                SELECT ce.session_id FROM crash_events ce WHERE ce.connection_id = ?
                UNION
                SELECT s2.session_id FROM sessions s2
                WHERE s2.session_date >= (SELECT started_at FROM connections WHERE connection_id = ?)
                  AND (s2.session_date <= (SELECT ended_at FROM connections WHERE connection_id = ?)
                       OR (SELECT ended_at FROM connections WHERE connection_id = ?) IS NULL)
            )
            GROUP BY s.session_id
            ORDER BY s.session_date ASC
        """, (connection_id, connection_id, connection_id, connection_id)).fetchall()
        return [dict(r) for r in rows]


# ============================================================
# CRASH EVENTS
# ============================================================

def log_crash_event(payload: dict) -> int:
    """
    Record a crash/data-silence event to the crash_events table.
    payload keys (all optional except trigger):
      connection_id, connection_age_sec,
      session_id, session_age_sec, rows_captured,
      prog_name, prog_step, last_volts, last_amps,
      last_rpm, last_kv, last_temp,
      motor_id, motor_identifier,
      silence_duration_sec, trigger, notes
    """
    with get_connection() as conn:
        _ensure_crash_events_table(conn)
        cur = conn.execute("""
            INSERT INTO crash_events (
                connection_id, connection_age_sec,
                session_id, session_age_sec, rows_captured,
                prog_name, prog_step, last_volts, last_amps,
                last_rpm, last_kv, last_temp,
                motor_id, motor_identifier,
                silence_duration_sec, trigger, notes
            ) VALUES (
                :connection_id, :connection_age_sec,
                :session_id, :session_age_sec, :rows_captured,
                :prog_name, :prog_step, :last_volts, :last_amps,
                :last_rpm, :last_kv, :last_temp,
                :motor_id, :motor_identifier,
                :silence_duration_sec, :trigger, :notes
            )
        """, payload)
        conn.commit()
        return cur.lastrowid


def get_crash_events(limit: int = 50) -> list:
    """Return recent crash events with their connection record, newest first."""
    with get_connection() as conn:
        _ensure_crash_events_table(conn)
        _ensure_connections_table(conn)
        rows = conn.execute("""
            SELECT
                ce.*,
                c.started_at        AS conn_started_at,
                c.total_sessions    AS conn_total_sessions
            FROM crash_events ce
            LEFT JOIN connections c ON ce.connection_id = c.connection_id
            ORDER BY ce.event_id DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


def delete_crash_event(event_id: int) -> None:
    """Delete a crash event by ID."""
    with get_connection() as conn:
        _ensure_crash_events_table(conn)
        conn.execute("DELETE FROM crash_events WHERE event_id = ?", (event_id,))
        conn.commit()
