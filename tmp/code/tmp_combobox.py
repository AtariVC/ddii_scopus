import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QComboBox, QVBoxLayout, QWidget, QLabel

class ComboBoxExample(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        # Создаем центральный виджет и layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Создаем QComboBox
        self.combo_box = QComboBox()
        
        # Добавляем элементы
        self.combo_box.addItem("Выберите вариант")
        self.combo_box.addItems(["Python", "JavaScript", "C++", "Java", "Go"])
        
        # Можно добавить элементы с данными
        self.combo_box.addItem("Ruby", "ruby_lang")  # Второй параметр - пользовательские данные
        
        # Создаем метку для отображения выбора
        self.label = QLabel("Выбранный вариант: ")
        
        # Подключаем сигнал изменения выбора
        self.combo_box.currentIndexChanged.connect(self.on_combobox_changed)
        self.combo_box.currentTextChanged.connect(self.on_text_changed)
        
        # Добавляем виджеты в layout
        layout.addWidget(self.combo_box)
        layout.addWidget(self.label)
        
        # Настройки окна
        self.setWindowTitle("Пример QComboBox")
        self.setGeometry(300, 300, 300, 150)
    
    def on_combobox_changed(self, index):
        # Получаем текущий текст и данные
        current_text = self.combo_box.currentText()
        current_data = self.combo_box.currentData()
        
        # Обновляем метку
        self.label.setText(f"Выбранный вариант (индекс {index}): {current_text}")
        
        if current_data:
            print(f"Связанные данные: {current_data}")
    
    def on_text_changed(self, text):
        print(f"Текст изменен на: {text}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = ComboBoxExample()
    ex.show()
    sys.exit(app.exec())