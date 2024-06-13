import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import UnivariateSpline



# Задайте исходную кривую
x = np.array([1, 2, 3, 4, 5])
y = np.array([2, 3, 5, 7, 11])

# Аппроксимация кривой
spline = UnivariateSpline(x, y, s=0)

# Создание случайных кривых
num_curves = 5  # Количество случайных кривых
noise_level = 0.9  # Уровень шума

for i in range(num_curves):
    # Генерация случайного шума
    noise = np.random.normal(0, noise_level, len(x))
    
    # Создание случайной кривой с добавлением шума
    random_curve = spline(x) + noise
    
    # Отображение результатов
    plt.plot(x, random_curve, label=f'Random Curve {i+1}')

# Отображение исходной кривой
plt.plot(x, y, 'ro-', label='Original Curve')
plt.legend()
plt.show()
