import h5py
import numpy as np
from pathlib import Path

# Функция для генерации данных
def generate_data():
    return [1, 1, 2, 0,3, 9]

# Функция для записи всех данных в один файл
def write_to_single_hdf5_file(output_file, num_datasets=10):
    with h5py.File(output_file, "w") as hdf5_file:
        # Создаем группу для хранения всех наборов данныхtmp/code/hdf5.py
        data_group = hdf5_file.create_group("sensor_data")

        for dataset_index in range(num_datasets):
            # Генерируем данные
            data = generate_data()
            # Создаем новый набор данных
            dataset_name = f"data_{dataset_index:05d}"
            data_group.create_dataset(dataset_name, data=data)
            print(f"Данные записаны в набор: {dataset_name}")

# Функция для чтения всех данных из файла
def read_from_single_hdf5_file(input_file, name_group: str):
    with h5py.File(input_file, "r") as hdf5_file:
        # Переходим в группу данных
        data_group = hdf5_file[name_group]
        all_data = {}
        for dataset_name in data_group:
            # Читаем данные из каждого набора
            all_data[dataset_name] = data_group[dataset_name][:]
            print(f"Прочитаны данные из набора: {dataset_name}")
    return all_data

def hdf5_to_csv(hdf5_file, output_dir):
    """
    Преобразует данные из HDF5-файла в текстовые файлы.

    :param hdf5_file: Путь к HDF5-файлу
    :param output_dir: Папка для сохранения текстовых файлов
    """
    # Убедимся, что папка для текстовых файлов существует
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with h5py.File(hdf5_file, "r") as hdf5_file:
        for group_name in hdf5_file:
            group = hdf5_file[group_name]
            for dataset_name in group:
                data = group[dataset_name][:]
                # Формируем имя текстового файла
                txt_file = output_dir / f"{group_name}_{dataset_name}.txt"
                # Записываем данные в текстовый файл
                with open(txt_file, "w") as file:
                    file.write("\n".join(map(str, data)))
                print(f"Данные из {group_name}/{dataset_name} сохранены в {txt_file}")

# Основной блок кода
if __name__ == "__main__":
    # Путь к файлу HDF5
    hdf5_file = Path("./data.hdf5")

    # Запись данных
    print("Запись данных...")
    write_to_single_hdf5_file(hdf5_file, num_datasets=10)

    # Чтение данных
    print("\nЧтение данных...")
    all_data = read_from_single_hdf5_file(hdf5_file, "sensor_data")

    # Вывод всех данных
    print("\nВсе прочитанные данные:")
    for dataset_name, data in all_data.items():
        print(f"{dataset_name}: {data[:10]}...")  # Выводим первые 10 значений каждого набора


    hdf5_path = Path("./data.hdf5")  # Укажите путь к вашему HDF5-файлу
    output_path = Path("./txt_output")  # Укажите папку для текстовых файлов

    print("Преобразование данных из HDF5 в TXT...")
    hdf5_to_csv(hdf5_path, output_path)
    print("Преобразование завершено.")