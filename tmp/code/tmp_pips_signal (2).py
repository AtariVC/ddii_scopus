import matplotlib.pyplot as plt
import re
import numpy as np
from tmp_particle import Particle
import math as m
import random

def plot_graph(y, x, baseline, yreal, ycfd) -> None:
    """
        Строим линейный график
    """
    plt.plot(x, y)
    plt.plot(x, baseline)
    plt.plot(x, yreal)
    plt.plot(x, ycfd)
    plt.xlabel('Время')
    plt.ylabel('Значение')
    plt.title('График значений')
    plt.show()

def read_waveform_csv(file_path):
    """
    Reads a CSV file containing waveform data and returns it as a list of numbers.

    Parameters:
    file_path (str): Path to the directory containing the CSV file.

    Returns:
    data (list): List of numbers representing the waveform data.

    Raises:
    ValueError: If the file does not exist or cannot be read.
    """
    # file_path = "./tmp/data/"
    data = []
    t = []
    with open("./tmp/data/mpp_data.txt", 'w') as f1:
        # f1.write("0x0E 0x03 0xA2 0x00 0x00 0x81 0xA6 0xED 0x0E 0x03")
        pass
    f1.close()
    try:
        with open(file_path, 'r') as f:
            for index, line in enumerate(f):
                if index % 1 == 0:  # уменьшаем массив данных в n = 1 раз
                    data_tmp = line.strip()
                    data_tmp = re.sub(',','.',data_tmp)  # замена , на .
                    reg_tmp = re.findall(r'\b[+-]?\d+\.\d+e[+-]?\d+\b', data_tmp)  # регулярка 1,123e-123
                    if len(reg_tmp) > 0:
                        data.append(float(''.join(reg_tmp)))
                    else:
                        reg_tmp = re.findall(r'\b[+-]?\d+[\.\,]?\d*\b', data_tmp)  # регулярка 1,123 или 123 или 1.
                        data.append(int(reg_tmp[1]))
                        num16 = hex(int(reg_tmp[1]))
                        with open("./tmp/data/mpp_data.txt", 'a') as f1:
                            f1.write(" " + reg_tmp[1]) # hex
                        f1.close()
                    t.append(index)
            f.close()
        with open("./tmp/data/mpp_data.txt", 'a') as f1:
            # f1.write(" 0xA6 0xED")
            pass
        f1.close()
    except FileNotFoundError: # если файл не существует
        pass
    return data, t

def trapezoid() -> None:
    pass

def meanVal(data: list) -> int:
    sum = 0
    size = len(data)
    for i in range(size):
        sum += data[i]
    mean: int = int(sum / size)
    return mean

def grade_noise_level(data):
    noise_level = max(data)
    return noise_level


def median_filter(yin, width: int) -> list:
    # Размер окна должен быть нечетным
    if width % 2 == 0:
        width += 1
    half_size: int = width // 2
    base_line = np.zeros(len(yin), dtype=int)
    for i in range(len(yin)):
        if i < half_size or i > len(yin) - half_size+1:
            base_line[i] = yin[i]
        else:
            window = yin[i-half_size:i+half_size+1]
            base_line[i] = sorted(window)[half_size]
    return list(base_line)

def get_val_from_median_filter(window, width: int):
    if width % 2 == 0:
        width += 1
    half_size = width // 2
    median_val = sorted(window)[half_size]
    return median_val

def gen_noise(c, FIFO_depth) -> list[int]:
    noise_tmp = [random.randint(0, 5) for i in range(c)]
    noise_tmp: list[int] = noise_tmp + [random.randint(0, 1) for i in range(c, FIFO_depth - 50 * 2)]
    noise: list[int] = noise_tmp + [random.randint(0, 5) for i in range(FIFO_depth - 50 * 2, FIFO_depth)]
    return noise

def gen_data(FIFO_depth):
    A = random.randint(200, 380)
    x = np.arange(0, FIFO_depth, 1)
    y = np.zeros(FIFO_depth, dtype=int)
    Trise = random.randint(15, 20)
    Tdecay = random.randint(25, 31)
    c = 50 # Смещение импульса по x, x > c

    for i in range(c + 1, FIFO_depth - 50):
        y[i] = A * (m.exp(-(x[i]-c)/Tdecay) - m.exp(-(x[i]-c)/Trise))

    noise = gen_noise(c, FIFO_depth)
    y = y + noise + list(map(int, (np.sin(x/10)*2 + np.sin(x/20)*2 + np.sin(x/40)*2))) + 30
    return y, x, noise


