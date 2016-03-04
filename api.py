"""api.py - Create and configure the Game API exposing the resources.
This can also contain game logic. For more complex games it would be wise to
move game logic to another file. Ideally the API will be simple, concerned
primarily with communication to/from the API's users."""


import logging
import endpoints
from protorpc import remote, messages
from google.appengine.api import memcache
from google.appengine.api import taskqueue

from models import User, Game, Score
from models import StringMessage, NewGameForm, GameForm, MakeMoveForm,\
    ScoreForms
from utils import get_by_urlsafe

# Assign values to face cards
cardValues = ("Ace","Two","Three","Four","Five","Six","Seven","Eight",
            "Nine","Ten", "Jack","Queen","King")

NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
GET_GAME_REQUEST = endpoints.ResourceContainer(
        urlsafe_game_key=messages.StringField(1),)
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(
    MakeMoveForm,
    urlsafe_game_key=messages.StringField(1),)
USER_REQUEST = endpoints.ResourceContainer(user_name=messages.StringField(1),
                                           email=messages.StringField(2))

MEMCACHE_CURRENT_STREAK = 'CURRENT_STREAK'

@endpoints.api(name='HotStreak', version='v1')
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
        
        # Use a task queue to update the average attempts remaining.
        # This operation is not needed to complete the creation of a new game
        # so it is performed out of sequence.
        taskqueue.add(url='/tasks/cache_current_streak')
        return game.to_form('Time To Play HotStreak!')

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Return the current game state."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            return game.to_form('Higher or Lower?')
        else:
            raise endpoints.NotFoundException('Oops. Game not found!')

    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='make_move',
                      http_method='PUT')
    def make_move(self, request):
        """Makes a move. Returns a game state with message"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        d_card = cardValues.index(game.dealercard)
        m_card = cardValues.index(game.myCard)
        my_guess= request.guess

        StringMessage(message="The dealer has a %s" %(cardValues(d_card)))

        if game.game_over:
            return game.to_form('Game already over!')

        # If incorrect input, warn user and try again
        if (my_guess.lower() != "higher" and my_guess.lower() != "h"
          and my_guess.lower() != "lower" and my_guess.lower() != "l"):
            game.end_game(False)
            msg = "Oops. You entered something other than Higher or Lower."
            game.put()
            return game.to_form(msg + "How about we try that again?")

        # If the cards match, automatic win.
        if m_card == d_card:
            game.streak += 1
            game.end_game(False)
            msg = "Your card is a %s" %(cardValues(m_card))
            game.put()
            return game.to_form(msg + "Lucky Break! You Automatically Win!")

        # User guesses Higher and is correct
        else if (my_guess.lower() == "higher" or my_guess.lower() == "h")
            and (m_card > d.card):
            game.streak += 1
            game.end_game(False)
            msg = "Your card is a %s" %(cardValues(m_card))
            game.put()
            return game.to_form(msg + "You Win!")

        # User guesses Lower and is correct
        else if (my_guess.lower() == "lower" or my_guess.lower() == "l")
            and (m_card < d.card):
            game.streak += 1
            game.end_game(False)
            msg = "Your card is a %s" %(cardValues(m_card))
            game.put()
            return game.to_form(msg + "You Win!")

        # User guesses incorrectly, so game over.
        else
          game.end_game(True)
          msg = "Your card is a %s" %(cardValues(m_card))
          return game.to_form(msg + "So Sorry. Game Over!")
        
    @endpoints.method(response_message=ScoreForms,
                      path='scores',
                      name='get_scores',
                      http_method='GET')
    def get_scores(self, request):
        """Return all scores"""
        return ScoreForms(items=[score.to_form() for score in Score.query()])

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
                      path='games/current_streak',
                      name='get_current_streak',
                      http_method='GET')
    def get_current_streak(self, request):
        # Get the current win streak stored in the cache
        return StringMessage(message=memcache.get(MEMCACHE_CURRENT_STREAK) or '')

    @staticmethod
    def _cache_current_streak():
        """Populates memcache with the average moves remaining of Games"""
        games = Game.query(Game.game_over == False).fetch()
        if games:
          memcache.set(MEMCACHE_CURRENT_STREAK, "Current Streak: %d" %game.streak)

api = endpoints.api_server([HotStreakApi])
