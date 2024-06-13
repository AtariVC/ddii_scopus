import matplotlib.pyplot as plt


def plot_graph(x, y) -> None:
    """
        Строим линейный график
    """
    plt.plot(x, y)
    plt.xlabel('Порядковый номер')
    plt.ylabel('Значение')
    plt.title('График значений')
    plt.show()

def plot_gist(h, x) -> None:
    """
        Строим гистограмму
    """
    pass
