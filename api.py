"""api.py - Create and configure the Game API exposing the resources.
This can also contain game logic. For more complex games it would be wise to
move game logic to another file. Ideally the API will be simple, concerned
primarily with communication to/from the API's users."""


import logging
import endpoints
import random
from protorpc import remote, messages
from google.appengine.api import memcache
from google.appengine.api import taskqueue

from models import User, Game, Score
from models import StringMessage, NewGameForm, GameForm, MakeMoveForm,\
    ScoreForms, GameForms, ScoreRequestForm, UserForm, UserForms
from utils import get_by_urlsafe

SCORE_REQUEST = endpoints.ResourceContainer(ScoreRequestForm)
NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
GET_GAME_REQUEST = endpoints.ResourceContainer(
        urlsafe_game_key=messages.StringField(1),)
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(
    MakeMoveForm,
    urlsafe_game_key=messages.StringField(1),)
USER_REQUEST = endpoints.ResourceContainer(user_name=messages.StringField(1, 
                                          required=True),
                                           email=messages.StringField(2))

MEMCACHE_AVERAGE_SCORE = 'AVERAGE_SCORE'

cardValues = ("Ace","Two","Three","Four","Five","Six","Seven","Eight",
            "Nine","Ten", "Jack","Queen","King")

@endpoints.api(name='hot_streak', version='v1')
class HotStreakApi(remote.Service):
    """Game API"""
    @endpoints.method(request_message=USER_REQUEST,
                      response_message=StringMessage,
                      path='user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """Create a User. Requires a unique username"""
        if User.query(User.name == request.user_name).get():
            raise endpoints.ConflictException(
                    'A User with that name already exists!')
        user = User(name=request.user_name, email=request.email)
        user.put()
        return StringMessage(message='User {} created!'.format(
                request.user_name))

    @endpoints.method(response_message=UserForms,
                      path='user/ranking',
                      name='get_user_rankings',
                      http_method='GET')
    def get_user_rankings(self, request):
        """Return all Users ranked by their win percentage"""
        users = User.query(User.total_games > 0).fetch()
        users = sorted(users, key=lambda x: x.avg_score, reverse=True)
        return UserForms(items=[user.to_form() for user in users])


    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='game',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        """Creates new game"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
            'A User with that name does not exist!')
        
        game = Game.new_game(user.key)
        return game.to_form('Time To Play HotStreak! You start with 10 points.')

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Return the current game state."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            msg = "The dealer has a %s" %(cardValues[game.nextcard])
            return game.to_form(msg + '. Higher or Lower? Place a bet!')
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=StringMessage,
                      path='game/{urlsafe_game_key}',
                      name='stop_game',
                      http_method='DELETE')
    def stop_game(self, request):
        """Ends a game that is currently in-progress"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game and not game.game_over:
            game.key.delete()
            return StringMessage(message='Game with key: {} deleted.'.
                                 format(request.urlsafe_game_key))
        elif game and game.game_over:
            raise endpoints.BadRequestException('Cannot delete a completed game!')
        else:
            raise endpoints.NotFoundException('That game does not exist!')

    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='make_move',
                      http_method='PUT')
    def make_move(self, request):
        """Guess Higher or Lower and place a bet"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        
        d_card = game.nextcard
        m_card = random.choice(range(1,13))
        my_guess= request.guess
        my_bet = request.bet

        if game.game_over:
          return game.to_form('Game already over!')

        # If the user is out of points. Game over.
        if game.points == 0:
          game.game_over=True
          game.history.append(("You are broke. Game over."))

          game.put()
          game.put_Scores(game.user)
          return game.to_form("You are broke. Game Over!")

        # If invalid bet, warn user and try again
        if my_bet < 0 or my_bet > game.points:
          msg = "Invalid Bet."
          msg = msg + ". You have %d" %(game.points)
          game.put()
          return game.to_form(msg + " points. How about we try that again?")

        # If incorrect gues, warn user and try again
        if (my_guess.lower() != "higher" and my_guess.lower() != "lower"):
          msg = "Oops. You entered something other than Higher or Lower."
          game.nextcard = random.choice(range(1,13))
          game.put()
          return game.to_form(msg + " How about we try that again?")

        # If the cards match, automatic win and you double your bet.
        if m_card == d_card:
          game.points += (my_bet *2)
          msg = "Your card is a %s" %(cardValues[m_card])
          msg += ". The dealer has the same card. You now have %d" %(game.points)
          game.history.append(("You had the same card as the dealer. Points: %d" 
                              %(game.points)))
          game.nextcard = random.choice(range(1,13))
          game.put()
          return game.to_form(msg + 
              " points. You doubled your bet!")

        # User guesses Higher and is correct
        elif (my_guess.lower() == "higher") and (m_card > d_card):
          game.points += my_bet
          msg = "The dealer has a %s" %(cardValues[d_card])
          msg = msg + ". Your card is a %s" %(cardValues[m_card])
          msg = msg + ". You now have %d" %(game.points)
          game.history.append(("You guessed higher and you were correct. Points: %d"
                              %(game.points)))
          game.nextcard = random.choice(range(1,13))
          game.put()
          return game.to_form(msg + " points. You Win!")

        # User guesses Lower and is correct
        elif (my_guess.lower() == "lower" and (m_card < d_card)):
          game.points += my_bet
          msg = "The dealer has a %s" %(cardValues[d_card])
          msg = msg + ". Your card is a %s" %(cardValues[m_card])
          msg = msg + ". You now have %d" %(game.points)
          game.history.append(("You guessed lower and you were correct. Points: %d"
                                %(game.points)))
          game.nextcard = random.choice(range(1,13))
          game.put()
          return game.to_form(msg + " points. You Win!")

        # User guesses incorrectly, so game over.
        else:
          msg = "The dealer has a %s" %(cardValues[d_card])
          msg = msg + ". Your card is a %s" %(cardValues[m_card])
          msg = msg + ". Your final score is %d" %(game.points)
          game.game_over=True
          game.history.append(("You were incorrect. Game over. Final Points: %d"
                                %(game.points)))

          game.put()
          game.put_Scores(game.user)
          return game.to_form(msg + " points. Game Over!")
 
    @endpoints.method(request_message=USER_REQUEST,
                      response_message=GameForms,
                      path='user/games',
                      name='get_user_games',
                      http_method='GET')
    def get_user_games(self, request):
        """Returns the active games of a specific user"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.BadRequestException('User not found!')
        
        games = Game.query(Game.user == user.key).\
            filter(Game.game_over == False)
        return GameForms(items=[game.to_form("") for game in games])

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=StringMessage,
                      path='game/{urlsafe_game_key}/history',
                      name='get_game_history',
                      http_method='GET')
    def get_game_history(self, request):
        """Returns a summary of a game's guesses."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if not game:
            raise endpoints.NotFoundException('Game not found')
        return StringMessage(message=str(game.history))

    @endpoints.method(request_message=SCORE_REQUEST,
                      response_message=ScoreForms,
                      path='scores',
                      name='get_high_scores',
                      http_method='PUT')
    def get_high_scores(self, request):
        """Return all scores ordered by total points"""
        rlen = request.num_results

        scores=Score.query().order(-Score.points)
        f_scores= scores.fetch(rlen)
        return ScoreForms(items=[score.to_form() for score in f_scores])

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=ScoreForms,
                      path='scores/user/{user_name}',
                      name='get_user_scores',
                      http_method='GET')
    def get_user_scores(self, request):
        """Returns all of an individual User's scores"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
        scores = Score.query(Score.user == user.key)
        return ScoreForms(items=[score.to_form() for score in scores])

    @endpoints.method(response_message=StringMessage,
                      path='games/average_score',
                      name='get_average_score',
                      http_method='GET')
    def get_average_score(self, request):
        """Get the cached average score"""
        return StringMessage(message=memcache.get(MEMCACHE_AVERAGE_SCORE) or "")

    @staticmethod
    def cache_average_score():
        """Populates memcache with the average score"""
        games = Game.query(Game.game_over == False).fetch()
        if games:
            count = len(games)
            total_score = sum([game.points for game in games])
            average = float(total_score)/count
            memcache.set(MEMCACHE_AVERAGE_SCORE,
                         'Your average score is {:.2f}'.format(average))

api = endpoints.api_server([HotStreakApi])