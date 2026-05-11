import sqlite3
import json
import datetime

class ProblemDatabase:
    def __init__(self, db_name="math_bank.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self._create_table()

    def _create_table(self):
        c = self.conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS verified_problems (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT,
                difficulty INTEGER,
                problem_data TEXT,
                created_at DATETIME
            )
        ''')
        self.conn.commit()

    def save_problem(self, topic, difficulty, data):
        """仅保存验证通过的题目"""
        c = self.conn.cursor()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute('''
            INSERT INTO verified_problems (topic, difficulty, problem_data, created_at)
            VALUES (?, ?, ?, ?)
        ''', (topic, difficulty, json.dumps(data, ensure_ascii=False), timestamp))
        self.conn.commit()

