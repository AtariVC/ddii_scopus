import h5py
import numpy as np
import pandas as pd
from pathlib import Path


def process_hdf5_and_save_histograms(hdf5_path: Path, output_folder: Path, bins: int = 10):
    """
    Обрабатывает HDF5-файл, извлекает данные из групп "pips" и "sipm",
    строит гистограммы и сохраняет их в виде CSV-файлов.

    Args:
        hdf5_path (Path): Путь к HDF5-файлу.
        output_folder (Path): Папка для сохранения гистограмм в виде CSV-файлов.
        bins (int): Количество интервалов для гистограммы.
    """
    # Убедимся, что папка для результатов существует
    output_folder.mkdir(parents=True, exist_ok=True)

    # Открываем HDF5 файл
    with h5py.File(hdf5_path, "r") as hdf5_file:
        for group_name in ["pips", "sipm"]:
            if group_name in hdf5_file:
                group = hdf5_file[group_name]
                max_values = []

                # Перебираем все наборы данных в группе
                for dataset_name in group.keys():
                    data = group[dataset_name][:]
                    max_value = data.max()  # Находим максимальное значение
                    max_values.append(max_value)

                # Строим гистограмму
                frequencies, bin_edges = np.histogram(max_values, bins=bins)

                # Создаем DataFrame для гистограммы
                histogram_data = pd.DataFrame({
                    "Bin Range": [f"{bin_edges[i]:.2f} - {bin_edges[i+1]:.2f}" for i in range(len(bin_edges) - 1)],
                    "Frequency": frequencies
                })

                # Сохраняем гистограмму в CSV файл
                output_csv_path = output_folder / f"{group_name}_histogram.csv"
                histogram_data.to_csv(output_csv_path, index=False)
                print(f"Гистограмма для группы '{group_name}' сохранена в файл: {output_csv_path}")

            else:
                print(f"Группа '{group_name}' не найдена в файле {hdf5_path}")


# Пример использования
if __name__ == "__main__":
    hdf5_file_path = Path(r"C:/Users\Admin\Desktop\data.hdf5")  # Путь к HDF5-файлу
    output_dir = Path(r"C:/Users\Admin\Desktop/histograms")  # Папка для сохранения результатов

    process_hdf5_and_save_histograms(hdf5_file_path, output_dir, bins=4096)
