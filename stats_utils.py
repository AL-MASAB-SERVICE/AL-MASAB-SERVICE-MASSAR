def calculate_budget(df):
    income = df[df['type']=='income']['amount'].sum()
    expense = df[df['type']=='expense']['amount'].sum()
    return income, expense, income-expense