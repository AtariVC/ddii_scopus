import pandas as pd

# Создаем DataFrame
df = pd.DataFrame({
    'Name': ['Alice', 'Bob', 'Charlie', 'David', 'Eva'],
    'Age': [24, 19, 30, 40, 22],
    'City': ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix']
})

print("Original DataFrame:")
print(df)

# Фильтрация данных по возрасту от 20 до 35 лет
filtered_df = df[(df['Age'] >= 20) & (df['Age'] <= 35)]

# Вывод отфильтрованного DataFrame
print("\nFiltered DataFrame:")
print(filtered_df)