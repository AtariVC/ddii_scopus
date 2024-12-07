import pandas as pd
import datetime

def writer_graph_data(x: list[int|float], y: list[int|float], name: str, folder_path:str) -> None:
    current_datetime = datetime.datetime.now()
    time = current_datetime.strftime("%Y-%m-%d_%H-%M-%S-%f")[:23]
    with open(folder_path + "/" + time + f" -- {name}.csv", "wb") as file:
        frame = pd.DataFrame(zip(x, y))
        frame.to_csv(file, index = False, sep=" ")
    file.close()



