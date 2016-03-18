HotStreakAPI

## Installation Instructions:
1.  Update the value of application in app.yaml to the app ID you have registered
in the App Engine admin console and would like to use to host your instance of this sample.
2.  Run Google App Engine Launcher. Choose to add an existing application and select
the project's directory. Click the run button.
3.  Ensure it's running by visiting the API Explorer - by default localhost:8080/_ah/api/explorer. 
 

##Game Description:
HotStreak is a higher/lower card game that includes betting. The dealer receives a
card that is displayed to the user. The user then guesses whether their card will be
higher or lower than the dealer's card. The user also bets points depending on how 
sure they are of their guess. The game gives the user 10 points at the start of the 
game. Guessing correctly increases the users points by the bet amount. If the user
receives the same card as the dealer, the user wins double their bet. The goal of the
game is to accumulate as many points as possible before the game ends by guessing
incorrectly. 
Many different HotStreak games can be played by many different Users at any
given time. Each game can be retrieved or played by using the path parameter
`urlsafe_game_key`.

##Files Included:
 - api.py: Contains endpoints and game playing logic.
 - app.yaml: App configuration.
 - cron.yaml: Cronjob configuration.
 - main.py: Handler for taskqueue handler.
 - models.py: Entity and message definitions including helper methods.
 - utils.py: Helper function for retrieving ndb.Models by urlsafe Key string.
 - Design.txt: Description of the game design decisions and process.

##Endpoints Included:
 - **create_user**
    - Path: 'user'
    - Method: POST
    - Parameters: user_name, email (optional)
    - Returns: Message confirming creation of the User.
    - Description: Creates a new User. user_name provided must be unique. Will 
    raise a ConflictException if a User with that user_name already exists.
 
 - **get_user_rankings**
    - Path: 'user/rankings'
    - Method: GET
    - Parameters: NONE
    - Returns: All users in the database in descending order by average score.
    - Description: Ranks all the users in the database based on their average
    score.  

 - **new_game**
    - Path: 'game'
    - Method: POST
    - Parameters: user_name
    - Returns: GameForm with initial game state.
    - Description: Creates a new Game. user_name provided must correspond to an
    existing user - will raise a NotFoundException if not. Also informs the user
    that they begin the game with 10 points.
     
 - **get_game**
    - Path: 'game/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameForm with current game state.
    - Description: Returns the current state of a game. Also displays the dealer's
    card to the user.
    
 - **stop_game**
    - Path: 'game/{urlsafe_game_key}'
    - Method: DELETE
    - Parameters: urlsafe_game_key
    - Returns: Message that they game has been deleted.
    - Description: Deletes an active game. Raises exceptions if the game does not
    exist or if the game has been completed.

 - **make_move**
    - Path: 'game/{urlsafe_game_key}'
    - Method: PUT
    - Parameters: urlsafe_game_key, guess, bet
    - Returns: GameForm with new game state.
    - Description: Accepts a 'guess' and a 'bet" and returns the updated state of the game. Records the status of the move the the game's history. If the game ends, a corresponding Score entity will be created. If the user's and the dealer's cards are the same, adds the "lucky email to the taskqueue. 
    
 - **get_user_games**
    - Path: 'user/games'
    - Method: GET
    - Parameters: user_name, email (optional)
    - Returns: GameForms for all active games belonging to a user.
    - Description: Returns all games in the database belonging to a specific user 
    that have not been completed.

 - **get_game_history**
    - Path: 'game/{urlsafe_game_key}/history'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: String message containing the history of the specified game.
    - Descriptions: Displays a history of the user's guesses for a specific game.

 - **get_high_scores**
    - Path: 'scores'
    - Method: PUT
    - Parameters: num_results
    - Returns: ScoreForms.
    - Description: Returns all Scores in the database order by the amount of points
    in descending order. The number of displayed scores can be limited by the user.
    
 - **get_user_scores**
    - Path: 'scores/user/{user_name}'
    - Method: GET
    - Parameters: user_name
    - Returns: ScoreForms. 
    - Description: Returns all Scores recorded by the provided player (unordered).
    Will raise a NotFoundException if the User does not exist.
    
 - **get_average_score**
    - Path: 'games/average_score'
    - Method: GET
    - Parameters: None
    - Returns: StringMessage
    - Description: Gets the average score for all games from a previously cached memcache key.

##Models Included:
 - **User**
    - Stores unique user_name, (optional) email address, total points scored and
    total games played.
    
 - **Game**
    - Stores unique game states. Associated with User model via KeyProperty.
    
 - **Score**
    - Records completed games. Associated with Users model via KeyProperty.
    
##Forms Included:
 - **GameForm**
    - Representation of a Game's state (urlsafe_key, points, next card, game_over flag, message, user_name).
 - **NewGameForm**
    - Used to create a new game (user_name)
 - **MakeMoveForm**
    - Inbound make move form (guess, bet).
 - **ScoreRequestForm**
    - Userd to limit the number of returned scores.
 - **ScoreForm**
    - Representation of a completed game's Score (user_name, date, points).
 - **ScoreForms**
    - Multiple ScoreForm container.
 - **UserForms**
    - Representation of a User's information (user_name, email, total_points, total_games, average_score)
 - **UserForms**
    - Multiple UserForm Container
 - **StringMessage**
    - General purpose String container.

##References and Notes**
- Used the GuessANumberAPI as a starting point for this project. Changed Models, Forms, and endpoints to what HotStreakAPI required. Replaced game logic with HotStreak game logic. Updated taskqueue and cron jobs to match project requirements.

- Note: Added an email to the taskqueue when the user gets lucky and receives the same card as the dealer. I changed the cron job to send a reminder email once a year. I made these changes because the game logic doesn't really give an obvious point to send reminder emails. On a personal note, i dislike reminder emails and think they should be sent very infrequently. 