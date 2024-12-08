import pandas as pd
import datetime
import os
from pathlib import Path
import h5py

def writer_graph_data(x: list[int|float], y: list[int|float], name: str, folder_path: str) -> None:
    if not Path(folder_path).exists():
            os.makedirs(str(folder_path), exist_ok=True)
    current_datetime = datetime.datetime.now()
    time = current_datetime.strftime("%Y-%m-%d_%H-%M-%S-%f")[:23]
    with open(folder_path + "/" + time + f" -- {name}.csv", "wb") as file:
        frame = pd.DataFrame(zip(x, y))
        frame.to_csv(file, index = False, sep=" ")
    file.close()

def write_to_hdf5_file(file_path_hdf5 : Path, name_grpup: str, data: list) -> None:
    with h5py.File(file_path_hdf5, "w") as hdf5_file:
        # Создаем группу для хранения всех наборов данныхtmp/code/hdf5.py
        data_group = hdf5_file.create_group(name_grpup)

        current_datetime = datetime.datetime.now()
        time = current_datetime.strftime("%Y-%m-%d_%H-%M-%S-%f")[:23]

        dataset_name = f"{time} -- {name_grpup}"
        data_group.create_dataset(dataset_name, data=data)
        print(f"Данные записаны в набор: {dataset_name}")

def read_hdf5_file(file_path_hdf5 : Path, name_group: str):
    with h5py.File(file_path_hdf5, "r") as hdf5_file:
        if not isinstance(name_group, str):
            raise TypeError(f"Имя группы должно быть строкой, получено: {type(name_group)}")
        if name_group not in hdf5_file:
            raise ValueError(f"Группа '{name_group}' не найдена в файле {file_path_hdf5}")
        name_group = hdf5_file[name_group] # type: ignore
        all_data = {}
        for dataset_name in name_group:
            # Читаем данные из каждого набора
            all_data[dataset_name] = name_group[dataset_name][:] # type: ignore
    return all_data


def hdf5_to_txt(path_hdf5_file: Path) -> None:
    """
    Преобразует данные из HDF5-файла в текстовые файлы.

    :param path_hdf5_file: Путь к HDF5-файлу
    """
    # Убедимся, что папка для текстовых файлов существует
    output_dir = path_hdf5_file.parent / path_hdf5_file.stem
    output_dir.mkdir(parents=True, exist_ok=True)
    with h5py.File(path_hdf5_file, "r") as hdf5_file: # type: ignore
        for group_name in hdf5_file:
            group = hdf5_file[group_name] # type: ignore
            for dataset_name in group:
                data: pd = group[dataset_name][:] # type: ignore
                # Формируем имя текстового файла
                path_output_dir =  output_dir / group_name # type: ignore
                file_name = f"{dataset_name}.csv"
                path_output_dir.mkdir(parents=True, exist_ok=True)
                # Записываем данные в текстовый файл
                df = pd.DataFrame(data.T) # type: ignore
                df.to_csv(path_output_dir/file_name, sep=" ", index=False, header=False)
                # with open(path_output_dir/file_name, "w") as file:
                #     file.write("\n".join(map(str, data)))
                print(f"Данные из {group_name}/{dataset_name} сохранены в {file_name}")

#print(read_hdf5_file(Path.cwd() / "data.hdf5", name_group = "sensor_data"))

hdf5_to_txt(Path.cwd() / "data.hdf5")