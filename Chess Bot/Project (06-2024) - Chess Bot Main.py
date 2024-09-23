import ChessBotEngine as ce
import chess as ch

class Main:

    def __init__(self, board=ch.Board):
        self.board = board

    # Function to play a human move
    def playHumanMove(self):
        try:
            print(self.board.legal_moves)
            print("""To undo your last move, type "undo".""")
            play = input("\nYour move: ") # Gets a human move as an input
            print("")
            if (play == "undo"):
                self.board.pop()
                self.board.pop()
                self.playHumanMove()
                return
            self.board.push_san(play)
        except:
            self.playHumanMove()

    # Function to play an engine move
    def playEngineMove(self, maxDepth, color):
        engine = ce.Engine(self.board, maxDepth, color)
        self.board.push(engine.getBestMove())

    # Function to start a game
    def startGame(self):
        color = None # Gets human player's color
        
        while(color != "b" and color != "w"):
            color = input("""Play as (type "b" or "w"): """)

        maxDepth = None

        while(isinstance(maxDepth, int) == False):
            maxDepth = int(input("""Choose depth: """))

        if color == "b":
            while (self.board.is_checkmate() == False):
                print("\nThe engine is thinking...")
                self.playEngineMove(maxDepth, ch.WHITE)
                print(self.board)
                self.playHumanMove()
                print(self.board)
            print(self.board)
            print(self.board.outcome())    

        elif color == "w":
            while (self.board.is_checkmate()==False):
                print(self.board)
                self.playHumanMove()
                print(self.board)
                print("\nThe engine is thinking...")
                self.playEngineMove(maxDepth, ch.BLACK)
            print(self.board)
            print(self.board.outcome())

        self.board.reset # Reset the board
        self.startGame() # Start another game

# Create an instance and start a game
newBoard= ch.Board()
game = Main(newBoard)
start = game.startGame()
