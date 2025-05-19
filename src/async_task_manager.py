import asyncio
from typing import Awaitable, Callable, Optional, Dict, Union
from logging import Logger

class AsyncTaskManager:
    def __init__(self, logger: Optional[Logger] = None):
        self.logger = logger
        self._tasks: Dict[str, asyncio.Task] = {}  # Хранит задачи по именам
        
    def _log(self, message: str, level: str = 'info'):
        if self.logger:
            getattr(self.logger, level)(message)
        else:
            print(f"[{level.upper()}] {message}")

    async def create_task(
        self,
        coro: Union[Callable[[], Awaitable], Awaitable],
        name: Optional[str] = None,
        replace_existing: bool = False
    ) -> Optional[asyncio.Task]:
        """
        Создает задачу, если она еще не существует
        
        Args:
            coro: Корутина или функция, возвращающая корутину
            name: Уникальное имя задачи (для проверки дубликатов)
            replace_existing: Заменить существующую задачу, если она есть
            
        Returns:
            Созданная задача или None если задача уже существует
        """
        # Получаем корутину, если передана функция
        if callable(coro) and not asyncio.iscoroutine(coro):
            coro = coro()
        
        # Проверяем существующую задачу
        if name and name in self._tasks:
            existing_task = self._tasks[name]
            if not existing_task.done():
                if replace_existing:
                    self._log(f"Отменяем существующую задачу '{name}'", 'warning')
                    existing_task.cancel()
                else:
                    self._log(f"Задача '{name}' уже выполняется", 'warning')
                    return None
        
        # Создаем новую задачу
        task = asyncio.create_task(coro, name=name)
        
        if name:
            self._tasks[name] = task
        
        def _cleanup(t):
            if name and name in self._tasks:
                del self._tasks[name]
        
        task.add_done_callback(_cleanup)
        return task

    def task_exists(self, name: str) -> bool:
        """Проверяет, существует ли задача с указанным именем"""
        return name in self._tasks and not self._tasks[name].done()

    async def get_task(self, name: str) -> Optional[asyncio.Task]:
        """Возвращает задачу по имени, если она существует и не завершена"""
        task = self._tasks.get(name)
        return task if task and not task.done() else None
    
    def cancel_all(self) -> None:
        """Отменяет все зарегистрированные задачи"""
        for task in self._tasks.values.copy():
            if not task.done():
                task.cancel()

    async def cancel_task(
        self,
        task: Union[str, asyncio.Task],
        wait: bool = True,
        timeout: Optional[float] = None
    ) -> bool:
        """
        Отменяет конкретную задачу
        
        Args:
            task: Имя задачи или объект Task
            wait: Ожидать ли завершения после отмены
            timeout: Таймаут ожидания в секундах
            
        Returns:
            bool: Успешно ли выполнена отмена
        """
        if isinstance(task, str):
            task = self._tasks.get(task)
            if task is None:
                self._log(f"Task '{task}' not found")
                return False

        if task.done():
            return True

        task.cancel()
        
        if wait:
            try:
                await asyncio.wait_for(task, timeout=timeout)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            except Exception as e:
                self._log(f"Error while cancelling task: {e}")
                return False
        return True
    
    def get_running_tasks(self) -> list[asyncio.Task]:
        """Возвращает список активных задач"""
        return [t for t in self._tasks.values() if not t.done()]