import turtle
import random

# Set up the screen
screen = turtle.Screen()
screen.title("Who wants to be a Questionaire?")
screen.bgcolor("white")
screen.setup(width=700, height=500)

# Create the turtle for drawing the path
path_drawer = turtle.Turtle()
path_drawer.speed(0)
path_drawer.color("black")
path_drawer.penup()
path_drawer.goto(-250, 180)
path_drawer.pendown()
path_drawer.hideturtle()

# Function to draw the path (a straight line)
def draw_path(length):
    path_drawer.forward(length)

# Draw the path
draw_path(500)

# Create the turtle character
character = turtle.Turtle()
character.shape("turtle")
character.color("green")
character.penup()
character.speed(0)
character.goto(-250, 180)

# Function to draw notches/markers every 100 units
def draw_notches(total_length, notch_distance):
    for _ in range(total_length // notch_distance):
        path_drawer.penup()
        path_drawer.forward(notch_distance)
        path_drawer.pendown()
        path_drawer.left(90)
        path_drawer.forward(10)
        path_drawer.backward(20)
        path_drawer.forward(10)
        path_drawer.right(90)

# Draw notches/markers
path_drawer.penup()
path_drawer.goto(-250, 180)
path_drawer.pendown()
draw_notches(500, 100)

# Function to display a question on the screen
def display_question(message):
    turtle.clear()
    screen.tracer(False) # Turn off animation
    turtle.penup()
    turtle.goto(0,100)
    turtle.color("green")
    turtle.write(message, align="center", font=("Arial", 18, "normal"))
    screen.tracer(True) # Turn on animation
    turtle.hideturtle()

# Function to display a message on the screen
def display_message(message):
    turtle.clear()
    screen.tracer(False)  # Turn off animation
    turtle.penup()
    turtle.goto(0, 100)
    turtle.color("blue")
    turtle.write(message, align="center", font=("Arial", 18, "bold"))
    screen.tracer(True)  # Turn on animation
    turtle.hideturtle()

# Define the path for the character to move
path = [(x, 180) for x in range(-250, 251, 500)]  # Adjust the range and step as needed

# Define your questions and answers
questions = ["What is 2 + 2?",
             "What is the capital of France?",
             "What is the largest planet in our solar system?",
             "What is the official language of Brazil?",
             "What is the largest land mammal on Earth?",
             "What is the capital city of Gauteng",
             "How many official languages does South Africa have?",
             "What currency is used in the United Kingdom",
             "What is a group of crows called?",
             "What is the national animal of Scotland"]

answers = [["4", "5", "8", "-4"],
           ["New York", "Paris", "Sydney", "Berlin"],
           ["Earth", "Mars", "Jupiter", "Uranus"],
           ["Spanish", "Brazilian", "Gibberish", "Portuguese"],
           ["Elephant", "Chihuahua", "Blue whale", "Hippo"],
           ["Bloemfontein", "Johannesburg", "Cape Town", "Rosebank"],
           ["12", "5", "11", "10"],
           ["Euro", "UK Dollar", "Great British Rand", "Great British Pound"],
           ["Murder", "Killing", "Flock", "Herd"],
           ["Dragon", "Unicorn", "Braveheart", "Goat"]]

# Define the correct answers' indexes
correct_answers = [0, 1, 2, 3, 0, 1, 2, 3, 0, 1]

# Function to ask questions
def ask_question(question, answers, correct_answer):
    display_question(question)
    answer = screen.numinput("Multiple Choice: ", "\n".join(f"{i + 1}. {answer}" for i, answer in enumerate(answers)), minval=1, maxval=len(answers))
    return answer == correct_answer + 1

# Function to move the character forward if the answer is correct
def move_character(correct):
    if correct:
        character.forward(100) # Move the character forward
        if character.xcor() >= 250:  # Check if the character reaches the final marker
            display_message("Congratulations! You reached the finish line.")
            return False # Return False to stop showing the next question
    
    else:
        character.setx(character.xcor() - 100) # Move the character back
        if character.xcor() <= -250: # Check if the character reaches the loss marker
            display_message("Better luck next time!")
            return False # Return False to stop showing the next question

    return True # Return True to continue showing the next question

# Main game loop
random_questions = list(zip(questions, answers, correct_answers))
random.shuffle(random_questions)

show_next_question = True

for question, answers, correct_answer in random_questions:
    if not show_next_question:  # Check if we need to show the next question
        break
    correct = ask_question(question, answers, correct_answer)
    if correct:
        show_next_question = move_character(correct)
    else:
        show_next_question = move_character(False)

    if not show_next_question:  # Check again if we need to show the next question after character movement
        break

# Keep the window open
screen.mainloop()
