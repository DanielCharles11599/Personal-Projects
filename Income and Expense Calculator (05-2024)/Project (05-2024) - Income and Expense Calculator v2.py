# The two dictionaries are set as global variables to make it easier to update them from each of the functions
income_list = {}
expense_list = {}

# This function repeatedly shows the options menu
def show_menu():
    print("------------------------------------")
    print("Menu:")
    print("1. Add income")
    print("2. Add expense")
    print("3. View all incomes")
    print("4. View all expenses")
    print("5. Change an income")
    print("6. Change an expense")
    print("7. Delete an income")
    print("8. Delete an expense")
    print("9. Calculate budget")
    print("0. Exit")
    print("------------------------------------")


# Function to get integer input from user
def get_integer_input(prompt):
    while True:
        user_input = input(prompt)
        try:
            user_input = int(user_input)
            return user_input
        except ValueError:
            print("Invalid input. Please enter a number.")
            print("")


# This function ensures that the value input is a float            
def get_float_input(prompt):
    while True:
        user_input = input(prompt)
        try:
            user_input = float(user_input)
            return user_input
        except ValueError:
            print("Invalid input. Please enter a number.")
            print("")

            
# This function adds new keys and values to the incomes dictionery
def add_income():
    income_name = input("Enter a name for your income: ").title()
    income_amount = get_float_input("Enter the amount for your income: R ")
    income_list[income_name] = income_amount
    print(income_name, "has been added to your income list")


# This function adds new keys and values to the expenses dictionery
def add_expense():
    expense_name = input("Enter a name for your expense: ").title()
    expense_amount = get_float_input("Enter the amount for your expense: R ")
    expense_list[expense_name] = expense_amount
    print(expense_name, "has been added to your expense list")


# This function prints all incomes
def show_incomes():
    print("Your Incomes:")
    for amount in income_list.values():
        for item, value in income_list.items():
            if value == amount:
                print(f"{item}: R{value:.2f}")

    if len(income_list) == 0: # This will display a message if there are no values in the dictionary
        print("Your income list is empty")


# This function prints all expenses
def show_expenses():
    print("Your Expenses:")
    for amount in expense_list.values():
        for item, value in expense_list.items():
            if value == amount:
                print(f"{item}: R{value:.2f}")

    if len(income_list) == 0: # This will display a message if there are no values in the dictionary
        print("Your expense list is empty")


# This function changes the value of an income based on an input index
def change_income():
    print("Your Incomes:")
    for amount in income_list.values(): # This will show the full income list to the user making it easier to remember their added items
        for item, value in income_list.items():
            if value == amount:
                print(f"{item}: R{value:.2f}")
                
    income_to_change = input("Enter the name of the income you would like to change: ").title()
    if income_to_change in income_list:
        income_list[income_to_change] = float(input("Enter the new amount: R "))
    else:
        print("That item is not in your income items")


# This function changes the value of an expense based on an input index
def change_expense():
    print("Your Expenses:")
    for amount in expense_list.values(): # This will show the full expense list to the user making it easier to remember their added items
        for item, value in expense_list.items():
            if value == amount:
                print(f"{item}: R{value:.2f}")
                
    expense_to_change = input("Enter the name of the expense you would like to change: ").title()
    if expense_to_change in expense_list:
        expense_list[expense_to_change] = float(input("Enter the new amount: R "))
    else:
        print("That item is not in your expense items")


# This function removes both the key and value from the income dictionary
def delete_income():
    print("Your Incomes:")
    for amount in income_list.values():
        for item, value in income_list.items():
            if value == amount:
                print(f"{item}: R{value:.2f}")
                
    income_to_delete = input("Enter the name of the income you would like to remove: ").title()
    if income_to_delete in income_list:
        del income_list[income_to_delete]
        print(income_to_delete, "has been removed from the list")
    else:
        print("That income is not in the list")


# This function removes both the key and value from the expense dictionary
def delete_expense():
    print("Your Expenses:")
    for amount in expense_list.values():
        for item, value in expense_list.items():
            if value == amount:
                print(f"{item}: R{value:.2f}")
                
    expense_to_delete = input("Enter the name of the expense you would like to remove: ").title()
    if expense_to_delete in expense_list:
        del expense_list[expense_to_delete]
        print(expense_to_delete, "has been removed from the list")
    else:
        print("That expense is not in the list")


# This function takes the values of all incomes and subtracts the value of all expenses
def calculate_budget():
    total_income = sum(income_list.values())
    total_expense = sum(expense_list.values())
    budget = total_income - total_expense
    print(f"Your final budget is R{budget:.2f}")
    if budget < 0:
        print("Your expenses are greater than your income")
        print("You will not be able to pay all your expenses this month")


def main():
    flag = True
    while flag == True:
        show_menu()
        while True:
            try:
                user_choice = get_integer_input("Enter the number of your choice: ")
                print("")

                # Perform actions based on user choice
                if user_choice == 1:
                    add_income()
            
                elif user_choice == 2:
                    add_expense()
                
                elif user_choice == 3:
                    show_incomes()
                
                elif user_choice == 4:
                    show_expenses()
                
                elif user_choice == 5:
                    change_income()

                elif user_choice == 6:
                    change_expense()

                elif user_choice == 7:
                    delete_income()

                elif user_choice == 8:
                    delete_expense()

                elif user_choice == 9:
                    calculate_budget()
                
                elif user_choice == 0:
                    flag = False
                    exit()

                else:
                    print("That input is not valid")

                break  # Exit the loop if user input is valid

            except ValueError:
                continue  # Continue prompting if user input is invalid



if __name__ == "__main__":
    main()
