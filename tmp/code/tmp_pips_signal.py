import matplotlib.pyplot as plt
import re
import numpy as np
from tmp_particle import Particle
import math as m
import random
from copy import deepcopy

def plot_graph(y, x, baseline, yreal, ycfd, ytrp) -> None:
    """
        Строим линейный график
    """
    plt.plot(x, y)
    plt.plot(x, baseline)
    plt.plot(x, yreal)
    # xcfd = np.arange(40, len(ycfd) + 40, 1)
    # print(len(ycfd))
    plt.plot(x[:len(ycfd)], ycfd)
    # xtrp = np.arange(0, len(ytrp), 1)
    plt.plot(x[:len(ytrp)], ytrp)
    plt.xlabel('Время')
    plt.ylabel('Значение')
    plt.title('График значений')
    plt.show()

def read_waveform_csv(file_path, colum_t = 0, colum_data = 1):
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
    reg_tmp_data = []
    reg_tmp_t = []
    # with open(file_path, 'w') as f1:
        # f1.write("0x0E 0x03 0xA2 0x00 0x00 0x81 0xA6 0xED 0x0E 0x03")
        # pass
    # f1.close()
    try:
        with open(file_path, 'r') as f:
            for index, line in enumerate(f):
                if index % 1 == 0:  # уменьшаем массив данных в n = 1 раз
                    data_tmp = line.strip()
                    str_tmp = re.sub(',','.',data_tmp)  # замена , на .
                    data_tmp = re.split(r"\s+",str_tmp)
                    if len(data_tmp) == 2:
                        reg_tmp_data = re.findall(r'[+-]?\d+\.\d+e[+-]?\d+', data_tmp[colum_data])  # регулярка 1.123e-123
                        reg_tmp_t = re.findall(r'[+-]?\d+\.\d+e[+-]?\d+', data_tmp[colum_t])  # регулярка 1.123e-123
                        if len(reg_tmp_t) > 0:
                            # print(reg_tmp_t)
                            t.append(float(reg_tmp_t[0]))
                            reg_tmp_t = []
                        if len(reg_tmp_data) > 0:
                            data.append(float(reg_tmp_data[0]))
                            reg_tmp_data = []
                        reg_tmp_data = re.findall(r'[+-]?\d+[\.\,]?\d+[\s\b]?', data_tmp[colum_data])  # регулярка 1,123 или 123 или 1.
                        reg_tmp_t = re.findall(r'[+-]?\d+[\.\,]?\d+[\s\b]+', data_tmp[colum_t])
                        if len(reg_tmp_t) > 0:
                            # print(reg_tmp_t)
                            # print(reg_tmp_data)
                            t.append(float(reg_tmp_t[0]))
                            reg_tmp_t = []
                        if len(reg_tmp_data) > 0:
                            data.append(float(reg_tmp_data[0]))
                            reg_tmp_data = []
                        # num16 = hex(int(reg_tmp[1]))
                        # file_path_write = re.sub('.w', '.csv', file_path)
                        # print(file_path_write)
                        # with open(file_path_write, 'a') as f1:
                        #     f1.write(" " + reg_tmp[1]) # hex
                        # f1.close()
                    if len(data_tmp) == 1:
                        data_tmp = line.strip()
                        str_tmp = re.sub(',','.',data_tmp)  # замена , на .
                        reg_tmp_data = re.findall(r'[+-]?\d+\.\d+e[+-]?\d+', data_tmp[0])  # регулярка 1.123e-123
                        if len(reg_tmp_data) > 0:
                            data.append(float(reg_tmp_data[0]))
                        reg_tmp_data = re.findall(r'[+-]?\d+[\.\,]?\d+[\s]+', data_tmp[colum_data])  # регулярка 1,123 или 123 или 1.
                        if len(reg_tmp_data) > 0:
                            data.append(float(reg_tmp_data[0]))
                        t.append(index)
            f.close()
            # f1.write(" 0xA6 0xED")
        # f1.close()
    except FileNotFoundError: # если файл не существует
        pass
    # print(data)
    # print(t)
    return data, t

def trapezoidFaster(y, x, DepthFIFO, Trise, Gap, Invert):
    dx = x[1] - x[0]
    Nrise = round(Trise/dx)

    if Invert:
        yin = -y
    else:
        yin = y

    yout1 = np.zeros(len(y))
    yout2 = np.zeros(len(y))
    yout = np.zeros(len(y))
    for i in range(len(yin) - 2):
        yout[i] = 1/(DepthFIFO) * sum(yin[i: DepthFIFO + i])

    for i in range(len(yin)-(DepthFIFO + Gap)):
        yout2[i] = 1/DepthFIFO * sum(yin[i + Gap : DepthFIFO + Gap + i])
    yout = yout2 - yout1

    # plt.plot(x, yout2)
    # plt.show()
    # yout = np.array(yout[Gap + Nrise:]) - np.array(yout[:-Gap - Nrise])
    return yout

