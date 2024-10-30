#include <iostream>
#include <string>
#include <vector>
#include <fstream>
#include <sstream>
#include <memory>
#include <ctime>

using namespace std;

// This class will create the question objects
class Question
{
private:
    string questionText;
    vector<string> options;
    int correctOption;

public:
    // Constructor
    Question(string text, vector<string> opt, int correct)
        : questionText(text), options(opt), correctOption(correct) {}

    // Method to display the questions to the user
    void display_question()
    {
        cout << questionText << endl;
        for (int i=0; i<options.size(); ++i)
        {
            cout << (i + 1) << ". " << options[i] << endl;
        }
    }

    // Method to see if the answer is correct
    bool check_answer(int userAnswer)
    {
        return (userAnswer - 1) == correctOption;
    }
};

// Function to load questions from a file
// It returns a vector array of shared_ptr for the questions
vector<shared_ptr<Question>> load_questions()
{
    vector<shared_ptr<Question>> questions;
    ifstream file("questions.txt");

    if (!file.is_open())
    {
        cerr << "Oops! We ran into a problem trying to open your file. Please look at the READ_ME if you need help" << endl;
        return questions;
    }

    string line;
    while (getline(file, line))
    {
        stringstream ss(line);
        string questionText;
        vector<string> options(4);
        int correctOption;

        // Reads each line from the file using ',' as the break between items
        getline(ss, questionText, ',');

        // Read all four options after the break from the question text
        for (int i=0; i<4; ++i)
        {
            getline(ss, options[i], ',');
        }


        ss >> correctOption;
        correctOption--; // Adjust to reflect the index of the item


        // Creates and adds the question object to the vector array
        questions.push_back(make_shared<Question>(questionText, options, correctOption));
    }

    file.close();

    return questions;
}

// Function to display the questions
void ask_question(shared_ptr<Question> question, int &score)
{
    question->display_question(); // Uses a member access operator to access the display_question() method
                                  // question is a shared_ptr that manages the questions used
                                  // in the display_question() method

    int userAnswer;
    cout << "Your answer: ";
    cin >> userAnswer;

    // Input validation to ensure that the user's guess matches available options
    while (userAnswer<1 || userAnswer>4)
    {
        cin.clear();
        cin.ignore();

        // Ensures the input is an integer
        if(!isdigit(userAnswer))
        {
            cout << "Please enter a number only!: ";

            cin >> userAnswer;
            cin.clear();
            cin.ignore();
        }

        else
        {
            cout << "Unfortunately that's not a valid option! Please enter a number between 1 and 4: ";
            cin >> userAnswer;
        }

    }

    // Increases the user's score depending on if they were correct
    if (question->check_answer(userAnswer))
    {
        cout << "Well Done!" << endl;
        score++;
    }
    else
    {
        cout << "That's Incorrect!" << endl;
    }

    cout << endl;
}

// Function to display the final score
void display_results(int score, int totalQuestions)
{
    cout << "Quiz completed!" << endl;
    cout << "Your score is: " << score << " out of " << totalQuestions << endl;

    double result = (double)score / (double)totalQuestions;

    if(result == 1.0)
    {
        cout << "Congrats on getting them all correct!" << endl;
    }
    else if((result < 1.0) && (result >= 0.5))
    {
        cout << "Almost there! Keep trying" << endl;
    }
    else if((result < 0.5) && (result > 0.0))
    {
        cout << "You'll need to put in a bit more effort!" << endl;
    }
    else if(result == 0.0)
    {
        cout << "You got nothing right! Keep practising" << endl;
    }
}

// Function to save the score to a file
void save_score(int score, int totalQuestions)
{
    ofstream outputFile("results.txt", ios::app); // Opens the file in append mode to store the results of multiple attempts
    if (outputFile)
    {
        // Get the current date and time for the output file
        time_t now = time(nullptr);

        outputFile << ctime(&now);
        outputFile << "Score: " << score << " out of " << totalQuestions << endl;
        outputFile << endl;
        outputFile.close();
        cout << "Score saved to 'results.txt'" << endl;
    }
    else
    {
        cerr << "There was an error saving your score." << endl;
    }
}

int main()
{
    vector<shared_ptr<Question>> questions = load_questions();

    // If there are question objects then start the game
    if (!questions.empty())
    {
        int score = 0;
        for (const auto &question : questions)
        {
            ask_question(question, score);
        }

        display_results(score, questions.size());
        save_score(score, questions.size());
    }
    else
    {
        cout << "We failed to load any questions! Please check the input file." << endl;
    }

    return 0;
}
