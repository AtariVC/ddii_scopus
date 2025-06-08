from threading import RLock, Thread
from typing import Callable, Type


class Event:

    lock: RLock = RLock()
    def __init__(self, *args: Type) -> None:
        self.subscribers: list[Callable] = []
        self.args: tuple[Type, ...] = args


    def subscribe(self, func: Callable) -> None:
        if func not in self.subscribers:
            self.subscribers.append(func)

    def unsubscribe(self, func: Callable) -> None:
        if func in self.subscribers:
            self.subscribers.remove(func)
            

    def emit(self, *args) -> None:
        """Потоковый излучатель
        """
        with self.lock:
            if len(args) == len(self.args):
                if any(not isinstance(arg, self_arg)
                       for arg, self_arg in zip(args, self.args)):
                    raise TypeError(f'This event should emit next types: '\
                                    f'{self.args}, but you try to emit {args}.')
            else:
                raise TypeError(f'This event should emit next types: '\
                                f'{self.args}, but you try to emit {args}.')
            for callback in self.subscribers:
                _thread: Thread = Thread(name='emit', target=callback,
                                         args=args, daemon=True)
                _thread.start()
                
                
                
def callback1(message: str):
    print(f"Callback 1 received: {message}")

def callback2(message: str):
    print(f"Callback 2 received: {message}")

# Создаем событие, которое передает строку
event = Event(str)

# Подписываем обработчики
event.subscribe(callback1)
event.subscribe(callback2)

# Имитируем событие - вызовет оба обработчика в отдельных потоках
event.emit("Hello World!")

# Отписываем один обработчик
event.unsubscribe(callback1)

# Снова вызываем событие - теперь сработает только callback2
event.emit("Another message")