def trapezoid(y, x, Tdecay, Trise, Ttop, Invert):
    dx = x[1] - x[0]
    Nrise = round(Trise/dx)
    Ntop = round(Ttop/dx)
    betta = m.exp(-dx/Tdecay)
    Ndecay = round(Tdecay/dx)
    phy = 1/Nrise

    if Invert:
        yin = np.array(-y)
    else:
        yin = np.array(y)

    # filtration
    # yout = np.array(yin[Nrise:]) - np.array(yin[:-Nrise])

    D       = np.copy(yin)
    Ydel_k  = np.copy(yin)
    Ydel_l  = np.copy(yin)
    Ydel_kl = np.copy(yin)

    Ydel_k[Nrise:] = yin[:-Nrise]
    Ydel_l[Nrise+Ntop:] = yin[:-Nrise-Ntop]
    Ydel_kl[Nrise+Ntop+Nrise:] = yin[:-Nrise-Ntop-Nrise]
    D = (yin-Ydel_k)-(Ydel_l-Ydel_kl)

    plt.plot(x, yin)
    plt.show()
    Ddel = betta*D
    Ddel[1:] = Ddel[:-1]


    Dif = D - Ddel
    Dif[0] = 0
    R = np.cumsum(Dif)

    ytr = np.cumsum(R)

    yout = ytr * phy
    # Создаем копию YA
    # Ydel = np.array(yin)
    # Ydel[Nrise + 1:] = yin[:-Nrise -1]
    # ya = yin - Ydel

    # Ydel = ya
    # Ydel[Nrise + Ntop + 1:] = ya[:-Nrise - Ntop - 1]
    # yb = ya - Ydel

    # yc = yb
    # yout = np.cumsum(yb)

    # # yout4 = list_shifter(yout3*betta, 1)
    # ydel = yc
    # ydel[1:] = np.array(yc[:-1]) * betta
    # yd = yc - ydel

    # ye = yd
    # ye = np.cumsum(yd)

    # yout = phy * ye

    return yout


def meanVal(data: list):
    sum = 0
    size = len(data)
    # print(data)
    for i in range(size):
        sum += data[i]
    mean = float(sum / size)
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
    Trise = random.randint(15, 21)
    Tdecay = random.randint(50, 79)
    c = 80 # Смещение импульса по x, x > c

    for i in range(c + 1, FIFO_depth - c):
        y[i] = A * (m.exp(-(x[i]-c)/Tdecay) - m.exp(-(x[i]-c)/Trise))

    noise = gen_noise(c, FIFO_depth)
    y = y + noise + list(map(int, (np.sin(x/10)*2 + np.sin(x/20)*2 + np.sin(x/40)*2))) + 30
    return y, x, noise

# скольязящее среднее
def SMA(data, n = 7):
    """
    SMA = 1/n*sum(p[t-i])
    p[t-i] - значение функции в точке t - i
    Args:
        data (list):
        n (int): задержка
    """
    data_out = []
    for i in range(len(data)-1):
        if i >= len(data)-n:
            n -= 1
        SMA = 1/n * sum(data[i: n + i])
        data_out.append(SMA)
    data_out.append(data[-1])
    return data_out

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
    yout = np.zeros((len(yin),), dtype=float)

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
    # print(yout)
    return yout

def CFD_Time(y, x, NoiseThreshold, D, K, Invert: bool):
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
    TS = np.zeros(len(y))

    if Invert:
        yin = np.array(-y)
    else:
        yin = np.array(y)

    # выделяем массив задержки
    ydel = np.array(yin)
    ydel[NDelay+1:] = yin[:-NDelay-1]
    ycfd = -K*yin + ydel
    # Time Trigger
    TS = ((yin > NoiseThreshold) & (ycfd < 0))
    try:
        TSIndex = list(TS).index(True)
        TS = TS * (5 * NoiseThreshold)
    except ValueError:
        TSIndex = 0

    return ycfd, TS, TSIndex

def list_shifter(data, shift):
    # for i in range(shift, len(data)):
    #     data_out.append(data[i])
    y_out = np.array(data[shift:]) - np.array(data[:-shift])
    return y_out

def RC_CR2_Time(y, x, AThreshold, NAvg, Trise, Invert: bool):
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
    Nrise = round(Trise/dx)
    TS = np.zeros(len(y))


    if Invert:
        yin = -y
    else:
        yin = y

    # выделяем массив задержки (скользящее среднее)
    y_avg = SMA(yin, NAvg)

    # первый дифф CR, задержка на время нарастания сигнала
    y_out = list_shifter(y_avg, Nrise)
    print(len(y_out))
    plt.plot(t[len(t)-len(y_out):], y_out)
    plt.show()
    # второй дифф CR, задержка на время нарастания сигнала
    yout = list_shifter(y_out, Nrise)

    # Интеграл RC
    # yout = np.cumsum(y_out)

    # Time Trigger
    TS = ((yin[:len(yout)] > AThreshold) & (yout < 0))
    try:
        TSIndex = list(TS).index(True)
        TS = TS * (5 * AThreshold)
    except ValueError:
        TSIndex = 0

    return yout, TS, TSIndex

data, t = read_waveform_csv(file_path = "./tmp/data/CH2_00001.dat")
# data, t, noise = gen_data(FIFO_depth = 512)
bgFIFODepth = 128
dThreshold = 0.000008 #grade_noise_level(noise) # Signal threshold [V]
bgHoldOff = 750E-9 # background hold-off time
# width_median_window = 150
scDecayTime = 100E-9
trTRise = 500E-9
trTTop  = 120E-9
baseline = base_line_Slava(t, data, bgFIFODepth, dThreshold, bgHoldOff)
yreal = data - baseline

# ycfd, TS, TSIndex = RC_CR2_Time(deepcopy(yreal), t, dThreshold, NAvg = 40, Trise = trTRise, Invert = True)
ycfd, TS, TSIndex = CFD_Time(deepcopy(yreal), t, 0.000002, 80E-9, 0.25, Invert = False)
print(TSIndex)
ytrp = trapezoid(deepcopy(yreal), t, Tdecay = scDecayTime, Trise = trTRise, Ttop = trTTop, Invert = False)
# ytrp = trapezoidFaster(deepcopy(yreal), t, DepthFIFO = 50, Trise  = 20, Gap = 20, Invert = False)
# ytrp = []
# ycfd = []
# ycfd = SMA(y_real)
plot_graph(data, t, baseline, -yreal, ycfd, ytrp)
