from typing import Callable


class PrintLogger:
	"""Заменяет стандартный логгер, имитируя его интерфейс"""
  def __call__(self, message: str, level: str = "INFO") -> None:
      print(f"[{level.upper()}] {message}")

  def __getattr__(self, level: str) -> Callable[[str], None]:
      # Для поддержки logger.warning() и других методов
      return lambda msg: self(msg, level)