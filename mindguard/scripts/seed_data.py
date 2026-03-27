#!/usr/bin/env python3
"""Seed database with initial data for MindGuard AI."""

import argparse
import json
from pathlib import Path
from datetime import datetime, timedelta
import random
import numpy as np
from typing import Dict, List, Optional
import sqlite3
import hashlib
import uuid

from config.logging_config import setup_logging, get_logger

logger = get_logger(__name__)


class DatabaseSeeder:
    """Seed database with initial data."""
    
    def __init__(self, db_path: Path):
        """
        Initialize database seeder.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        self.conn = None
        
        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def connect(self):
        """Connect to database."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        logger.info(f"Connected to database: {self.db_path}")
    
    def disconnect(self):
        """Disconnect from database."""
        if self.conn:
            self.conn.close()
            logger.info("Disconnected from database")
    
    def create_tables(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                settings TEXT DEFAULT '{}',
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                duration INTEGER,
                mode TEXT DEFAULT 'focus',
                notes TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Cognitive states table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cognitive_states (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                fatigue REAL,
                stress REAL,
                attention REAL,
                cognitive_load REAL,
                confidence REAL,
                FOREIGN KEY (session_id) REFERENCES sessions (id)
            )
        ''')
        
        # Interventions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interventions (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                type TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT,
                status TEXT DEFAULT 'pending',
                completed_at TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (id)
            )
        ''')
        
        # Collector statistics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS collector_stats (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                collector_name TEXT NOT NULL,
                samples INTEGER,
                error_rate REAL,
                is_active BOOLEAN,
                FOREIGN KEY (session_id) REFERENCES sessions (id)
            )
        ''')
        
        # User baselines table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_baselines (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                fatigue_baseline REAL,
                stress_baseline REAL,
                attention_baseline REAL,
                load_baseline REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Weekly reports table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weekly_reports (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                week_start DATE NOT NULL,
                week_end DATE NOT NULL,
                report_data TEXT NOT NULL,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        self.conn.commit()
        logger.info("Database tables created/verified")
    
    def hash_password(self, password: str) -> str:
        """Hash password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def seed_users(self, num_users: int = 5):
        """Seed users table."""
        cursor = self.conn.cursor()
        
        users = [
            {
                'id': str(uuid.uuid4()),
                'username': 'admin',
                'email': 'admin@mindguard.ai',
                'password': 'admin123',
                'full_name': 'System Administrator',
                'role': 'admin',
                'settings': json.dumps({
                    'notifications': True,
                    'theme': 'dark',
                    'privacy_mode': True
                })
            },
            {
                'id': str(uuid.uuid4()),
                'username': 'john_doe',
                'email': 'john@example.com',
                'password': 'password123',
                'full_name': 'John Doe',
                'role': 'user',
                'settings': json.dumps({
                    'notifications': True,
                    'theme': 'dark',
                    'privacy_mode': True,
                    'thresholds': {
                        'fatigue_high': 0.75,
                        'stress_high': 0.7
                    }
                })
            },
            {
                'id': str(uuid.uuid4()),
                'username': 'jane_smith',
                'email': 'jane@example.com',
                'password': 'password123',
                'full_name': 'Jane Smith',
                'role': 'user',
                'settings': json.dumps({
                    'notifications': True,
                    'theme': 'light',
                    'privacy_mode': False
                })
            }
        ]
        
        # Add additional random users
        first_names = ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve', 'Frank', 'Grace', 'Henry']
        last_names = ['Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis']
        
        for i in range(num_users - len(users)):
            first = random.choice(first_names)
            last = random.choice(last_names)
            username = f"{first.lower()}_{last.lower()}"
            
            users.append({
                'id': str(uuid.uuid4()),
                'username': username,
                'email': f"{username}@example.com",
                'password': 'password123',
                'full_name': f"{first} {last}",
                'role': 'user' if random.random() > 0.2 else 'manager',
                'settings': json.dumps({
                    'notifications': random.choice([True, False]),
                    'theme': random.choice(['dark', 'light']),
                    'privacy_mode': random.choice([True, False])
                })
            })
        
        # Insert users
        for user in users:
            cursor.execute('''
                INSERT OR REPLACE INTO users 
                (id, username, email, password_hash, full_name, role, settings)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                user['id'],
                user['username'],
                user['email'],
                self.hash_password(user['password']),
                user['full_name'],
                user['role'],
                user['settings']
            ))
        
        self.conn.commit()
        logger.info(f"Seeded {len(users)} users")
        
        return users
    
    def seed_sessions(self, users: List[Dict], num_sessions: int = 20):
        """Seed sessions table."""
        cursor = self.conn.cursor()
        
        sessions = []
        modes = ['focus', 'meeting', 'break', 'learning']
        
        for _ in range(num_sessions):
            user = random.choice(users)
            
            # Random session time in last 30 days
            start_time = datetime.now() - timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
            
            # Random duration between 15 minutes and 4 hours
            duration = random.randint(900, 14400)
            end_time = start_time + timedelta(seconds=duration)
            
            session = {
                'id': str(uuid.uuid4()),
                'user_id': user['id'],
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration': duration,
                'mode': random.choice(modes),
                'notes': random.choice(['', 'Good session', 'Need improvement', 'Productive'])
            }
            
            cursor.execute('''
                INSERT INTO sessions (id, user_id, start_time, end_time, duration, mode, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                session['id'],
                session['user_id'],
                session['start_time'],
                session['end_time'],
                session['duration'],
                session['mode'],
                session['notes']
            ))
            
            sessions.append(session)
        
        self.conn.commit()
        logger.info(f"Seeded {len(sessions)} sessions")
        
        return sessions
    
    def seed_cognitive_states(self, sessions: List[Dict], points_per_session: int = 100):
        """Seed cognitive states table."""
        cursor = self.conn.cursor()
        
        states = []
        
        for session in sessions:
            start_time = datetime.fromisoformat(session['start_time'])
            
            # Generate random walk for cognitive metrics
            fatigue = [random.uniform(0.2, 0.8)]
            stress = [random.uniform(0.2, 0.8)]
            attention = [random.uniform(0.3, 0.9)]
            cognitive_load = [random.uniform(0.3, 0.8)]
            
            for i in range(1, points_per_session):
                # Random walk with drift
                fatigue.append(np.clip(
                    fatigue[-1] + random.uniform(-0.05, 0.08),
                    0.1, 0.95
                ))
                stress.append(np.clip(
                    stress[-1] + random.uniform(-0.04, 0.06),
                    0.1, 0.9
                ))
                attention.append(np.clip(
                    attention[-1] + random.uniform(-0.06, 0.04),
                    0.1, 0.95
                ))
                cognitive_load.append(np.clip(
                    cognitive_load[-1] + random.uniform(-0.05, 0.07),
                    0.2, 0.9
                ))
            
            # Add trend based on session mode
            if session['mode'] == 'focus':
                # Attention increases, fatigue increases slowly
                for i in range(points_per_session):
                    attention[i] = np.clip(attention[i] + 0.001 * i, 0.3, 0.95)
                    fatigue[i] = np.clip(fatigue[i] + 0.0005 * i, 0.2, 0.9)
            elif session['mode'] == 'meeting':
                # Stress increases, attention varies
                for i in range(points_per_session):
                    stress[i] = np.clip(stress[i] + 0.0015 * i, 0.2, 0.9)
                    attention[i] = np.clip(attention[i] + 0.0002 * i * random.choice([-1, 1]), 0.2, 0.9)
            elif session['mode'] == 'break':
                # All metrics improve
                for i in range(points_per_session):
                    fatigue[i] = np.clip(fatigue[i] - 0.002 * i, 0.1, 0.8)
                    stress[i] = np.clip(stress[i] - 0.002 * i, 0.1, 0.7)
                    attention[i] = np.clip(attention[i] + 0.001 * i, 0.4, 0.95)
                    cognitive_load[i] = np.clip(cognitive_load[i] - 0.0015 * i, 0.2, 0.7)
            
            for i in range(points_per_session):
                timestamp = start_time + timedelta(seconds=i * 30)  # 30-second intervals
                
                if timestamp > datetime.fromisoformat(session['end_time']):
                    break
                
                state = {
                    'id': str(uuid.uuid4()),
                    'session_id': session['id'],
                    'timestamp': timestamp.isoformat(),
                    'fatigue': fatigue[i],
                    'stress': stress[i],
                    'attention': attention[i],
                    'cognitive_load': cognitive_load[i],
                    'confidence': random.uniform(0.7, 0.95)
                }
                
                cursor.execute('''
                    INSERT INTO cognitive_states 
                    (id, session_id, timestamp, fatigue, stress, attention, cognitive_load, confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    state['id'],
                    state['session_id'],
                    state['timestamp'],
                    state['fatigue'],
                    state['stress'],
                    state['attention'],
                    state['cognitive_load'],
                    state['confidence']
                ))
                
                states.append(state)
        
        self.conn.commit()
        logger.info(f"Seeded {len(states)} cognitive states")
        
        return states
    
    def seed_interventions(self, sessions: List[Dict], cognitive_states: List[Dict]):
        """Seed interventions table."""
        cursor = self.conn.cursor()
        
        interventions = []
        intervention_types = [
            'break_reminder', 'breathing_exercise', 'hydration_reminder',
            'task_switch_suggestion', 'stretch_reminder', 'focus_recovery'
        ]
        intervention_levels = ['info', 'suggestion', 'warning', 'critical']
        
        # Group states by session
        session_states = {}
        for state in cognitive_states:
            if state['session_id'] not in session_states:
                session_states[state['session_id']] = []
            session_states[state['session_id']].append(state)
        
        for session_id, states in session_states.items():
            # Check for high fatigue/stress states
            for i, state in enumerate(states):
                if i % 10 == 0 and random.random() > 0.7:  # ~30% chance of intervention
                    fatigue = state['fatigue']
                    stress = state['stress']
                    
                    if fatigue > 0.8 or stress > 0.75:
                        level = 'critical' if max(fatigue, stress) > 0.9 else 'warning'
                        type = random.choice(intervention_types)
                        
                        intervention = {
                            'id': str(uuid.uuid4()),
                            'session_id': session_id,
                            'timestamp': state['timestamp'],
                            'type': type,
                            'level': level,
                            'message': f"High {type.replace('_', ' ')} detected",
                            'status': random.choice(['pending', 'completed', 'dismissed']),
                            'completed_at': None
                        }
                        
                        if intervention['status'] == 'completed':
                            # Add random completion time (1-5 minutes after)
                            comp_time = datetime.fromisoformat(intervention['timestamp']) + timedelta(
                                seconds=random.randint(60, 300)
                            )
                            intervention['completed_at'] = comp_time.isoformat()
                        
                        cursor.execute('''
                            INSERT INTO interventions 
                            (id, session_id, timestamp, type, level, message, status, completed_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            intervention['id'],
                            intervention['session_id'],
                            intervention['timestamp'],
                            intervention['type'],
                            intervention['level'],
                            intervention['message'],
                            intervention['status'],
                            intervention['completed_at']
                        ))
                        
                        interventions.append(intervention)
        
        self.conn.commit()
        logger.info(f"Seeded {len(interventions)} interventions")
        
        return interventions
    
    def seed_baselines(self, users: List[Dict], cognitive_states: List[Dict]):
        """Seed user baselines table."""
        cursor = self.conn.cursor()
        
        baselines = []
        
        for user in users:
            # Get user's cognitive states
            user_states = [
                s for s in cognitive_states
                if any(s['session_id'] == sess['id'] for sess in sessions if sess['user_id'] == user['id'])
            ]
            
            if user_states:
                fatigue_vals = [s['fatigue'] for s in user_states]
                stress_vals = [s['stress'] for s in user_states]
                attention_vals = [s['attention'] for s in user_states]
                load_vals = [s['cognitive_load'] for s in user_states]
                
                baseline = {
                    'id': str(uuid.uuid4()),
                    'user_id': user['id'],
                    'fatigue_baseline': np.mean(fatigue_vals),
                    'stress_baseline': np.mean(stress_vals),
                    'attention_baseline': np.mean(attention_vals),
                    'load_baseline': np.mean(load_vals)
                }
            else:
                baseline = {
                    'id': str(uuid.uuid4()),
                    'user_id': user['id'],
                    'fatigue_baseline': 0.5,
                    'stress_baseline': 0.5,
                    'attention_baseline': 0.6,
                    'load_baseline': 0.5
                }
            
            cursor.execute('''
                INSERT OR REPLACE INTO user_baselines 
                (id, user_id, fatigue_baseline, stress_baseline, attention_baseline, load_baseline)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                baseline['id'],
                baseline['user_id'],
                baseline['fatigue_baseline'],
                baseline['stress_baseline'],
                baseline['attention_baseline'],
                baseline['load_baseline']
            ))
            
            baselines.append(baseline)
        
        self.conn.commit()
        logger.info(f"Seeded {len(baselines)} user baselines")
        
        return baselines
    
    def seed_weekly_reports(self, users: List[Dict], cognitive_states: List[Dict]):
        """Seed weekly reports table."""
        cursor = self.conn.cursor()
        
        reports = []
        
        for user in users:
            # Generate reports for last 4 weeks
            for week_offset in range(4):
                week_start = datetime.now() - timedelta(weeks=week_offset + 1)
                week_end = week_start + timedelta(days=6, hours=23, minutes=59)
                
                # Get user's states for this week
                user_states = [
                    s for s in cognitive_states
                    if any(s['session_id'] == sess['id'] for sess in sessions if sess['user_id'] == user['id'])
                    and week_start <= datetime.fromisoformat(s['timestamp']) <= week_end
                ]
                
                if user_states:
                    report_data = {
                        'summary': {
                            'avg_fatigue': np.mean([s['fatigue'] for s in user_states]),
                            'avg_stress': np.mean([s['stress'] for s in user_states]),
                            'avg_attention': np.mean([s['attention'] for s in user_states]),
                            'avg_load': np.mean([s['cognitive_load'] for s in user_states]),
                            'samples': len(user_states)
                        },
                        'daily_breakdown': {}
                    }
                else:
                    report_data = {
                        'summary': {
                            'avg_fatigue': 0.5,
                            'avg_stress': 0.5,
                            'avg_attention': 0.6,
                            'avg_load': 0.5,
                            'samples': 0
                        },
                        'daily_breakdown': {}
                    }
                
                report = {
                    'id': str(uuid.uuid4()),
                    'user_id': user['id'],
                    'week_start': week_start.date().isoformat(),
                    'week_end': week_end.date().isoformat(),
                    'report_data': json.dumps(report_data)
                }
                
                cursor.execute('''
                    INSERT INTO weekly_reports 
                    (id, user_id, week_start, week_end, report_data)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    report['id'],
                    report['user_id'],
                    report['week_start'],
                    report['week_end'],
                    report['report_data']
                ))
                
                reports.append(report)
        
        self.conn.commit()
        logger.info(f"Seeded {len(reports)} weekly reports")
        
        return reports
    
    def run(self, clear_existing: bool = False):
        """Run the seeder."""
        logger.info("Starting database seeding...")
        
        self.connect()
        
        if clear_existing:
            cursor = self.conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS weekly_reports")
            cursor.execute("DROP TABLE IF EXISTS user_baselines")
            cursor.execute("DROP TABLE IF EXISTS collector_stats")
            cursor.execute("DROP TABLE IF EXISTS interventions")
            cursor.execute("DROP TABLE IF EXISTS cognitive_states")
            cursor.execute("DROP TABLE IF EXISTS sessions")
            cursor.execute("DROP TABLE IF EXISTS users")
            self.conn.commit()
            logger.info("Cleared existing tables")
        
        self.create_tables()
        
        # Seed data
        users = self.seed_users(num_users=10)
        sessions = self.seed_sessions(users, num_sessions=50)
        cognitive_states = self.seed_cognitive_states(sessions, points_per_session=120)
        interventions = self.seed_interventions(sessions, cognitive_states)
        baselines = self.seed_baselines(users, cognitive_states)
        reports = self.seed_weekly_reports(users, cognitive_states)
        
        logger.info("Database seeding completed successfully!")
        
        # Print summary
        print("\n" + "="*50)
        print("DATABASE SEEDING SUMMARY")
        print("="*50)
        print(f"Users: {len(users)}")
        print(f"Sessions: {len(sessions)}")
        print(f"Cognitive States: {len(cognitive_states)}")
        print(f"Interventions: {len(interventions)}")
        print(f"User Baselines: {len(baselines)}")
        print(f"Weekly Reports: {len(reports)}")
        print("="*50)


def main():
    """Main seeding function."""
    parser = argparse.ArgumentParser(description='Seed MindGuard AI database')
    parser.add_argument('--db-path', type=str, default='data/mindguard.db',
                        help='Path to SQLite database')
    parser.add_argument('--clear', action='store_true',
                        help='Clear existing tables before seeding')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(log_level='INFO')
    
    # Run seeder
    seeder = DatabaseSeeder(Path(args.db_path))
    seeder.run(clear_existing=args.clear)


if __name__ == '__main__':
    main()