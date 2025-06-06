

class FiltrsData():
    
    def __init__(self):
        self.filters = {
            'max()': lambda data: max(data) if data else 0,
            'median()': self.median_filter,
            'moving_average()': self.moving_average_filter,
            'exp_smoothing()': self.exp_smoothing_filter
        }

    def median_filter(self, data: list[int | float], window_size: int = 5) -> float:
        """Медианный фильтр последних N значений"""
        if not data:
            return 0
        window = data[-window_size:]
        sorted_window = sorted(window)
        mid_index = len(sorted_window) // 2
        if len(sorted_window) % 2 == 0:
            return (sorted_window[mid_index - 1] + sorted_window[mid_index]) / 2
        else:
            return sorted_window[mid_index]

    def moving_average_filter(self, data: list[int | float], window_size: int = 5) -> float:
        """Скользящее среднее последних N значений"""
        window = data[-window_size:]
        return sum(window)/len(window) if window else 0

    def exp_smoothing_filter(self, data: list[int | float], alpha: float = 0.3) -> float:
        """Экспоненциальное сглаживание"""
        smoothed = data[0] if data else 0
        for val in data[1:]:
            smoothed = alpha * val + (1 - alpha) * smoothed
        return smoothed