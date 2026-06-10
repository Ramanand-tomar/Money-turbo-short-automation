import ast
from abc import ABC, abstractmethod

from loguru import logger

from app.config import config
from app.models import const


# Base class for state management
class BaseState(ABC):
    @abstractmethod
    def update_task(self, task_id: str, state: int, progress: int = 0, **kwargs):
        pass

    @abstractmethod
    def get_task(self, task_id: str):
        pass

    @abstractmethod
    def get_all_tasks(self, page: int, page_size: int):
        pass

    def update_queued_positions(self):
        pass



# Memory state management
class MemoryState(BaseState):
    def __init__(self):
        self._tasks = {}

    def get_all_tasks(self, page: int, page_size: int):
        start = (page - 1) * page_size
        end = start + page_size
        tasks = list(self._tasks.values())
        total = len(tasks)
        return tasks[start:end], total

    def update_task(
        self,
        task_id: str,
        state: int = const.TASK_STATE_PROCESSING,
        progress: int = 0,
        **kwargs,
    ):
        progress = int(progress)
        if progress > 100:
            progress = 100

        self._tasks[task_id] = {
            "task_id": task_id,
            "state": state,
            "progress": progress,
            **kwargs,
        }

    def get_task(self, task_id: str):
        return self._tasks.get(task_id, None)

    def delete_task(self, task_id: str):
        if task_id in self._tasks:
            del self._tasks[task_id]


