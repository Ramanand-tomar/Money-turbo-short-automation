import threading
from typing import Any, Callable, Dict

from loguru import logger


class TaskQueueFullError(ValueError):
    pass


class TaskManager:
    def __init__(self, max_concurrent_tasks: int, max_queued_tasks: int = 100):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.max_queued_tasks = max_queued_tasks
        self.current_tasks = 0
        self.lock = threading.Lock()
        self.queue = self.create_queue()

    def update_limits(self, max_concurrent: int, max_queued: int):
        with self.lock:
            self.max_concurrent_tasks = max_concurrent
            self.max_queued_tasks = max_queued
            logger.info(f"Updated TaskManager limits: max_concurrent_tasks={max_concurrent}, max_queued_tasks={max_queued}")

    def create_queue(self):
        raise NotImplementedError()

    def add_task(self, func: Callable, *args: Any, **kwargs: Any):
        with self.lock:
            if self.current_tasks < self.max_concurrent_tasks:
                logger.info(
                    f"add task: {func.__name__}, current_tasks: {self.current_tasks}"
                )
                self.execute_task(func, *args, **kwargs)
            else:
                queue_size = self.queue_size()
                # 并发数已满时才进入排队。队列必须有上限，否则匿名接口可以持续
                # 堆积任务对象和请求参数，最终造成内存耗尽或第三方 API 成本失控。
                if queue_size >= self.max_queued_tasks:
                    logger.warning(
                        f"reject task: {func.__name__}, queue_size: {queue_size}, "
                        f"max_queued_tasks: {self.max_queued_tasks}"
                    )
                    raise TaskQueueFullError("task queue is full, please try again later")

                logger.info(
                    f"enqueue task: {func.__name__}, current_tasks: {self.current_tasks}, "
                    f"queue_size: {queue_size}"
                )
                
                # Update enqueued status in database
                task_id = kwargs.get("task_id")
                user_id = kwargs.get("user_id", "global")
                if task_id:
                    try:
                        from app.services import state as sm
                        position = queue_size + 1
                        sm.state.update_task(
                            task_id,
                            state=0,
                            progress=0,
                            status_message=f"Queued (position {position} in queue)",
                            user_id=user_id
                        )
                    except Exception as err:
                        logger.warning(f"Failed to set enqueued task DB status: {err}")

                self.enqueue({"func": func, "args": args, "kwargs": kwargs})

    def execute_task(self, func: Callable, *args: Any, **kwargs: Any):
        thread = threading.Thread(
            target=self.run_task, args=(func, *args), kwargs=kwargs
        )
        thread.start()

    def run_task(self, func: Callable, *args: Any, **kwargs: Any):
        try:
            with self.lock:
                self.current_tasks += 1
            func(*args, **kwargs)  # call the function here, passing *args and **kwargs.
        finally:
            self.task_done()

    def check_queue(self):
        with self.lock:
            if (
                self.current_tasks < self.max_concurrent_tasks
                and not self.is_queue_empty()
            ):
                task_info = self.dequeue()
                func = task_info["func"]
                args = task_info.get("args", ())
                kwargs = task_info.get("kwargs", {})
                
                # Update dequeued task status to processing in DB immediately to avoid race condition
                task_id = kwargs.get("task_id")
                user_id = kwargs.get("user_id", "global")
                if task_id:
                    try:
                        from app.services import state as sm
                        sm.state.update_task(
                            task_id,
                            state=4,
                            progress=5,
                            status_message="Initializing video generation pipeline...",
                            user_id=user_id
                        )
                        # Now update other queued tasks' positions
                        sm.state.update_queued_positions()
                    except Exception as err:
                        logger.warning(f"Failed to update task status on dequeue: {err}")

                self.execute_task(func, *args, **kwargs)


    def task_done(self):
        with self.lock:
            self.current_tasks -= 1
        self.check_queue()

    def enqueue(self, task: Dict):
        raise NotImplementedError()

    def dequeue(self):
        raise NotImplementedError()

    def is_queue_empty(self):
        raise NotImplementedError()

    def queue_size(self):
        raise NotImplementedError()
