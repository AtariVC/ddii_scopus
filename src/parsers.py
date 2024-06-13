"""Различные парсеры
Парсер данных мпп
Парсер log
"""

class Parsers:
    def __init__(self, mpp_data) -> None:
        self.mpp_data = mpp_data

    def mpp_parser(self):
        """Парсер сырых данных МПП

        Returns:
            [type]: [description]
        """
        data = []
        lst_index = []
        # Преобразуем данные в список двухбайтовых значений
        hex_values = [str(self.mpp_data[i] + self.mpp_data[i+1])
                      for i in range(0, len(self.mpp_data), 2)]
        for index, value in enumerate(hex_values):
            hex_value = value.replace('E', '', 1) # удаляем старший бит E
            lst_index.append(index)
            try:
                decimal_value: int = int(hex_value, 16)  # преобразуем значение из шестнадцатеричного в десятичный формат
                data.append(decimal_value)
            except ValueError:
                print(f"Ошибка преобразования значения: {value}")
                continue
        return data, lst_index