def base_line_Slava(xin, yin, width: int, NoiseThreshold: float, THoldOff: float):
    """
    Args:
        xin (list): Time
        yin (list): Input Signal
        width (int): FIFO width
        NoiseThreshold (int): noise threshold absolute value [V]
        THoldOff (int): время удержания базовой линии после момента, когда сигнал превышает шумовой порог
    """
    dx = xin[1] - xin[0]
    NoiseHold = round(THoldOff / dx)
    yout = np.zeros((len(yin),), dtype=int)

    NoiseHoldCounter = 0

    # init FIFO
    meanFIFO = yin[0:width]
    M = meanVal(meanFIFO)

    for i in range(len(yin)):
        yout[i] = M
        NoiseHoldCounter -= 1
        da = abs(yin[i] - M)
        # алгоритм скользящего среднего
        if (da < NoiseThreshold and NoiseHoldCounter < 1):
            meanFIFO[:-1] = meanFIFO[1:]
            meanFIFO[-1] = yin[i]
            M = meanVal(meanFIFO)

        if (da >= NoiseThreshold and NoiseHoldCounter < 1):
            NoiseHoldCounter = NoiseHold
    return yout

def CFD_Time(y, x, NoiseThreshold, D, K, Invert: bool): # не работает!!!
    """
    Constant-Fraction-Discriminator - нахождение положения переднего фронта по времени
    (положение точки полувысоты амплитуды сигнала по времени)
    Args:
        x (list): Время
        y (list): Сигнал
        NoiseHold (int): Порог шума
        D (int): Задержка
        F ([type]): [description]
        Invert (bool): Инверсия сигнала
    """
    dx = x[1] - x[0]
    NDelay = round(D/dx)
    TS = np.zeros(len(y), dtype=int)

    if Invert:
        yin = -y
    else:
        yin = y

    # выделяем массив задержки
    ydel = yin

    ydel[NDelay+1:] = yin[:-NDelay-1]

    ycfd = -K*yin + ydel
    print(ycfd)
    print(ydel)
    # TS = ((yin > NoiseThreshold) & (ycfd < 0))
    # TSIndex = list(TS).index(1)
    # TS = TS * 5 * NoiseThreshold
    TSIndex = 1
    TS = 1
    return ycfd, TS, TSIndex

def RC_CR2_Time(y, x, AThreshold, Tavg, Trise, Invert: bool):
    """
    Args:
        x (list): Время
        y (list): Сигнал
        AThreshold ([type]): [description]
        Tavg ([type]): [description]
        Trise ([type]): [description]
        Invert (bool): Инверсия сигнала
    """
    dx = x[1] - x[0]
    NAvg = round(Tavg/dx)
    Nrise = round(Trise/dx)
    TS = np.zeros(len(y), dtype=int)

    if Invert:
        yin = -y
    else:
        yin = y

    # выделяем массив задержки (скользящее среднее)
    ydel_avg = yin
    ydel_avg[NAvg+1:] = yin[:-NAvg-1]
    # ydel_avg = yin - ydel_avg
    print(ydel_avg)
    print(yin)

    # первый вывод, RC
    yrise1 = ydel_avg
    yrise1[Nrise+1:] = yrise1[:-Nrise-1]
    yrise1 = ydel_avg - yrise1

    # второй вывод, CR
    yrise2 = ydel_avg
    yrise2[Nrise+1:] = yrise2[:-Nrise-1]
    yrise2 = ydel_avg - yrise2

    yout = np.cumsum(yrise2)
    # print(yout)
    # print(yin)
    TS = ((yin > AThreshold) & (yout < 0))

    try:
        TSIndex = list(TS).index(1)
        TS = TS * 5 * AThreshold
    except ValueError:
        TSIndex = 0
    return yout, TS, TSIndex

# data, t = read_waveform_csv(file_path = "./tmp/data/mpp_data.csv")
data, t, noise = gen_data(FIFO_depth = 512)
bgFIFODepth = 7
dThreshold =  grade_noise_level(noise) # Signal threshold [V]
bgHoldOff = 0 # background hold-off time
# width_median_window = 150
baseline = base_line_Slava(t, data, bgFIFODepth, dThreshold, bgHoldOff)
y_real = data - baseline
ycfd, TS, TSIndex = RC_CR2_Time(y_real, t, AThreshold = 1, Tavg = 2, Trise = 90, Invert = False)

plot_graph(data, t, baseline, y_real, ycfd)
