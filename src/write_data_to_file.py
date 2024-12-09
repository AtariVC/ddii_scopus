import pandas as pd
import datetime
import os
from pathlib import Path
import h5py
import re
import locale
import numpy as np

locale.setlocale(locale.LC_NUMERIC,"ru_RU")

def writer_graph_data(x: list[int|float], y: list[int|float], name: str, folder_path: Path) -> None:
    if not Path(folder_path).exists():
            os.makedirs(str(folder_path), exist_ok=True)
    current_datetime = datetime.datetime.now()
    time = current_datetime.strftime("%Y-%m-%d_%H-%M-%S-%f")[:23]
    with open(folder_path / f"{time} -- {name}.csv", "wb") as file:
        frame = pd.DataFrame(zip(x, y))
        frame.to_csv(file, index = False, sep=" ")
    file.close()

def write_to_hdf5_file(data: list,
                        name_group: str,
                        path_hdf5 : Path,
                        name_file_hdf5: str,) -> None:
    """_summary_

    Args:
        data (list): Массив любой размерности, важно!!! данные в масиве объеденены по коллонкам
        name_grpup (str): В hdf5 данные обеденены под одним лейблом
        path_hdf5 (Path): Куда сохранять hdf5
        name_file_hdf5 (str): Под каким именем сохранять hdf5
        loc (bool, optional): Если True, то data будет сохранена как строка в виде 1,22
        Нужно для интеграции с Veusz и xcel.
    """
    # if loc:
    #     data = [list(map(locale.str, data_col)) for data_col in data]
    # Преобразование строк в массив байтов для совместимости с HDF5
    if not Path(path_hdf5).exists():
            os.makedirs(str(path_hdf5), exist_ok=True)
    with h5py.File(path_hdf5/Path(f"{name_file_hdf5}.hdf5"), "a") as hdf5_file: # w-перезаписывает, a-добавляет
        # Создаем группу для хранения всех наборов данныхtmp/code/hdf5.py
        if name_group not in hdf5_file:
            data_group = hdf5_file.create_group(name_group)  # Создаем группу
        else:
            data_group = hdf5_file[name_group]  # Используем существующую группу

        current_datetime = datetime.datetime.now()
        time = current_datetime.strftime("%Y-%m-%d_%H-%M-%S-%f")[:23]

        dataset_name = f"{time} -- {name_group}"
        data_np = np.array(data).T
        data_np.squeeze()
        data_group.create_dataset(dataset_name, data=data_np) # type: ignore

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
                df = pd.DataFrame(data) # type: ignore
                df.to_csv(path_output_dir/file_name, sep=" ", index=False, header=False)
                # with open(path_output_dir/file_name, "w") as file:
                #     file.write("\n".join(map(str, data)))

def hdf5_converter(path_to_folder: Path) -> None:
    if os.listdir(path_to_folder):
        for file_name in os.listdir(path_to_folder):
            if Path(path_to_folder/file_name).suffix in (".csv",".txt"):
                if '-- pips' in file_name:
                    name_group= 'pips'
                if '-- sipm' in file_name:
                    name_group = 'sipm'
                data: pd.DataFrame = pd.read_csv(path_to_folder/file_name, sep=' ', index_col=False, names=["x_numeric", "y_numeric"])
                data_list = [data["y_numeric"].tolist()]
                # if loc:
                #     data_list = [list(map(locale.str, data_col)) for data_col in data_list]
                write_to_hdf5_file(data_list, name_group, path_to_folder, path_to_folder.name)

#print(read_hdf5_file(Path.cwd() / "data.hdf5", name_group = "sensor_data"))

# hdf5_to_txt(Path.cwd() / "data.hdf5")

# path = Path("D:\ddii_project\ddii_scopus\log\data_flow/08-10-2024_17-52-54-261")

# hdf5_converter(path)
# hdf5_to_txt(Path("D:\ddii_project\ddii_scopus\log\data_flow/08-10-2024_17-52-54-261/08-10-2024_17-52-54-261.hdf5"))


# value = 3.1415

# print(locale.str(value))