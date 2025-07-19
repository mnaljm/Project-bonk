import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiosqlite


class Database:
    def __init__(self):
        self.db_path = Path("data/bot.db")
        self.connection = None
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        """Initialize the database and create tables"""
        # Ensure data directory exists
        self.db_path.parent.mkdir(exist_ok=True)
        
        self.connection = await aiosqlite.connect(self.db_path)
        await self.connection.execute("PRAGMA foreign_keys = ON")
        # Enable row factory for dictionary-like access
        self.connection.row_factory = aiosqlite.Row
        await self.create_tables()
        self.logger.info("Database initialized successfully")

    async def create_tables(self):
        """Create all necessary tables"""
        # Guild configuration table
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id INTEGER PRIMARY KEY,
                prefix TEXT DEFAULT '!',
                log_channel_id INTEGER,
                auto_mod_enabled INTEGER DEFAULT 0,
                max_warnings INTEGER DEFAULT 3,
                mute_role_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Moderation cases table
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS moderation_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                case_type TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason TEXT,
                duration INTEGER,
                expires_at TIMESTAMP,
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (guild_id) REFERENCES guild_config(guild_id)
            )
        """)
        
        # Warnings table
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (guild_id) REFERENCES guild_config(guild_id)
            )
        """)
        
        # Temporary punishments table
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS temp_punishments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                punishment_type TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                case_id INTEGER,
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (guild_id) REFERENCES guild_config(guild_id),
                FOREIGN KEY (case_id) REFERENCES moderation_cases(id)
            )
        """)
        
        # Auto-moderation settings table
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS automod_settings (
                guild_id INTEGER PRIMARY KEY,
                spam_detection INTEGER DEFAULT 1,
                profanity_filter INTEGER DEFAULT 1,
                link_filter INTEGER DEFAULT 0,
                invite_filter INTEGER DEFAULT 1,
                caps_filter INTEGER DEFAULT 1,
                caps_threshold INTEGER DEFAULT 70,
                spam_threshold INTEGER DEFAULT 5,
                lockdown_mode INTEGER DEFAULT 0,
                lockdown_auto_enable INTEGER DEFAULT 1,
                lockdown_caps_threshold INTEGER DEFAULT 50,
                lockdown_spam_threshold INTEGER DEFAULT 3,
                lockdown_timeout_duration INTEGER DEFAULT 300,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (guild_id) REFERENCES guild_config(guild_id)
            )
        """)
        
        # User activity tracking table
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS user_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                date DATE NOT NULL,
                message_count INTEGER DEFAULT 0,
                voice_minutes INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (guild_id) REFERENCES guild_config(guild_id),
                UNIQUE(guild_id, user_id, date)
            )
        """)
        
        # Create indexes for better performance
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_moderation_cases_guild_user 
            ON moderation_cases(guild_id, user_id)
        """)
        
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_warnings_guild_user 
            ON warnings(guild_id, user_id)
        """)
        
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_temp_punishments_expires 
            ON temp_punishments(expires_at, active)
        """)
        
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_activity_guild_user_date
            ON user_activity(guild_id, user_id, date)
        """)
        
        await self.connection.commit()

    async def migrate_database(self):
        """Migrate database schema to add new columns"""
        try:
            # Check if lockdown columns exist
            cursor = await self.connection.execute("PRAGMA table_info(automod_settings)")
            columns = await cursor.fetchall()
            column_names = [column[1] for column in columns]
            
            # Add missing lockdown columns
            if "lockdown_mode" not in column_names:
                await self.connection.execute(
                    "ALTER TABLE automod_settings ADD COLUMN lockdown_mode INTEGER DEFAULT 0"
                )
                self.logger.info("Added lockdown_mode column to automod_settings")
            
            if "lockdown_auto_enable" not in column_names:
                await self.connection.execute(
                    "ALTER TABLE automod_settings ADD COLUMN lockdown_auto_enable INTEGER DEFAULT 1"
                )
                self.logger.info("Added lockdown_auto_enable column to automod_settings")
            
            if "lockdown_caps_threshold" not in column_names:
                await self.connection.execute(
                    "ALTER TABLE automod_settings ADD COLUMN lockdown_caps_threshold INTEGER DEFAULT 50"
                )
                self.logger.info("Added lockdown_caps_threshold column to automod_settings")
            
            if "lockdown_spam_threshold" not in column_names:
                await self.connection.execute(
                    "ALTER TABLE automod_settings ADD COLUMN lockdown_spam_threshold INTEGER DEFAULT 3"
                )
                self.logger.info("Added lockdown_spam_threshold column to automod_settings")
            
            if "lockdown_timeout_duration" not in column_names:
                await self.connection.execute(
                    "ALTER TABLE automod_settings ADD COLUMN lockdown_timeout_duration INTEGER DEFAULT 300"
                )
                self.logger.info("Added lockdown_timeout_duration column to automod_settings")
            
            if "lockdown_manual_override" not in column_names:
                await self.connection.execute(
                    "ALTER TABLE automod_settings ADD COLUMN lockdown_manual_override INTEGER DEFAULT 0"
                )
                self.logger.info("Added lockdown_manual_override column to automod_settings")
            
            # Check if user_activity table exists
            cursor = await self.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='user_activity'"
            )
            user_activity_exists = await cursor.fetchone()
            
            if not user_activity_exists:
                # Create user_activity table
                await self.connection.execute("""
                    CREATE TABLE user_activity (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        date DATE NOT NULL,
                        message_count INTEGER DEFAULT 0,
                        voice_minutes INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (guild_id) REFERENCES guild_config(guild_id),
                        UNIQUE(guild_id, user_id, date)
                    )
                """)
                
                # Create index for user_activity
                await self.connection.execute("""
                    CREATE INDEX idx_user_activity_guild_user_date
                    ON user_activity(guild_id, user_id, date)
                """)
                
                self.logger.info("Created user_activity table and index")
            
            await self.connection.commit()
            self.logger.info("Database migration completed successfully")
            
        except Exception as e:
            self.logger.error(f"Database migration failed: {e}")

    async def initialize(self):
        """Initialize the database and create tables"""
        # Ensure data directory exists
        self.db_path.parent.mkdir(exist_ok=True)
        
        self.connection = await aiosqlite.connect(self.db_path)
        await self.connection.execute("PRAGMA foreign_keys = ON")
        # Enable row factory for dictionary-like access
        self.connection.row_factory = aiosqlite.Row
        await self.create_tables()
        await self.migrate_database()  # Add migration after table creation
        self.logger.info("Database initialized successfully")

    # Guild configuration methods
    async def get_guild_config(self, guild_id: int) -> dict:
        """Get guild configuration"""
        async with self.connection.execute(
            "SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(zip([col[0] for col in cursor.description], row))
            else:
                return await self.create_guild_config(guild_id)

    async def create_guild_config(self, guild_id: int) -> dict:
        """Create default guild configuration"""
        await self.connection.execute(
            "INSERT OR IGNORE INTO guild_config (guild_id) VALUES (?)", (guild_id,)
        )
        await self.connection.commit()
        return await self.get_guild_config(guild_id)

    async def update_guild_config(self, guild_id: int, **kwargs) -> bool:
        """Update guild configuration"""
        if not kwargs:
            return False
        
        fields = ", ".join(f"{key} = ?" for key in kwargs.keys())
        values = list(kwargs.values()) + [guild_id]
        
        await self.connection.execute(
            f"UPDATE guild_config SET {fields}, updated_at = CURRENT_TIMESTAMP WHERE guild_id = ?",
            values
        )
        await self.connection.commit()
        return True

    # Moderation cases methods
    async def create_moderation_case(
        self, guild_id: int, case_type: str, user_id: int, moderator_id: int, 
        reason: str = None, duration: int = None
    ) -> int:
        """Create a new moderation case"""
        expires_at = None
        if duration:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=duration)
        
        cursor = await self.connection.execute(
            """INSERT INTO moderation_cases 
               (guild_id, case_type, user_id, moderator_id, reason, duration, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (guild_id, case_type, user_id, moderator_id, reason, duration, expires_at)
        )
        await self.connection.commit()
        return cursor.lastrowid

    async def get_moderation_case(self, case_id: int) -> dict:
        """Get a specific moderation case"""
        async with self.connection.execute(
            "SELECT * FROM moderation_cases WHERE id = ?", (case_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(zip([col[0] for col in cursor.description], row)) if row else None

    async def get_user_cases(self, guild_id: int, user_id: int) -> list:
        """Get all moderation cases for a user"""
        async with self.connection.execute(
            """SELECT * FROM moderation_cases 
               WHERE guild_id = ? AND user_id = ? 
               ORDER BY created_at DESC""",
            (guild_id, user_id)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(zip([col[0] for col in cursor.description], row)) for row in rows]

    async def get_active_cases(self, guild_id: int) -> list:
        """Get all active moderation cases for a guild"""
        async with self.connection.execute(
            """SELECT * FROM moderation_cases 
               WHERE guild_id = ? AND active = 1 
               ORDER BY created_at DESC""",
            (guild_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(zip([col[0] for col in cursor.description], row)) for row in rows]

    # Warnings methods
    async def add_warning(self, guild_id: int, user_id: int, moderator_id: int, reason: str) -> int:
        """Add a warning to a user"""
        cursor = await self.connection.execute(
            """INSERT INTO warnings (guild_id, user_id, moderator_id, reason)
               VALUES (?, ?, ?, ?)""",
            (guild_id, user_id, moderator_id, reason)
        )
        await self.connection.commit()
        return cursor.lastrowid

    async def get_warnings(self, guild_id: int, user_id: int) -> list:
        """Get all active warnings for a user"""
        async with self.connection.execute(
            """SELECT * FROM warnings 
               WHERE guild_id = ? AND user_id = ? AND active = 1
               ORDER BY created_at DESC""",
            (guild_id, user_id)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(zip([col[0] for col in cursor.description], row)) for row in rows]

    async def get_all_warnings(self, guild_id: int) -> list:
        """Get all active warnings for a guild"""
        async with self.connection.execute(
            """SELECT * FROM warnings 
               WHERE guild_id = ? AND active = 1
               ORDER BY created_at DESC""",
            (guild_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(zip([col[0] for col in cursor.description], row)) for row in rows]

    async def get_warning_count(self, guild_id: int, user_id: int) -> int:
        """Get the number of active warnings for a user"""
        async with self.connection.execute(
            """SELECT COUNT(*) FROM warnings 
               WHERE guild_id = ? AND user_id = ? AND active = 1""",
            (guild_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def remove_warning(self, warning_id: int) -> bool:
        """Remove a specific warning"""
        await self.connection.execute(
            "UPDATE warnings SET active = 0 WHERE id = ?", (warning_id,)
        )
        await self.connection.commit()
        return True

    async def clear_warnings(self, guild_id: int, user_id: int) -> int:
        """Clear all warnings for a user"""
        cursor = await self.connection.execute(
            """UPDATE warnings SET active = 0 
               WHERE guild_id = ? AND user_id = ? AND active = 1""",
            (guild_id, user_id)
        )
        await self.connection.commit()
        return cursor.rowcount

    # Temporary punishments methods
    async def add_temp_punishment(
        self, guild_id: int, user_id: int, punishment_type: str, expires_at: datetime, case_id: int = None
    ) -> int:
        """Add a temporary punishment"""
        cursor = await self.connection.execute(
            """INSERT INTO temp_punishments (guild_id, user_id, punishment_type, expires_at, case_id)
               VALUES (?, ?, ?, ?, ?)""",
            (guild_id, user_id, punishment_type, expires_at, case_id)
        )
        await self.connection.commit()
        return cursor.lastrowid

    async def get_expired_punishments(self) -> list:
        """Get all expired punishments"""
        async with self.connection.execute(
            """SELECT * FROM temp_punishments 
               WHERE expires_at <= CURRENT_TIMESTAMP AND active = 1"""
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(zip([col[0] for col in cursor.description], row)) for row in rows]

    async def remove_temp_punishment(self, punishment_id: int) -> bool:
        """Remove a temporary punishment"""
        await self.connection.execute(
            "UPDATE temp_punishments SET active = 0 WHERE id = ?", (punishment_id,)
        )
        await self.connection.commit()
        return True

    # Auto-moderation settings methods
    async def get_automod_settings(self, guild_id: int) -> dict:
        """Get auto-moderation settings for a guild"""
        async with self.connection.execute(
            "SELECT * FROM automod_settings WHERE guild_id = ?", (guild_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(zip([col[0] for col in cursor.description], row))
            else:
                return await self.create_automod_settings(guild_id)

    async def create_automod_settings(self, guild_id: int) -> dict:
        """Create default auto-moderation settings"""
        # Ensure guild_config exists first (required for foreign key constraint)
        await self.get_guild_config(guild_id)
        
        await self.connection.execute(
            "INSERT OR IGNORE INTO automod_settings (guild_id) VALUES (?)", (guild_id,)
        )
        await self.connection.commit()
        return await self.get_automod_settings(guild_id)

    async def update_automod_settings(self, guild_id: int, **kwargs) -> bool:
        """Update auto-moderation settings"""
        if not kwargs:
            return False
        
        fields = ", ".join(f"{key} = ?" for key in kwargs.keys())
        values = list(kwargs.values()) + [guild_id]
        
        await self.connection.execute(
            f"UPDATE automod_settings SET {fields}, updated_at = CURRENT_TIMESTAMP WHERE guild_id = ?",
            values
        )
        await self.connection.commit()
        return True

    async def is_lockdown_active(self, guild_id: int) -> bool:
        """Check if lockdown mode is active for a guild"""
        automod_settings = await self.get_automod_settings(guild_id)
        return bool(automod_settings.get("lockdown_mode", 0))

    async def enable_lockdown(self, guild_id: int, manual: bool = False) -> bool:
        """Enable lockdown mode for a guild"""
        if manual:
            # Manual override - set both lockdown_mode and lockdown_manual_override
            return await self.update_automod_settings(guild_id, lockdown_mode=1, lockdown_manual_override=1)
        else:
            # Auto-enable - only set lockdown_mode
            return await self.update_automod_settings(guild_id, lockdown_mode=1)

    async def disable_lockdown(self, guild_id: int, manual: bool = False) -> bool:
        """Disable lockdown mode for a guild"""
        if manual:
            # Manual disable - set manual override to prevent auto-enable
            return await self.update_automod_settings(guild_id, lockdown_mode=0, lockdown_manual_override=1)
        else:
            # Auto-disable - only disable lockdown_mode, keep manual override
            return await self.update_automod_settings(guild_id, lockdown_mode=0)
    
    async def is_manual_lockdown_override(self, guild_id: int) -> bool:
        """Check if lockdown has been manually overridden"""
        automod_settings = await self.get_automod_settings(guild_id)
        return bool(automod_settings.get("lockdown_manual_override", 0))
    
    async def clear_lockdown_override(self, guild_id: int) -> bool:
        """Clear manual lockdown override"""
        return await self.update_automod_settings(guild_id, lockdown_manual_override=0)

    # User activity tracking methods
    async def update_user_activity(self, guild_id: int, user_id: int, message_count: int = 0, voice_minutes: int = 0) -> bool:
        """Update user activity for today"""
        from datetime import date
        today = date.today()
        
        try:
            # Try to update existing record
            cursor = await self.connection.execute(
                """UPDATE user_activity 
                   SET message_count = message_count + ?, 
                       voice_minutes = voice_minutes + ?,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE guild_id = ? AND user_id = ? AND date = ?""",
                (message_count, voice_minutes, guild_id, user_id, today)
            )
            
            if cursor.rowcount == 0:
                # No existing record, create new one
                await self.connection.execute(
                    """INSERT INTO user_activity (guild_id, user_id, date, message_count, voice_minutes)
                       VALUES (?, ?, ?, ?, ?)""",
                    (guild_id, user_id, today, message_count, voice_minutes)
                )
            
            await self.connection.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to update user activity: {e}")
            return False

    async def get_user_activity(self, guild_id: int, user_id: int, days: int = 30) -> dict:
        """Get user activity for the last N days"""
        from datetime import date, timedelta
        cutoff_date = date.today() - timedelta(days=days)
        
        async with self.connection.execute(
            """SELECT SUM(message_count) as total_messages, SUM(voice_minutes) as total_voice_minutes
               FROM user_activity 
               WHERE guild_id = ? AND user_id = ? AND date >= ?""",
            (guild_id, user_id, cutoff_date)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "message_count": row["total_messages"] or 0,
                    "voice_minutes": row["total_voice_minutes"] or 0
                }
            return {"message_count": 0, "voice_minutes": 0}

    async def get_top_active_users(self, guild_id: int, days: int = 30, limit: int = 50) -> list:
        """Get top active users in a guild"""
        from datetime import date, timedelta
        cutoff_date = date.today() - timedelta(days=days)
        
        async with self.connection.execute(
            """SELECT user_id, SUM(message_count) as total_messages, SUM(voice_minutes) as total_voice_minutes
               FROM user_activity 
               WHERE guild_id = ? AND date >= ?
               GROUP BY user_id
               ORDER BY (SUM(message_count) + SUM(voice_minutes)/10) DESC
               LIMIT ?""",
            (guild_id, cutoff_date, limit)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def cleanup_old_activity(self, days: int = 90) -> int:
        """Clean up activity data older than specified days"""
        from datetime import date, timedelta
        cutoff_date = date.today() - timedelta(days=days)
        
        cursor = await self.connection.execute(
            "DELETE FROM user_activity WHERE date < ?",
            (cutoff_date,)
        )
        await self.connection.commit()
        return cursor.rowcount

    async def close(self):
        """Close the database connection"""
        if self.connection:
            await self.connection.close()
            self.logger.info("Database connection closed")
