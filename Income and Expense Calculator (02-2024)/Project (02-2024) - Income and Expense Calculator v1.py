# Adding password protection
password = "1234" # This is the current password. Please update this variable when the password changes
print("Please Insert Password: ")
guess = input()
attempt_count = 1
max_attempts = 4
while guess != password:
    print("Incorrect password, please try again")
    guess = input()
    attempt_count = attempt_count + 1 # This decreases the amount of guesses available until they reach zero
    if attempt_count > max_attempts: # This is when the number of attempts exceeds the number of guesses remaining
        print("You have exceeded the maximum number of attempts. Shutting down")
        exit()
print("Access Granted")
print("")

# Defining income
income = float(input("Please Insert Income Amount: R"))

# Adding the first expense
initial_expense = float(input("Please Insert Expense Amount: R"))
print("")
if initial_expense > income:
    print("")
    print("The Expense Amount Is Too Large and Your Remaining Balance Is Insufficient")
    user_input = input("Do You Wish To Continue? Type 'Yes' or 'No' Only: ".lower())
    if user_input == "yes":
        remaining_balance = income - initial_expense
        print("Remaining Balance = R",f"{remaining_balance:.2f}")
        print("")
    if user_input == "no":
        print("Exiting Program")
        exit()
remaining_balance = income - initial_expense

# Loop to add in new expenses and deduct from remaining balance
while remaining_balance > 0:
    print("Remaining Balance = R",f"{remaining_balance:.2f}")
    print("")
    new_expense = float(input("Please Insert Expense Amount: R"))
    if new_expense > remaining_balance: # Display message for if the expense exceeds the remaining balance
        print("")
        print("The Expense Amount Is Too Large and Your Remaining Balance Is Insufficient")
        user_input = input("Do You Wish To Continue? Type 'Yes' or 'No' Only: ".lower())
        if user_input == "yes":
            remaining_balance = remaining_balance - new_expense # Calculating the remaining balance after the next expense is added
            print("Remaining Balance = R",f"{remaining_balance:.2f}")
            print("")
        if user_input == "no":
            print("Exiting Program")
            exit()
    remaining_balance = remaining_balance - new_expense # Calculating the remaining balance after the next expense is added
            
# End message for when the income amount reaches 0
if remaining_balance <= 0:
    print("No Funds Remaining: GAME OVER")
    exit()
                  
