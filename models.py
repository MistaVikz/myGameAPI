# Contains class definitions for all datastone entries used by HotStreak.
# Also contains updating/displaying methods.

import random
from datetime import date
from protorpc import messages
from google.appengine.ext import ndb


class User(ndb.Model):
    """User profile"""
    name = ndb.StringProperty(required=True)
    email =ndb.StringProperty()
    total_points=ndb.IntegerProperty(default=0)
    total_games = ndb.IntegerProperty(default=0)

    @property
    def avg_score(self):
        if self.total_games > 0:
            return float(self.total_points)/float(self.total_games)
        else:
            return 0

    def to_form(self):
        return UserForm(name=self.name,
                        email=self.email,
                        total_points=self.total_points,
                        total_games=self.total_games,
                        avg_score=self.avg_score)

    def update_user(self, points):
        """Update user scoring."""
        self.total_points += points
        self.total_games += 1
        self.put()

class Game(ndb.Model):
    """Game object"""
    points = ndb.IntegerProperty(required=True)
    nextcard=ndb.IntegerProperty()
    game_over = ndb.BooleanProperty(required=True, default=False)
    user = ndb.KeyProperty(required=True, kind='User')
    history = ndb.PickleProperty(required=True)

    @classmethod
    def new_game(cls, user):
        """Creates and returns a new game"""
        game = Game(user=user,
                    nextcard=random.choice(range(1,13)),
                    points=10,
                    game_over=False)
        game.history = []
        game.put()
        return game

    def to_form(self, message):
        """Returns a GameForm representation of the Game"""
        form = GameForm()
        form.urlsafe_key = self.key.urlsafe()
        form.user_name = self.user.get().name
        form.nextcard = self.nextcard
        form.points = self.points
        form.game_over = self.game_over
        form.message = message
        return form

    def put_Scores(self,user):
        self.game_over= True
        self.put()
        # Add the game to the score 'board'
        score = Score(user=self.user, date=date.today(),
                      points=self.points)
        score.put()
        user.get().update_user(self.points)

class Score(ndb.Model):
    """Score object"""
    user = ndb.KeyProperty(required=True, kind='User')
    date = ndb.DateProperty(required=True)
    points = ndb.IntegerProperty(required=True)

    def to_form(self):
        return ScoreForm(user_name=self.user.get().name, date=str(self.date),
                        points=self.points)

class GameForm(messages.Message):
    """GameForm for outbound game state information"""
    urlsafe_key = messages.StringField(1, required=True)
    points = messages.IntegerField(2)
    nextcard = messages.IntegerField(3)
    game_over = messages.BooleanField(4, required=True)
    message = messages.StringField(5, required=True)
    user_name = messages.StringField(6, required=True)

class GameForms(messages.Message):
    """Return multiple GameForms"""
    items = messages.MessageField(GameForm, 1, repeated=True)

class NewGameForm(messages.Message):
    """Used to create a new game"""
    user_name = messages.StringField(1, required=True)

class MakeMoveForm(messages.Message):
    """Used to make a move in an existing game"""
    guess = messages.StringField(1, required=True)
    bet = messages.IntegerField(2, required=True)

class ScoreRequestForm(messages.Message):
    """Used to limit the number of returned Scores"""
    num_results = messages.IntegerField(1, required=False, default=5)

class ScoreForm(messages.Message):
    """ScoreForm for outbound Score information"""
    user_name = messages.StringField(1, required=True)
    date = messages.StringField(2, required=True)
    points = messages.IntegerField(3)

class ScoreForms(messages.Message):
    """Return multiple ScoreForms"""
    items = messages.MessageField(ScoreForm, 1, repeated=True)

class UserForm(messages.Message):
    """User Form"""
    name = messages.StringField(1, required=True)
    email = messages.StringField(2)
    total_points = messages.IntegerField(3, required=True)
    total_games = messages.IntegerField(4, required=True)
    avg_score = messages.FloatField(5, required=True)

class UserForms(messages.Message):
    """Container for multiple User Forms"""
    items = messages.MessageField(UserForm, 1, repeated=True)

class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)
