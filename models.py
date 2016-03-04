"""models.py - This file contains the class definitions for the Datastore
entities used by the Game. Because these classes are also regular Python
classes they can include methods (such as 'to_form' and 'new_game')."""
# Changed to support the HotStreak game.

# To Do (if time):
# 1. Add card class to allow for suits
# 2. Calculate and Store max and average streak.

import random
from datetime import date
from protorpc import messages
from google.appengine.ext import ndb



# HotStreak only requires a name, email for user info
class User(ndb.Model):
    """User profile"""
    name = ndb.StringProperty(required=True)
    email =ndb.StringProperty()


# HotStreak game consists of a displayed card, a hidden card, the win
# streak and a gameover property
class Game(ndb.Model):
    """Game object"""
    dealerCard = ndb.StringProperty(required=True)
    myCard = distCard = ndb.StringProperty(required=True)
    streak = ndb.IntegerProperty(required=True)
    game_over = ndb.BooleanProperty(required=True, default=False)
    user = ndb.KeyProperty(required=True, kind='User')

    @classmethod
    def new_game(cls, user):
        """Creates and returns a new game"""
        game = Game(user=user,
                    dealerCard=random.choice(range(1, 13)),
                    myCard=random.choice(range(1, 13)),
                    streak=0,
                    game_over=False)
        game.put()
        return game

    def to_form(self, message):
        """Returns a GameForm representation of the Game"""
        form = GameForm()
        form.urlsafe_key = self.key.urlsafe()
        form.user_name = self.user.get().name
        form.streak = self.streak
        form.game_over = self.game_over
        form.message = message
        return form

    # If the user guesses incorrectly the game is over and the
    # score is recorded
    def end_game(self):
        self.game_over = True
        self.put()

        # Add the game to the score 'board'
        score = Score(user=self.user, date=date.today(),
                      lastStreak=self.streak)
        score.put()


class Score(ndb.Model):
    """Score object"""
    user = ndb.KeyProperty(required=True, kind='User')
    date = ndb.DateProperty(required=True)
    lastStreak = ndb.IntegerProperty(required=True)
    maxStreak = ndb.IntegerProperty(default=0)
    avgStreak = ndb.IntegerProperty(default=0)
    def to_form(self):
        return ScoreForm(user_name=self.user.get().name, date=str(self.date),
                        lastStreak=self.streak)


class GameForm(messages.Message):
    """GameForm for outbound game state information"""
    urlsafe_key = messages.StringField(1, required=True)
    streak = messages.IntegerField(2, required=True)
    game_over = messages.BooleanField(3, required=True)
    message = messages.StringField(4, required=True)
    user_name = messages.StringField(5, required=True)


class NewGameForm(messages.Message):
    """Used to create a new game"""
    user_name = messages.StringField(1, required=True)
    streak = messages.IntegerField(2)


class MakeMoveForm(messages.Message):
    # Used to make a guess in the current game
    guess = messages.StringField(1, required=True)


class ScoreForm(messages.Message):
    """ScoreForm for outbound Score information"""
    user_name = messages.StringField(1, required=True)
    date = messages.StringField(2, required=True)
    lastStreak = messages.IntegerField(3, required=True)
    maxStreak = messages.IntegerField(4)
    avgStreak = messages.IntegerField(5)


class ScoreForms(messages.Message):
    """Return multiple ScoreForms"""
    items = messages.MessageField(ScoreForm, 1, repeated=True)


class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)
