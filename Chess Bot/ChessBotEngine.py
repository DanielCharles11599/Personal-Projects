import chess as ch
import random as rd

class Engine:

    def __init__(self, board, maxDepth, color):
        self.board = board
        self.color = color
        self.maxDepth = maxDepth

    
    def getBestMove(self):
        return self.engine(None, 1)


    def evalFunct(self):
        count = 0
        for i in range(64): # Sums up the material values
            count += self.squareResPoints(ch.SQUARES[i])
        count += self.mateOpportunity() + self.opening() + 0.001*rd.random() # Provides ambiguity to aid Alpha-beta Pruning
        return count


    def mateOpportunity(self):
        if (self.board.legal_moves.count()==0): # No legal moves means it is checkmate
            if (self.board.turn == self.color): # This means that the engine is being checkmated
                return -999
            else:
                return 999
        else:
            return 0


    # Function to make the engine develop in the first moves
    def opening(self):
        if (self.board.fullmove_number < 10):
            if (self.board.turn == self.color):
                return 1/30 * self.board.legal_moves.count()
            else:
                return -1/30 * self.board.legal_moves.count()
        else:
            return 0


    # Function to take a square as input and returns the corresponding Hans Berliner's system value of it's resident
    def squareResPoints(self, square):
        pieceValue = 0
        if(self.board.piece_type_at(square) == ch.PAWN):
            pieceValue = 1
        elif (self.board.piece_type_at(square) == ch.ROOK):
            pieceValue = 5.1
        elif (self.board.piece_type_at(square) == ch.BISHOP):
            pieceValue = 3.33
        elif (self.board.piece_type_at(square) == ch.KNIGHT):
            pieceValue = 3.2
        elif (self.board.piece_type_at(square) == ch.QUEEN):
            pieceValue = 8.8

        if (self.board.color_at(square) != self.color):
            return -pieceValue
        else:
            return pieceValue

        
    def engine(self, candidate, depth):
        
        # Reached max depth of search or no possible moves
        if ( depth == self.maxDepth or self.board.legal_moves.count() == 0):
            return self.evalFunct()
        
        else: 
            moveList = list(self.board.legal_moves) # Get list of legal moves of the current position
            
            newCandidate = None # Initialise newCandidate
                                # newCandidate will be used as a recursive parameter

            # An uneven depth means it's the engine's turn
            if(depth % 2 != 0):
                newCandidate = float("-inf")
            else:
                newCandidate = float("inf")
            
            # Analyses the board after deeper moves
            for i in moveList:

                # Play move i
                self.board.push(i)

                # Get value of move i (by exploring the repercussions)
                value = self.engine(newCandidate, depth + 1) 

                # Basic minmax algorithm:
                # If maximizing (engine's turn)
                if(value > newCandidate and depth % 2 != 0): # Updates candidate based on the surrounding nodes

                    if (depth == 1): # Need to save move played by the engine
                        move = i
                    newCandidate = value
                    
                # If minimizing (human player's turn)
                elif(value < newCandidate and depth % 2 == 0): # Updates candidate based on the surrounding nodes
                    newCandidate = value



                # Alpha-beta prunning cuts: 

                # If previous move was made by the engine
                if (candidate != None and value < candidate and depth % 2 == 0):
                    self.board.pop()
                    break
                
                # If previous move was made by the human player
                elif (candidate != None and value > candidate and depth % 2 != 0):
                    self.board.pop()
                    break
                
                # Undo last move
                self.board.pop()

            # Return result
            if (depth > 1):
                # Return value of a move in the tree
                return newCandidate

            else:
                # Return the move (only on first move)
                return move