# Redis state management
class RedisState(BaseState):
    def __init__(self, host="localhost", port=6379, db=0, password=None):
        import redis

        self._redis = redis.StrictRedis(host=host, port=port, db=db, password=password)

    def get_all_tasks(self, page: int, page_size: int):
        start = (page - 1) * page_size
        end = start + page_size
        tasks = []
        cursor = 0
        total = 0
        while True:
            cursor, keys = self._redis.scan(cursor, count=page_size)
            batch_start = total
            batch_size = len(keys)
            total += batch_size

            # Redis SCAN 是分批返回 key。分页切片必须基于“当前批次起始索引”
            # 计算，而不能用累积后的 total 反推，否则第一页会切到空数组，
            # 第二页也可能只返回部分数据。
            if batch_start < end and total > start:
                slice_start = max(0, start - batch_start)
                slice_end = min(batch_size, end - batch_start)
                for key in keys[slice_start:slice_end]:
                    task_data = self._redis.hgetall(key)
                    task = {
                        k.decode("utf-8"): self._convert_to_original_type(v)
                        for k, v in task_data.items()
                    }
                    tasks.append(task)

            # 即使当前页已经取满，也要继续 SCAN 到 cursor=0，
            # 因为调用方需要准确 total 来渲染分页信息。
            if cursor == 0:
                break
        return tasks, total

    def update_task(
        self,
        task_id: str,
        state: int = const.TASK_STATE_PROCESSING,
        progress: int = 0,
        **kwargs,
    ):
        progress = int(progress)
        if progress > 100:
            progress = 100

        fields = {
            "task_id": task_id,
            "state": state,
            "progress": progress,
            **kwargs,
        }

        for field, value in fields.items():
            self._redis.hset(task_id, field, str(value))

    def get_task(self, task_id: str):
        task_data = self._redis.hgetall(task_id)
        if not task_data:
            return None

        task = {
            key.decode("utf-8"): self._convert_to_original_type(value)
            for key, value in task_data.items()
        }
        return task

    def delete_task(self, task_id: str):
        self._redis.delete(task_id)

    def update_queued_positions(self):
        try:
            keys = []
            cursor = 0
            while True:
                cursor, scan_keys = self._redis.scan(cursor)
                for key in scan_keys:
                    task_data = self._redis.hgetall(key)
                    if task_data:
                        state_val = task_data.get(b"state")
                        if state_val and state_val.decode("utf-8") == "0":
                            keys.append((key, task_data))
                if cursor == 0:
                    break
            
            def get_created_at(item):
                data = item[1]
                ca = data.get(b"created_at")
                return ca.decode("utf-8") if ca else ""
            
            keys.sort(key=get_created_at)
            
            for idx, (key, _) in enumerate(keys):
                position = idx + 1
                status_msg = f"Queued (position {position} in queue)"
                self._redis.hset(key, b"status_message", status_msg.encode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to update queued task positions in Redis: {e}")


    @staticmethod
    def _convert_to_original_type(value):
        """
        Convert the value from byte string to its original data type.
        You can extend this method to handle other data types as needed.
        """
        value_str = value.decode("utf-8")

        try:
            # try to convert byte string array to list
            return ast.literal_eval(value_str)
        except (ValueError, SyntaxError):
            pass

        if value_str.isdigit():
            return int(value_str)
        # Add more conversions here if needed
        return value_str



# NeonDB / SQLite state management for persistent SaaS metadata
class NeonDbState(BaseState):
    def __init__(self):
        import json
        from app.services import db
        self.db = db
        # Ensure database tables are created
        self.db.init_db()

    def _row_to_dict(self, row, columns):
        import json
        if not row:
            return None
        # Handle SQLite Row vs PostgreSQL tuple
        if hasattr(row, 'keys'): # sqlite3.Row
            data = dict(row)
        else: # PostgreSQL tuple
            data = dict(zip(columns, row))
        
        # Deserialize JSON fields
        json_fields = ["params", "videos", "combined_videos", "materials"]
        for field in json_fields:
            if field in data and data[field]:
                try:
                    if isinstance(data[field], str):
                        data[field] = json.loads(data[field])
                except Exception:
                    pass
        return data

    def update_task(
        self,
        task_id: str,
        state: int = None,
        progress: int = None,
        user_id: str = "global",
        **kwargs,
    ):
        import json

        # Serialize parameters if they exist
        serialized_kwargs = {}
        for k, v in kwargs.items():
            if k in ["params", "videos", "combined_videos", "materials"]:
                serialized_kwargs[k] = json.dumps(v)
            else:
                serialized_kwargs[k] = v

        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if task exists
            if self.db.IS_POSTGRES:
                cursor.execute("SELECT 1 FROM tasks WHERE task_id = %s", (task_id,))
            else:
                cursor.execute("SELECT 1 FROM tasks WHERE task_id = ?", (task_id,))
            exists = cursor.fetchone() is not None

            if not exists:
                # Insert dynamic parameters scoped to user_id
                params_val = serialized_kwargs.get("params", None)
                state_val = 4 if state is None else int(state)
                progress_val = 0 if progress is None else int(progress)
                if self.db.IS_POSTGRES:
                    cursor.execute(
                        "INSERT INTO tasks (task_id, state, progress, params, user_id) VALUES (%s, %s, %s, %s, %s)",
                        (task_id, state_val, progress_val, params_val, user_id)
                    )
                else:
                    cursor.execute(
                        "INSERT INTO tasks (task_id, state, progress, params, user_id) VALUES (?, ?, ?, ?, ?)",
                        (task_id, state_val, progress_val, params_val, user_id)
                    )
            else:
                # Update task
                update_fields = {}
                if state is not None:
                    update_fields["state"] = int(state)
                if progress is not None:
                    progress_val = int(progress)
                    if progress_val > 100:
                        progress_val = 100
                    update_fields["progress"] = progress_val
                
                for k, v in serialized_kwargs.items():
                    if k != "task_id" and k != "user_id":
                        update_fields[k] = v
                
                if update_fields:
                    set_clause = []
                    values = []
                    for k, v in update_fields.items():
                        if self.db.IS_POSTGRES:
                            set_clause.append(f"{k} = %s")
                        else:
                            set_clause.append(f"{k} = ?")
                        values.append(v)
                    
                    values.append(task_id)
                    clause_str = ", ".join(set_clause)
                    
                    if self.db.IS_POSTGRES:
                        cursor.execute(f"UPDATE tasks SET {clause_str} WHERE task_id = %s", tuple(values))
                    else:
                        cursor.execute(f"UPDATE tasks SET {clause_str} WHERE task_id = ?", tuple(values))
            
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to update task {task_id} for user {user_id}: {e}")
            conn.rollback()
        finally:
            conn.close()

    def get_task(self, task_id: str):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            if self.db.IS_POSTGRES:
                cursor.execute("SELECT * FROM tasks WHERE task_id = %s", (task_id,))
            else:
                cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            conn.close()
            return self._row_to_dict(row, columns)
        except Exception as e:
            logger.error(f"Failed to fetch task {task_id}: {e}")
            conn.close()
            return None

    def get_all_tasks(self, page: int, page_size: int, user_id: str = "global"):
        offset = (page - 1) * page_size
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            # Get total count filtered by user_id
            if self.db.IS_POSTGRES:
                cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = %s", (user_id,))
            else:
                cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ?", (user_id,))
            total = cursor.fetchone()[0]

            # Fetch paginated tasks filtered by user_id
            if self.db.IS_POSTGRES:
                cursor.execute("SELECT * FROM tasks WHERE user_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s", (user_id, page_size, offset))
            else:
                cursor.execute("SELECT * FROM tasks WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?", (user_id, page_size, offset))
            
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            conn.close()
            
            tasks = [self._row_to_dict(row, columns) for row in rows]
            return tasks, total
        except Exception as e:
            logger.error(f"Failed to fetch all tasks for user {user_id}: {e}")
            conn.close()
            return [], 0

    def delete_task(self, task_id: str):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            if self.db.IS_POSTGRES:
                cursor.execute("DELETE FROM tasks WHERE task_id = %s", (task_id,))
            else:
                cursor.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {e}")
            conn.rollback()
            conn.close()
            return False

    def update_queued_positions(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            if self.db.IS_POSTGRES:
                cursor.execute("SELECT task_id, user_id FROM tasks WHERE state = 0 ORDER BY created_at ASC")
            else:
                cursor.execute("SELECT task_id, user_id FROM tasks WHERE state = 0 ORDER BY created_at ASC")
            rows = cursor.fetchall()
            
            for idx, row in enumerate(rows):
                if hasattr(row, 'keys'):
                    task_id = row['task_id']
                else:
                    task_id = row[0]
                
                position = idx + 1
                status_msg = f"Queued (position {position} in queue)"
                
                if self.db.IS_POSTGRES:
                    cursor.execute("UPDATE tasks SET status_message = %s WHERE task_id = %s", (status_msg, task_id))
                else:
                    cursor.execute("UPDATE tasks SET status_message = ? WHERE task_id = ?", (status_msg, task_id))
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to update queued task positions: {e}")
            conn.rollback()
        finally:
            conn.close()



# Global state - Set NeonDbState as default for production storage compatibility
state = NeonDbState()
