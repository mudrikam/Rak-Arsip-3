import sqlite3
from datetime import datetime


class DatabaseTeamsHelper:
    """Helper class for team management, attendance, and earnings."""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def get_all_teams(self):
        """Get all teams basic information."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "SELECT username, full_name, contact, address, email, phone, attendance_pin, started_at, added_at, bank, account_number, account_holder FROM teams ORDER BY username ASC"
        )
        rows = cursor.fetchall()
        teams = []
        for row in rows:
            teams.append({
                "username": row[0],
                "full_name": row[1],
                "contact": row[2],
                "address": row[3],
                "email": row[4],
                "phone": row[5],
                "attendance_pin": row[6],
                "started_at": row[7],
                "added_at": row[8],
                "bank": row[9],
                "account_number": row[10],
                "account_holder": row[11]
            })
        self.db_manager.close()
        return teams

    def add_team(self, username, full_name, contact, address, email, phone, attendance_pin, started_at, bank, account_number, account_holder, profile_image=None):
        """Add new team member."""
        if not username or not full_name:
            raise ValueError("Username and Full Name cannot be empty.")
        
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            INSERT INTO teams (username, full_name, contact, address, email, phone, attendance_pin, started_at, bank, account_number, account_holder, profile_image, added_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (username, full_name, contact, address, email, phone, attendance_pin, started_at, bank, account_number, account_holder, profile_image))
        self.db_manager.connection.commit()
        self.db_manager.close()
        self.db_manager.create_temp_file()

    def update_team(self, old_username, new_username, full_name, contact, address, email, phone, attendance_pin, started_at, bank, account_number, account_holder, profile_image=None):
        """Update existing team member."""
        if not new_username or not full_name:
            raise ValueError("Username and Full Name cannot be empty.")
        
        self.db_manager.connect()
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            UPDATE teams SET
                username = ?,
                full_name = ?,
                contact = ?,
                address = ?,
                email = ?,
                phone = ?,
                attendance_pin = ?,
                started_at = ?,
                bank = ?,
                account_number = ?,
                account_holder = ?,
                profile_image = ?
            WHERE username = ?
        """, (new_username, full_name, contact, address, email, phone, attendance_pin, started_at, bank, account_number, account_holder, profile_image, old_username))
        self.db_manager.connection.commit()
        self.db_manager.close()
        self.db_manager.create_temp_file()

    def get_team_profile_data(self, username=None):
        """Get detailed team profile data including attendance and earnings."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        params = []
        where = ""
        if username:
            where = "WHERE t.username = ?"
            params.append(username)
        
        cursor.execute(f"""
            SELECT
                t.id, t.username, t.full_name, t.contact, t.address, t.email, t.phone, t.attendance_pin,
                t.started_at, t.added_at, t.bank, t.account_number, t.account_holder,
                t.profile_image,
                -- Attendance summary
                (SELECT COUNT(DISTINCT a.date) FROM attendance a WHERE a.team_id = t.id) as total_days,
                (SELECT COUNT(*) FROM attendance a WHERE a.team_id = t.id) as total_records,
                (SELECT SUM(
                    CASE WHEN a.check_in IS NOT NULL AND a.check_out IS NOT NULL
                        THEN (strftime('%s', a.check_out) - strftime('%s', a.check_in))
                        ELSE 0 END
                ) FROM attendance a WHERE a.team_id = t.id) as total_seconds,
                (SELECT a.check_out FROM attendance a WHERE a.team_id = t.id AND a.check_out IS NOT NULL ORDER BY a.id DESC LIMIT 1) as last_checkout
            FROM teams t
            {where}
            ORDER BY t.username ASC
        """, params)
        
        teams = []
        team_ids = []
        for row in cursor.fetchall():
            team = {
                "id": row[0],
                "username": row[1],
                "full_name": row[2],
                "contact": row[3],
                "address": row[4],
                "email": row[5],
                "phone": row[6],
                "attendance_pin": row[7],
                "started_at": row[8],
                "added_at": row[9],
                "bank": row[10],
                "account_number": row[11],
                "account_holder": row[12],
                "profile_image": row[13],
                "attendance_summary": {
                    "total_days": row[14] or 0,
                    "total_records": row[15] or 0,
                    "total_seconds": row[16] or 0,
                    "last_checkout": row[17] or "-"
                }
            }
            teams.append(team)
            team_ids.append(row[0])
        
        attendance_map = {}
        earnings_map = {}
        client_map = {}
        
        if team_ids:
            # Attendance records
            cursor.execute(
                f"SELECT team_id, date, check_in, check_out, note, id FROM attendance WHERE team_id IN ({','.join(['?']*len(team_ids))}) ORDER BY id DESC",
                tuple(team_ids)
            )
            for row in cursor.fetchall():
                tid = row[0]
                attendance_map.setdefault(tid, []).append((row[1], row[2], row[3], row[4], row[5]))
            
            # Earnings and files
            cursor.execute(
                f"""
                SELECT
                    t.id as team_id, f.id as file_id, f.name, f.date, f.status_id, s.name as status,
                    ip.price, ip.currency,
                    e.amount, e.note,
                    c.client_name
                FROM teams t
                LEFT JOIN earnings e ON e.team_id = t.id
                LEFT JOIN item_price ip ON e.item_price_id = ip.id
                LEFT JOIN files f ON ip.file_id = f.id
                LEFT JOIN statuses s ON f.status_id = s.id
                LEFT JOIN file_client_price fcp ON f.id = fcp.file_id
                LEFT JOIN client c ON fcp.client_id = c.id
                WHERE t.id IN ({','.join(['?']*len(team_ids))})
                """,
                tuple(team_ids)
            )
            for row in cursor.fetchall():
                tid = row[0]
                file_id = row[1]
                if file_id is None:
                    continue
                earning = {
                    "file_id": file_id,
                    "file_name": row[2],
                    "file_date": row[3],
                    "status_id": row[4],
                    "status": row[5],
                    "price": row[6],
                    "currency": row[7],
                    "amount": row[8],
                    "note": row[9],
                    "client_name": row[10]
                }
                earnings_map.setdefault(tid, []).append(earning)
        
        self.db_manager.close()
        return {
            "teams": teams,
            "attendance_map": attendance_map,
            "earnings_map": earnings_map
        }

    # Attendance methods
    def get_latest_open_attendance(self, username, pin):
        """Get latest open attendance record for user."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "SELECT id FROM teams WHERE username = ? AND attendance_pin = ?",
            (username, pin)
        )
        team_row = cursor.fetchone()
        if not team_row:
            self.db_manager.close()
            return None
        
        team_id = team_row[0]
        cursor.execute(
            "SELECT id, date, check_in, check_out, note FROM attendance WHERE team_id = ? AND check_in IS NOT NULL AND check_out IS NULL ORDER BY id DESC LIMIT 1",
            (team_id,)
        )
        attendance_row = cursor.fetchone()
        self.db_manager.close()
        
        if attendance_row:
            return {
                "id": attendance_row[0],
                "date": attendance_row[1],
                "check_in": attendance_row[2],
                "check_out": attendance_row[3],
                "note": attendance_row[4]
            }
        return None

    def add_attendance_record(self, username, pin, note="", mode="checkin"):
        """Add attendance record (check-in or check-out)."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "SELECT id FROM teams WHERE username = ? AND attendance_pin = ?",
            (username, pin)
        )
        team_row = cursor.fetchone()
        self.db_manager.close()
        
        if not team_row:
            return False, "Invalid username or pin."
        
        team_id = team_row[0]
        now_date = datetime.now().strftime("%Y-%m-%d")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if mode == "checkin":
            self.db_manager.connect()
            cursor = self.db_manager.connection.cursor()
            cursor.execute(
                "INSERT INTO attendance (team_id, date, check_in, note) VALUES (?, ?, ?, ?)",
                (team_id, now_date, now_str, note)
            )
            self.db_manager.connection.commit()
            self.db_manager.close()
            self.db_manager.create_temp_file()
            return True, "Checked in."
        elif mode == "checkout":
            self.db_manager.connect(write=False)
            cursor = self.db_manager.connection.cursor()
            cursor.execute(
                "SELECT id FROM attendance WHERE team_id = ? AND check_in IS NOT NULL AND check_out IS NULL ORDER BY id DESC LIMIT 1",
                (team_id,)
            )
            open_attendance = cursor.fetchone()
            self.db_manager.close()
            
            if open_attendance:
                att_id = open_attendance[0]
                self.db_manager.connect()
                cursor = self.db_manager.connection.cursor()
                cursor.execute(
                    "UPDATE attendance SET check_out = ?, note = ? WHERE id = ?",
                    (now_str, note, att_id)
                )
                self.db_manager.connection.commit()
                self.db_manager.close()
                self.db_manager.create_temp_file()
                return True, "Checked out."
            else:
                return False, "No open attendance to check out."
        else:
            return False, "Invalid mode."

    def get_attendance_by_username_pin(self, username, pin):
        """Get latest attendance record by username and pin."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "SELECT id FROM teams WHERE username = ? AND attendance_pin = ?",
            (username, pin)
        )
        team_row = cursor.fetchone()
        if not team_row:
            self.db_manager.close()
            return None
        
        team_id = team_row[0]
        cursor.execute(
            "SELECT date, check_in, check_out, note FROM attendance WHERE team_id = ? ORDER BY id DESC LIMIT 1",
            (team_id,)
        )
        attendance_row = cursor.fetchone()
        self.db_manager.close()
        
        if attendance_row:
            return {
                "date": attendance_row[0],
                "check_in": attendance_row[1],
                "check_out": attendance_row[2],
                "note": attendance_row[3]
            }
        return None

    def get_attendance_records_by_username(self, username):
        """Get all attendance records for username."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT id FROM teams WHERE username = ?", (username,))
        team_row = cursor.fetchone()
        records = []
        if team_row:
            team_id = team_row[0]
            cursor.execute(
                "SELECT date, check_in, check_out, note, id FROM attendance WHERE team_id = ? ORDER BY id DESC",
                (team_id,)
            )
            records = cursor.fetchall()
        self.db_manager.close()
        return records

    def get_attendance_by_team_id_paged(self, team_id, search_text=None, day_filter=None, month_filter=None, year_filter=None, sort_field="date", sort_order="desc", offset=0, limit=20):
        """Get paginated attendance records for team."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        where_clauses = ["team_id = ?"]
        params = [team_id]
        
        hari_map = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
        bulan_map = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        
        if search_text:
            search_pattern = f"%{search_text}%"
            where_clauses.append("(note LIKE ? OR date LIKE ? OR check_in LIKE ? OR check_out LIKE ?)")
            params.extend([search_pattern] * 4)
        
        if day_filter and day_filter != "All Days":
            where_clauses.append("strftime('%w', date) = ?")
            idx = hari_map.index(day_filter) if day_filter in hari_map else None
            if idx is not None:
                params.append(str((idx + 1) % 7))  # SQLite: Sunday=0, Python: Monday=0
        
        if month_filter and month_filter != "All Months":
            idx = bulan_map.index(month_filter) + 1 if month_filter in bulan_map else None
            if idx:
                where_clauses.append("CAST(strftime('%m', date) AS INTEGER) = ?")
                params.append(idx)
        
        if year_filter and year_filter != "All Years":
            where_clauses.append("strftime('%Y', date) = ?")
            params.append(year_filter)
        
        where_sql = "WHERE " + " AND ".join(where_clauses)
        
        sort_map = {
            "Date": "date",
            "Check In": "check_in",
            "Check Out": "check_out",
            "Note": "note"
        }
        sort_sql = sort_map.get(sort_field, "date")
        order_sql = "DESC" if sort_order.lower() in ("desc", "descending") else "ASC"
        
        sql = f"""
            SELECT date, check_in, check_out, note, id
            FROM attendance
            {where_sql}
            ORDER BY {sort_sql} {order_sql}, id DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        self.db_manager.close()
        return [tuple(row) for row in rows]

    def count_attendance_by_team_id_filtered(self, team_id, search_text=None, day_filter=None, month_filter=None, year_filter=None):
        """Count attendance records with filters."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        where_clauses = ["team_id = ?"]
        params = [team_id]
        
        hari_map = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
        bulan_map = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        
        if search_text:
            search_pattern = f"%{search_text}%"
            where_clauses.append("(note LIKE ? OR date LIKE ? OR check_in LIKE ? OR check_out LIKE ?)")
            params.extend([search_pattern] * 4)
        
        if day_filter and day_filter != "All Days":
            idx = hari_map.index(day_filter) if day_filter in hari_map else None
            if idx is not None:
                where_clauses.append("strftime('%w', date) = ?")
                params.append(str((idx + 1) % 7))
        
        if month_filter and month_filter != "All Months":
            idx = bulan_map.index(month_filter) + 1 if month_filter in bulan_map else None
            if idx:
                where_clauses.append("CAST(strftime('%m', date) AS INTEGER) = ?")
                params.append(idx)
        
        if year_filter and year_filter != "All Years":
            where_clauses.append("strftime('%Y', date) = ?")
            params.append(year_filter)
        
        where_sql = "WHERE " + " AND ".join(where_clauses)
        sql = f"SELECT COUNT(*) FROM attendance {where_sql}"
        cursor.execute(sql, params)
        count = cursor.fetchone()[0]
        self.db_manager.close()
        return count

    def attendance_summary_by_team_id_filtered(self, team_id, search_text=None, day_filter=None, month_filter=None, year_filter=None):
        """Get attendance summary with filters."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        where_clauses = ["team_id = ?"]
        params = [team_id]
        
        hari_map = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
        bulan_map = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        
        if search_text:
            search_pattern = f"%{search_text}%"
            where_clauses.append("(note LIKE ? OR date LIKE ? OR check_in LIKE ? OR check_out LIKE ?)")
            params.extend([search_pattern] * 4)
        
        if day_filter and day_filter != "All Days":
            idx = hari_map.index(day_filter) if day_filter in hari_map else None
            if idx is not None:
                where_clauses.append("strftime('%w', date) = ?")
                params.append(str((idx + 1) % 7))
        
        if month_filter and month_filter != "All Months":
            idx = bulan_map.index(month_filter) + 1 if month_filter in bulan_map else None
            if idx:
                where_clauses.append("CAST(strftime('%m', date) AS INTEGER) = ?")
                params.append(idx)
        
        if year_filter and year_filter != "All Years":
            where_clauses.append("strftime('%Y', date) = ?")
            params.append(year_filter)
        
        where_sql = "WHERE " + " AND ".join(where_clauses)
        sql = f"""
            SELECT date, check_in, check_out, note
            FROM attendance
            {where_sql}
        """
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        total_days = set()
        total_records = 0
        total_seconds = 0
        last_checkout = "-"
        
        for row in rows:
            date, check_in, check_out, note = row
            if date:
                total_days.add(date)
            if check_in and check_out:
                try:
                    dt_in = datetime.strptime(check_in, "%Y-%m-%d %H:%M:%S")
                    dt_out = datetime.strptime(check_out, "%Y-%m-%d %H:%M:%S")
                    total_seconds += int((dt_out - dt_in).total_seconds())
                    last_checkout = check_out
                except Exception:
                    pass
            elif check_out:
                last_checkout = check_out
            total_records += 1
        
        self.db_manager.close()
        return {
            "total_days": len(total_days),
            "total_records": total_records,
            "total_seconds": total_seconds,
            "last_checkout": last_checkout
        }

    def get_earnings_by_team_id_paged(self, team_id, search_text=None, batch_filter=None, sort_field="File Name", sort_order="desc", offset=0, limit=20):
        """Get paginated earnings for team."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        where_clauses = ["t.id = ?"]
        params = [team_id]
        
        if search_text:
            search_pattern = f"%{search_text}%"
            where_clauses.append(
                "(f.name LIKE ? OR f.date LIKE ? OR e.amount LIKE ? OR e.note LIKE ? OR s.name LIKE ? OR c.client_name LIKE ? OR fcb.batch_number LIKE ?)"
            )
            params.extend([search_pattern] * 7)
        
        if batch_filter and batch_filter != "All Batches":
            where_clauses.append("fcb.batch_number = ?")
            params.append(batch_filter)
        
        where_sql = "WHERE " + " AND ".join(where_clauses)
        
        sort_map = {
            "File Name": "f.name",
            "Date": "f.date",
            "Amount": "e.amount",
            "Status": "s.name",
            "Client": "c.client_name",
            "Batch": "fcb.batch_number"
        }
        sort_sql = sort_map.get(sort_field, "f.name")
        order_sql = "DESC" if sort_order.lower() in ("desc", "descending") else "ASC"
        
        sql = f"""
            SELECT
                f.name, f.date, e.amount, e.note, s.name as status, c.client_name, fcb.batch_number, f.path
            FROM teams t
            LEFT JOIN earnings e ON e.team_id = t.id
            LEFT JOIN item_price ip ON e.item_price_id = ip.id
            LEFT JOIN files f ON ip.file_id = f.id
            LEFT JOIN statuses s ON f.status_id = s.id
            LEFT JOIN file_client_price fcp ON f.id = fcp.file_id
            LEFT JOIN client c ON fcp.client_id = c.id
            LEFT JOIN file_client_batch fcb ON f.id = fcb.file_id AND c.id = fcb.client_id
            {where_sql}
            ORDER BY {sort_sql} {order_sql}, f.date DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        self.db_manager.close()
        return [tuple(row) for row in rows]

    def count_earnings_by_team_id_filtered(self, team_id, search_text=None, batch_filter=None):
        """Count earnings with filters."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        where_clauses = ["t.id = ?"]
        params = [team_id]
        
        if search_text:
            search_pattern = f"%{search_text}%"
            where_clauses.append(
                "(f.name LIKE ? OR f.date LIKE ? OR e.amount LIKE ? OR e.note LIKE ? OR s.name LIKE ? OR c.client_name LIKE ? OR fcb.batch_number LIKE ?)"
            )
            params.extend([search_pattern] * 7)
        
        if batch_filter and batch_filter != "All Batches":
            where_clauses.append("fcb.batch_number = ?")
            params.append(batch_filter)
        
        where_sql = "WHERE " + " AND ".join(where_clauses)
        
        sql = f"""
            SELECT COUNT(*)
            FROM teams t
            LEFT JOIN earnings e ON e.team_id = t.id
            LEFT JOIN item_price ip ON e.item_price_id = ip.id
            LEFT JOIN files f ON ip.file_id = f.id
            LEFT JOIN statuses s ON f.status_id = s.id
            LEFT JOIN file_client_price fcp ON f.id = fcp.file_id
            LEFT JOIN client c ON fcp.client_id = c.id
            LEFT JOIN file_client_batch fcb ON f.id = fcb.file_id AND c.id = fcb.client_id
            {where_sql}
        """
        cursor.execute(sql, params)
        count = cursor.fetchone()[0]
        self.db_manager.close()
        return count

    def earnings_summary_by_team_id_filtered(self, team_id, search_text=None, batch_filter=None):
        """Get earnings summary with filters."""
        self.db_manager.connect(write=False)
        cursor = self.db_manager.connection.cursor()
        where_clauses = ["t.id = ?"]
        params = [team_id]
        
        if search_text:
            search_pattern = f"%{search_text}%"
            where_clauses.append(
                "(f.name LIKE ? OR f.date LIKE ? OR e.amount LIKE ? OR e.note LIKE ? OR s.name LIKE ? OR c.client_name LIKE ? OR fcb.batch_number LIKE ?)"
            )
            params.extend([search_pattern] * 7)
        
        if batch_filter and batch_filter != "All Batches":
            where_clauses.append("fcb.batch_number = ?")
            params.append(batch_filter)
        
        where_sql = "WHERE " + " AND ".join(where_clauses)
        
        sql = f"""
            SELECT e.amount, s.name as status
            FROM teams t
            LEFT JOIN earnings e ON e.team_id = t.id
            LEFT JOIN item_price ip ON e.item_price_id = ip.id
            LEFT JOIN files f ON ip.file_id = f.id
            LEFT JOIN statuses s ON f.status_id = s.id
            LEFT JOIN file_client_price fcp ON f.id = fcp.file_id
            LEFT JOIN client c ON fcp.client_id = c.id
            LEFT JOIN file_client_batch fcb ON f.id = fcb.file_id AND c.id = fcb.client_id
            {where_sql}
        """
        cursor.execute(sql, params)
        
        total_amount = 0
        total_pending = 0
        total_paid = 0
        
        for row in cursor.fetchall():
            amount, status = row
            try:
                amt = int(float(amount)) if amount is not None else 0
            except Exception:
                amt = 0
            total_amount += amt
            if str(status).lower() == "pending":
                total_pending += amt
            elif str(status).lower() == "paid":
                total_paid += amt
        
        self.db_manager.close()
        return {
            "total_amount": total_amount,
            "total_pending": total_pending,
            "total_paid": total_paid
        }
