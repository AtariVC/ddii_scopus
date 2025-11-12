class FiltersData:

    def __init__(self):
        self.filters = {
            'нет': None,
            'median()': self.median_filter,
            'moving_average()': self.moving_average_filter,
            'exp_smoothing()': self.exp_smoothing_filter,
        }

    def median_filter(self, data: list[int | float], window_size: int = 5) -> list[float]:
        """Return full-series median filter with trailing window.

        For each index i, compute the median of data[max(0, i-window_size+1): i+1].
        Returns a list of the same length as input.
        """
        if not data:
            return []
        out: list[float] = []
        for i in range(len(data)):
            start = 0 if i - window_size + 1 < 0 else i - window_size + 1
            window = data[start:i + 1]
            w_sorted = sorted(window)
            mid = len(w_sorted) // 2
            if len(w_sorted) % 2 == 0:
                out.append((w_sorted[mid - 1] + w_sorted[mid]) / 2)
            else:
                out.append(float(w_sorted[mid]))
        return out

    def moving_average_filter(self, data: list[int | float], window_size: int = 5) -> list[float]:
        """Return full-series moving average with trailing window.

        For each index i, compute the mean of data[max(0, i-window_size+1): i+1].
        Returns a list of the same length as input.
        """
        if not data:
            return []
        out: list[float] = []
        run_sum: float = 0.0
        from collections import deque
        q = deque()
        for val in data:
            v = float(val)
            q.append(v)
            run_sum += v
            if len(q) > window_size:
                run_sum -= q.popleft()
            out.append(run_sum / len(q))
        return out

    def exp_smoothing_filter(self, data: list[int | float], alpha: float = 0.3) -> list[float]:
        """Return full-series exponential smoothing.

        s0 = data[0]; s[i] = alpha*data[i] + (1-alpha)*s[i-1].
        Returns a list of the same length as input.
        """
        if not data:
            return []
        out: list[float] = []
        s = float(data[0])
        out.append(s)
        for val in data[1:]:
            s = alpha * float(val) + (1.0 - alpha) * s
            out.append(s)
        return out

