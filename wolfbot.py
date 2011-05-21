#!/usr/bin/env python
#
# IRC Bot to moderate a game of "Werewolf".
#
# Werewolf is a traditional party game, sometimes known as 'Mafia',
# with dozens of variants.  This bot is following Andrew Plotkin's rules:
# http://www.eblong.com/zarf/werewolf.html
#
# Code originally based on example bot and irc-bot class from
# Joel Rosdahl <joel@rosdahl.net>, author of included python-irclib.
#
# Several modifications by Victor "Liag" Radmark <victor@liag.se>

"""An IRC bot to moderate a game of "Werewolf".

This is an example bot that uses the SingleServerIRCBot class from
ircbot.py.  The bot enters a channel and listens for commands in
private messages and channel traffic.  Commands in channel messages
are given by prefixing the text by the bot name followed by a colon.
(Or by prefixing the command with '!', e.g. '!start'
or 'wolfbot: start')

The main commands are:

    start game -- start a new werewolf game.

    end game -- quit the current werewolf game (you must have started it)

    stats -- print information about state of game-in-progress.

"""

import sys, string, random, time
from ircbot import SingleServerIRCBot
import irclib
from irclib import nm_to_n, nm_to_h, irc_lower, parse_channel_modes
from botcommon import OutputManager

url = "https://github.com/Liag/wolfbot"

# Game config
GAME_STARTER_TIMEOUT = 70 #In seconds
DAY_LENGTH = 120 #Voting period is half this
NIGHT_LENGTH = 60
MIN_USERS = 5
WOLF_TRESHOLD_MULTI = 8 #How many players per wolf (max three wolves)
# Chances for each role on first role roll in percent
# Should add up to 100%
SEER_CHANCE = 75
MYSTIC_CHANCE = 9
ANGEL_CHANCE = 6
NINJA_CHANCE = 4
CUPID_CHANCE = 3
ELDER_CHANCE = 2
WATCHMAN_CHANCE = 1
"""SEER_CHANCE = 0
MYSTIC_CHANCE = 100
ANGEL_CHANCE = 0
NINJA_CHANCE = 0
CUPID_CHANCE = 0
ELDER_CHANCE = 0
WATCHMAN_CHANCE = 0"""


#---------------------------------------------------------------------
# General texts for narrating the game.  Change these global strings
# however you wish, without having to muck with the core logic!

# Printed when a game first starts:

new_game_texts = \
["This is a game of paranoia and psychological intrigue.  Everyone\
 in this group appears to be a common villager, but several of\
 you are 'special'.  One or more of you are actually evil werewolves, seeking\
 to kill everyone while concealing your identity.",

 "Depending on the number of players, there are also additional villager roles\
 like the seer and the mystic.",

 "As a community, your group objective is to weed out the werewolves\
 and lynch them before you're all killed in your sleep."]

# Printed when informing players of their initial roles:

wolf_intro_text = \
"You are a \x034werewolf\x0f\x02.  You want to kill everyone while they sleep. \
Whatever happens, keep your identity secret.  Act natural!"

seer_intro_text = \
"You're a villager, but also a \x034seer\x0f\x02.  Later on, you'll get chances to \
learn whether someone is or isn't a werewolf.  Keep your identity \
secret, or the werewolves may kill you!"

mystic_intro_text = \
"You're a villager, but also a \x034mystic\x0f\x02.  Later on, you'll get chances to \
protect someone from harm using your powers. Keep your identity \
secret, or the werewolves may kill you!"

angel_intro_text = \
"You're a villager, but also an \x034angel\x0f\x02.  You are immune against the wolves' attacks!"

ninja_intro_text = \
"You're a villager, but also a \x034ninja\x0f\x02.  You have a single chance to \
assassinate someone during the course of the game. Keep your identity \
secret, or the werewolves may kill you!"

cupid_intro_text = \
"You're a villager, but also a \x034cupid\x0f\x02.  During the first night, you can \
make two people fall in love with each other. Choose wisely!"

elder_intro_text = \
"You're a villager, but also the revered \x034village elder\x0f\x02.  During the  \
days, you can vote twice, once with a secret vote. Keep your identity \
secret, or the werewolves may kill you!"

watchman_intro_text = \
"You're a villager, but also a \x034watchman\x0f\x02.  Later on, you will be notified \
of what has transpired if nobody died during the night. Keep your identity \
secret, or the werewolves may kill you!"

villager_intro_text = \
"You're an ordinary villager."


# Printed when night begins:

night_game_texts = \
["Darkness falls:  it is \x034night\x0f\x02.",
 "The village enters a restless slumber, each inhabitant fearing that they are next...",
 "Who knows what horrors the dark will bring?"]

# Printed when wolves and villager get nighttime instructions:

night_seer_texts = \
["In your dreams, you have the ability to see whether a certain person\
  is or is not a werewolf.",

 "You can use this power now: please type 'see <nickname>' (as a\
 private message to me) to learn about one living player's true\
 identity."]
 
night_mystic_texts = \
["With you bullshit powers, you have the ability to guard someone\
 against the werewolves, including yourself.",
 "Please type 'guard <nickname>' (as a private message to me)\
 to protect this person."]

night_angel_texts = \
["You are immune to the wolves' attacks! You can rest easy tonight. Just beware of being lynched tomorrow..."]
 
night_ninja_texts = \
["As the others are asleep, you have a single chance to sneak in and assassinate someone.",
 "Please type 'assassinate <nickname>' (as a private message to me)\
  to carry this out.",
 "But remember: you can only use this power once per game."]

night_cupid_texts = \
["As it is the first night, you have the power to make two people fall \
 in love with each other.",
 "Please type 'lovers <nickname1> <nickname>' (as a private message to me)\
  to fire your arrows.",
 "Remember that this is your only chance! If you do not act now, your \
  powers will still be forfeit for the rest of the game."]

night_watchman_texts = \
["As the watchman, you keep a firm vigil on the villagers. If a failed attack takes place in the night, you are sure to see the signs."]

night_werewolf_texts = \
["As the villagers sleep, you must now decide whom you want to kill.",
 "You and the other werewolves (if there are any and they are alive) should discuss (privately) and choose a victim.",
 "Please type 'kill <nickname>' (as a private message to me)."]


# Printed when day begins.

morning_game_texts = \
["Paranoia runs through the village!  Who is a werewolf in disguise?",
 "The villagers will gather to vote upon this matter in a short while."]
  
day_game_texts = \
["The villagers are all gathered to vote.",
"The villagers may now decide to lynch one player. If you do not vote two nights in a row, the powers of good will cast you down!",
 "When each player is ready, send me the command:  'vote <nickname>',",
 "and I will lynch the player who gets the most votes!",
 "Remember:  votes cannot be changed after you have voted."]
 
day_elder_texts = \
["As the village elder, you have a secret vote at your disposal each voting session.",
 "Please type 'secretvote <nickname>' (as a private message to me) to use this extra vote."]




#---------------------------------------------------------------------
# Actual code.
#
# WolfBot subclasses a basic 'bot' class, which subclasses a basic
# IRC-client class, which uses the python-irc library.  Thanks to Joel
# Rosdahl for the great framework!

IRC_BOLD = "\x02"

class WolfBot(SingleServerIRCBot):
  GAMESTATE_NONE, GAMESTATE_STARTING, GAMESTATE_RUNNING, GAMESTATE_PAUSED  = range(4)
  def __init__(self, channel, nickname, nickpass, server, port=6667,
      debug=False):
    SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
    self.channel = channel
    # self.nickname is the nickname we _want_. The nickname we actually
    # have at any particular time is c.get_nickname().
    self.nickname = nickname
    self.nickpass = nickpass
    self.debug = debug
    self.moderation = True
    self._reset_gamedata()
    self.queue = OutputManager(self.connection)
    self.queue.start()
    try:
      self.start()
    except KeyboardInterrupt:
      self.connection.quit("Ctrl-C at console")
      print "Quit IRC."
    except Exception, e:
      self.connection.quit("%s: %s" % (e.__class__.__name__, e.args))
      raise


  _uninteresting_events = {
    'all_raw_messages': None,
    'yourhost': None,
    'created': None,
    'myinfo': None,
    'featurelist': None,
    'luserclient': None,
    'luserop': None,
    'luserchannels': None,
    'luserme': None,
    'n_local': None,
    'n_global': None,
    'luserconns': None,
    'motdstart': None,
    'motd': None,
    'endofmotd': None,
    'topic': None,
    'topicinfo': None,
    'ping': None,
    }
  def _dispatcher(self, c, e):
    if self.debug:
      eventtype = e.eventtype()
      if eventtype not in self._uninteresting_events:
        source = e.source()
        if source is not None:
          source = nm_to_n(source)
        else:
          source = ''
        print "E: %s (%s->%s) %s" % (eventtype, source, e.target(),
            e.arguments())
    SingleServerIRCBot._dispatcher(self, c, e)
  
  def process_timers(self):
    #Process all existing timers and check if their functions need to executed
    
    curTime = time.time()
    
    if self.gamestate == self.GAMESTATE_STARTING:
      elapsed = int(curTime - self.game_start_timer)
      if self.old_elapsed != elapsed:
        if self.game_start_timer != -1:
          if elapsed == GAME_STARTER_TIMEOUT:
            self.say_public("The required startup time has now passed.")
            self.say_public("Anyone can now start the game with !start")
            
          #print "elapsed: " + str(elapsed) + ", elapsed mod 10: " + str(elapsed % 10)
          if elapsed % 10 == 0:
            players = self.game_starter
            for player in self.live_players:
              if player is not self.game_starter:
                players += ", " + player
            self.say_public("Players who have currently joined: %s" % players)
      self.old_elapsed = elapsed
                  
    if self.gamestate == self.GAMESTATE_RUNNING:
      if self.time == "night":
        elapsed = int(curTime - self.night_timer)
        if self.old_elapsed != elapsed:
          if self.check_night_done():
            self.day()
        self.old_elapsed = elapsed
      elif self.time == "day":
        elapsed = int(curTime - self.day_timer)
        if self.old_elapsed != elapsed:
          if self.check_day_done(elapsed):
            victims = self.check_for_votes()
            if not victims:
              self.print_tally()
              self.night()
              return
            elif len(victims) == 1:
              victim = victims[0]
            else:
              victim = victims[random.randrange(len(victims))]
        
            self.say_public(("The villagers have voted to lynch %s!! "
                             "Mob violence ensues.  This player is now \x034dead\x0f\x02." % victim))
            if not self.kill_player(victim):
            # Day is done;  flip bot back into night-mode.
              self.night()
          elif elapsed == DAY_LENGTH / 2:
            for text in day_game_texts:
              self.say_public(text)
          self.old_elapsed = elapsed
            
      
                          
          
  def process_forever(self):
    """Run an infinite loop, processing data from connections.

    This method repeatedly calls process_once.

    Arguments:

        timeout -- Parameter to pass to process_once.
    """
    while 1:
        self.process_timers()
        self.ircobj.process_once(0.2)
    
  def start(self):
    """Start the bot."""
    self._connect()
    self.process_forever()
  
  def on_nicknameinuse(self, c, e):
    c.nick(c.get_nickname() + "_")

  def _renameUser(self, old, new):
    for list in (self.live_players, self.dead_players, self.wolves,
        self.villagers, self.originalwolves):
      if old in list:
        list.append(new)
        list.remove(old)
    for map in (self.wolf_votes, self.villager_votes, self.tally):
      if map.has_key(new):
        map[new] = map[old]
        del map[old]
    for map in (self.wolf_votes, self.villager_votes):
      for k, v in map.items():
        if v == old:
          map[k] = new
    for var in ('game_starter', 'seer', 'seer_target', 'wolf_target'):
      if getattr(self, var) == old:
        setattr(self, var, new)

  def _removeUser(self, nick):
    if nick == self.game_starter:
      self.game_starter = None
    if nick in self.live_players:
      self.say_public("%s disappeared in some sort of strange wormhole." % nick)
      self.live_players.remove(nick)
      if self.gamestate == self.GAMESTATE_STARTING:
        # No more to do
        return
      self.dead_players.append(nick)
      if nick in self.wolves:
        self.wolves.remove(nick)
        self.say_public("The only relic left by %s was a copious amount of lupine fur.  "
	    "Now we know why %s always growled whenever a cat was nearby." % (nick,nick))
      if nick in self.villagers:
        self.villagers.remove(nick)
        self.say_public("%s had a boring position in the game, that of a villager.  "
            "Hopefully death will be more interesting." % nick)
      if self.seer is not None and nick == self.seer:
        self.say_public("%s was a seer.  Apollo is mad that all his seers "
            "get destroyed by timespace anomalies." % nick)
      if self.seer is not None and nick == self.seer_target:
        self.say_private(self.seer, "Due to %s's unexpected erasure from reality, "
            "you may See once again this night." % nick)
        self.seer_target = None
      if self.mystic is not None and nick == self.mystic:
        self.say_public("%s was a mystic. He won't be doing any protecting soon." % nick)
      if self.mystic is not None and nick == self.mystic_target:
        self.say_private(self.mystic, "Due to %s's unexpected erasure from reality, "
                         "you may protect someone else this night." % nick)
        self.mystic_target = None
      if self.angel is not None and nick == self.angel:
        self.say_public("%s was an angel. God's wrath will surely be mighty." % nick)
      if self.ninja is not None and nick == self.ninja:
        self.say_public("%s was a ninja. He hid in a disconnection or something, I guess." % nick)
        ninja_target = None
      if self.ninja is not None and nick == self.ninja_target and self.time == "night":
        self.say_private(self.ninja, "Due to %s's unexpected erasure from reality, "
                         "you may assassinate someone else this night." % nick)
      if self.cupid is not None and nick == self.cupid:
        self.say_public("%s was a cupid. The subjects of his work surely won't mourn him." % nick)
      if self.lovers and (nick == self.lovers[0] or nick == self.lovers[1]):
        self.check_lovers(nick)
      if self.village_elder is not None and nick == self.village_elder:
        self.say_public("%s was the village elder. The villagers are sorry for his lots." % nick)
      if self.watchman is not None and nick == self.watchman:
        self.say_public("%s was a watchman. Perhaps he should have been more watchful!" % nick)
      if nick == self.wolf_target:
        for wolf in self.wolves:
          self.say_private("Due to %s's unexpected erasure from reality, "
              "you can choose someone else to kill tonight." % nick, wolf)
        self.wolf_target = None
      for map in (self.wolf_votes, self.villager_votes, self.tally):
        if map.has_key(nick):
          del map[nick]
      for map in (self.wolf_votes, self.villager_votes):
        for k, v in map.items():
          if v == nick:
            del map[k]
      self.check_game_over()

  def on_join(self, c, e):
    nick = nm_to_n(e.source())
    if nick == c.get_nickname():
      chan = e.target()
      self.connection.mode(self.channel, '')

  def on_channelmodeis(self, c, e):
    c._handle_event(
        irclib.Event("mode", e.source(), e.arguments()[0], [e.arguments()[1]]))
    self.fix_modes()

  def on_mode(self, c, e):
    if e.target() == self.channel:
      try:
        if parse_channel_modes(e.arguments()[0]) == ['+','o',c.get_nickname()]:
          self.fix_modes()
      except IndexError:
        pass
      

  def on_quit(self, c, e):
    source = nm_to_n(e.source())
    self._removeUser(source)
    if source == self.nickname:
      # Our desired nick just quit - take the nick back
      c.nick(self.nickname)

  def on_nick(self, c, e):
    self._renameUser(nm_to_n(e.source()), e.target())


  def on_welcome(self, c, e):
    c.join(self.channel)
    if c.get_nickname() != self.nickname:
      # Reclaim our desired nickname
      c.privmsg('nickserv', 'ghost %s %s' % (self.nickname, self.nickpass))
    self.queue.send('identify %s' % self.nickpass, 'nickserv')


  def fix_modes(self, night = False):
    chobj = self.channels[self.channel]
    is_moderated = chobj.is_moderated()
    should_be_moderated = (self.gamestate == self.GAMESTATE_RUNNING
        and self.moderation)
    if is_moderated and not should_be_moderated:
      self.connection.mode(self.channel, '-m')
    elif not is_moderated and should_be_moderated:
      self.connection.mode(self.channel, '+m')

    voice = []
    devoice = []
    for user in chobj.users():
      is_live = user in self.live_players
      is_voiced = chobj.is_voiced(user)
      if night:
        if is_live:
          devoice.append(user)
      else:
        if is_live and not is_voiced:
          voice.append(user)
        elif not is_live and is_voiced:
          devoice.append(user)
    if not night: 
      self.multimode('+v', voice)
    self.multimode('-v', devoice)


  def multimode(self, mode, nicks):
    max_batch = 4 # FIXME: Get this from features message
    assert len(mode) == 2
    assert mode[0] in ('-', '+')
    while nicks:
      batch_len = len(nicks)
      if batch_len > max_batch:
        batch_len = max_batch
      tokens = [mode[0] + (mode[1]*batch_len)]
      while batch_len:
        tokens.append(nicks.pop(0))
        batch_len -= 1
      self.connection.mode(self.channel, ' '.join(tokens))


  def on_privnotice(self, c, e):
    source = e.source()
    if source and irc_lower(nm_to_n(source)) == 'nickserv':
      if e.arguments()[0].find('IDENTIFY') >= 0:
        # Received request to identify
        if self.nickpass and self.nickname == c.get_nickname():
          self.queue.send('identify %s' % self.nickpass, 'nickserv')

  def on_privmsg(self, c, e):
    self.do_command(e, e.arguments()[0])


  def on_part(self, c, e):
    self._removeUser(nm_to_n(e.source()))

  def on_kick(self, c, e):
    self._removeUser(nm_to_n(e.arguments()[0]))

  def on_pubmsg(self, c, e):
    s = e.arguments()[0]
    a = string.split(s, ":", 1)
    if len(a) > 1 and irc_lower(a[0]) == irc_lower(c.get_nickname()):
      self.do_command(e, string.strip(a[1]))
    if s[0]=='!' and (len(s) > 1) and s[1]!='!':
      self.do_command(e, string.strip(s[1:]))

  def _reset_gamedata(self):
    self.old_elapsed = 0
    self.game_start_timer = -1
    self.night_timer = -1
    self.day_timer = -1
    self.gamestate = self.GAMESTATE_NONE
    self.time = None
    self.game_starter = None
    self.live_players = []
    self.dead_players = []
    self.wolves = []
    self.villagers = []
    self.lovers = []
    self.seer = None
    self.mystic = None
    self.angel = None
    self.ninja = None
    self.cupid = None
    self.village_elder = None
    self.elder_voted = False
    self.watchman = None
    self.originalwolves = []
    # Night round variables
    self.seer_target = None
    self.mystic_target = None
    self.ninja_target = None
    self.wolf_target = None
    self.wolf_votes = {}
    # Day round variables
    self.villager_votes = {}
    self.tally = {}


  def say_public(self, text):
    "Print TEXT into public channel, for all to see."

    self.queue.send(IRC_BOLD+text, self.channel)


  def say_private(self, nick, text):
    "Send private message of TEXT to NICK."
    self.queue.send(IRC_BOLD+text,nick)


  def reply(self, e, text):
    "Send TEXT to public channel or as private msg, in reply to event E."
    if e.eventtype() == "pubmsg":
      self.say_public("%s: %s" % (nm_to_n(e.source()), text))
    else:
      self.say_private(nm_to_n(e.source()), text)


  def start_game(self, game_starter):
    "Initialize a werewolf game -- assign roles and notify all players."
    chname, chobj = self.channels.items()[0]

    if self.gamestate == self.GAMESTATE_RUNNING:
      self.say_public("A game started by %s is in progress; "
          "that person must end it." % self.game_starter)
      return

    if self.gamestate == self.GAMESTATE_NONE:
      self._reset_gamedata()
      self.gamestate = self.GAMESTATE_STARTING
      self.game_starter = game_starter
      self.live_players.append(game_starter)
      self.say_public("A new game has been started by %s; "
          "say '!join' to join the game."
          % self.game_starter)
      self.say_public("%s: Say '!start' when everyone has joined."
          % self.game_starter)
      self.fix_modes()
      self.game_start_timer = time.time()
      return

    if self.gamestate == self.GAMESTATE_STARTING:
      if ((time.time() - self.game_start_timer) < GAME_STARTER_TIMEOUT) and self.game_starter and game_starter != self.game_starter:
        self.say_public("Game startup was begun by %s; "
            "that person must finish starting it." % self.game_starter)
        return
      elif self.game_starter is None:
        self.game_starter = game_starter

      if len(self.live_players) < MIN_USERS:
        self.say_public("Sorry, to start a game, there must be " + \
                        "at least active %d players."%(MIN_USERS))
        self.say_public(("I count only %d active players right now: %s."
          % (len(self.live_players), self.live_players)))

      else:
        # Randomly select an appropriate amount of wolves and special roles.  Everyone else is a villager.
        users = self.live_players[:]
        self.say_public("A new game has begun! Please wait, assigning roles...")
        #Set number of village roles based on amount of players
        if len(users) < 6: 
          roles = 1
        elif len(users) < 7:
          roles = 2
        elif len(users) < 9:
          roles = 3
        elif len(users) < 10:
          roles = 4
        elif len(users) < 12:
          roles = 5
        elif len(users) < 13:
          roles = 6
        else:
          roles = 7
        
        self.wolves.append(users.pop(random.randrange(len(users))))
		
        if len(self.live_players) > WOLF_TRESHOLD_MULTI:
          self.wolves.append(users.pop(random.randrange(len(users))))
		  
          if len(self.live_players) > (WOLF_TRESHOLD_MULTI * 2):
            self.wolves.append(users.pop(random.randrange(len(users))))
            self.say_public("There are %s or more players so there are three werewolves." %((WOLF_TRESHOLD_MULTI * 2) + 1))
          else:
            self.say_public("There are %s or more players so there are two werewolves." %(WOLF_TRESHOLD_MULTI + 1))
        else:
		  self.say_public("There are less than %s players, so there is only one werewolf." %(WOLF_TRESHOLD_MULTI + 1))
			
        self.originalwolves = self.wolves[:]
        
        #Generate roles
        for i in range(roles):
          role = 0
          while role == 0:
            role = random.randint(1, 100)
            if role > (100 - WATCHMAN_CHANCE):
              if self.watchman != None:
                role = 0
              else:
                self.watchman = users.pop(random.randrange(len(users)))
            elif role > (CUPID_CHANCE + ANGEL_CHANCE + NINJA_CHANCE + MYSTIC_CHANCE + SEER_CHANCE):
              if self.village_elder != None:
                role = 0
              else:
                self.village_elder = users.pop(random.randrange(len(users)))
            elif role > (ANGEL_CHANCE + NINJA_CHANCE + MYSTIC_CHANCE + SEER_CHANCE):
              if self.cupid != None:
                role = 0
              else:
                self.cupid = users.pop(random.randrange(len(users)))
            elif role > (ANGEL_CHANCE + MYSTIC_CHANCE + SEER_CHANCE):
              if self.ninja != None:
                role = 0
              else:
                self.ninja = users.pop(random.randrange(len(users)))
            elif role > (MYSTIC_CHANCE + SEER_CHANCE):
              if self.angel != None:
                role = 0
              else:
                self.angel = users.pop(random.randrange(len(users)))
            elif role > SEER_CHANCE:
              if self.mystic != None:
                role = 0
              else:
                self.mystic = users.pop(random.randrange(len(users)))
            else:
              if self.seer != None:
                role = 0
              else:
                self.seer = users.pop(random.randrange(len(users)))
              
        for user in users:
          self.villagers.append(user)

        # Private message each user, tell them their role.
        if self.seer != None:
          self.say_private(self.seer, seer_intro_text)
        if self.mystic != None:
          self.say_private(self.mystic, mystic_intro_text)
        if self.angel != None:
          self.say_private(self.angel, angel_intro_text)
        if self.ninja != None:
          self.say_private(self.ninja, ninja_intro_text)
        if self.cupid != None:
          self.say_private(self.cupid, cupid_intro_text)
        if self.village_elder != None:
          self.say_private(self.village_elder, elder_intro_text)
        if self.watchman != None:
          self.say_private(self.watchman, watchman_intro_text)
          
        for wolf in self.wolves:
          self.say_private(wolf, wolf_intro_text)
        for villager in self.villagers:
          self.say_private(villager, villager_intro_text)

        if self.debug:
          print "SEER: %s, WOLVES: %s" % (self.seer, self.wolves)

        for text in new_game_texts:
          self.say_public(text)
        self.gamestate = self.GAMESTATE_RUNNING

        self.fix_modes()
        
        self.first_night = True
        # Start game by putting bot into "night" mode.
        self.night()


  def end_game(self, game_ender):
    "Quit a game in progress."

    if self.gamestate == self.GAMESTATE_NONE:
      self.say_public(\
               "No game is in progress.  Use 'start' to begin a game.")
    elif self.game_starter and game_ender != self.game_starter:
      self.say_public(\
        ("Sorry, only the starter of the game (%s) may end it." %\
         self.game_starter))
    else:
      self.say_public("The game has ended.")
      if self.gamestate == self.GAMESTATE_RUNNING:
        self.reveal_all_identities()
      self._reset_gamedata()
      self.gamestate = self.GAMESTATE_NONE
      self.fix_modes()


  def reveal_all_identities(self):
    "Print everyone's identities."
    
    self.say_public("*** Player roles:")
    
    if len(self.originalwolves) == 3:
      self.say_public(("*** Wolves: %s, %s and %s" % (self.originalwolves[0], self.originalwolves[1], self.originalwolves[2])))
    if len(self.originalwolves) == 2:
      self.say_public(("*** Wolves: %s and %s" % (self.originalwolves[0], self.originalwolves[1])))
    else:
      self.say_public(("*** Wolf: %s" % (self.originalwolves[0])))
    
    if self.seer != None:
      self.say_public(("*** Seer: %s" % self.seer))
    if self.mystic != None:
      self.say_public(("*** Mystic: %s" % self.mystic))
    if self.angel != None:
      self.say_public(("*** Angel: %s" % self.angel))
    if self.ninja != None:
      self.say_public(("*** Ninja: %s" % self.ninja))
    if self.cupid != None:
      self.say_public(("*** Cupid: %s" % self.cupid))
    if self.village_elder != None:
      self.say_public(("*** Village elder: %s" % self.village_elder))
    if self.watchman != None:
      self.say_public(("*** Watchman: %s" % self.watchman))
    
    self.say_public("Everyone else was a normal villager.")
    
  def check_game_over(self):
    """End the game if either villagers or werewolves have won.
    Return 1 if game is over, 0 otherwise."""

    # If all wolves are dead, the villagers win.
    if len(self.wolves) == 0:
      self.say_public("The wolves are dead!  The \x034villagers\x0f\x02 have \x034won\x0f.")
      self.end_game(self.game_starter)
      return 1

    # If the number of non-wolves is the same as the number of wolves,
    # then the wolves win.
    if (len(self.live_players) - len(self.wolves)) == len(self.wolves):
      lover_pos = check_wolf_lovers()
      if check_wolf_lovers():
        if len(self.wolves) == 1:
          self.say_public("Everyone except the lovers are dead! The \x034lovers\x0f\x02 have \x034won\x0f.")
          self.end_game(self.game_starter)
        else:
          self.say_public("There are now an equal number of villagers and werewolves.")
          msg = "The werewolves have no need to hide anymore; "
          msg = msg + "They attack the remaining villagers. "
          msg = msg + "Amongst the villagers who were killed, " + self.lovers[lover_pos[0]] + "finds their dead lover " + self.lovers[lover_pos[1]] + "."
          msg = msg + "In shock and grief, " + self.lovers[lover_pos[0]] + " commits suicide."
          msg = msg + "The \x034werewolves\x0f\x02 have \x034won\x0f."
          self.say_public(msg)
      else:
        self.say_public(\
          "There are now an equal number of villagers and werewolves.")
        msg = "The werewolves have no need to hide anymore; "
        msg = msg + "They attack the remaining villagers. "
        msg = msg + "The \x034werewolves\x0f\x02 have \x034won\x0f."
        self.say_public(msg)
        
      self.end_game(self.game_starter)
      return 1
      
    return 0
    
  def check_wolf_lovers(self):
    """Check if the lovers are a wolf and a villager.
    Returns the positions of the lovers or an empty list if not """
    lover_pos = []
    if self.lovers and (self.lovers[0] in self.live_players and self.lovers[1] in self.live_players):
      if (self.lovers[0] in self.wolves) and not (self.lovers[1] in self.wolves):
        lover_pos[0] = 0
        lover_pos[1] = 1
        return lover_pos
      elif (not self.lovers[0] in self.wolves) and (self.lovers[1] in self.wolves):
        lover_pos[0] = 1
        lover_pos[1] = 0
        return lover_pos
    return -1


  def check_night_done(self, elapsed = 0):
    "Check if nighttime is over.  Return 1 if night is done, 0 otherwise."
    
    if (elapsed > NIGHT_LENGTH) or (int(time.time() - self.night_timer) > NIGHT_LENGTH):
      return 1
    # Is the seer done seeing?
    if self.seer is None or self.seer not in self.live_players:
      seer_done = 1
    else:
      if self.seer_target is None:
        seer_done = 0
      else:
        seer_done = 1
    
    # Is the mystic done guarding
    if self.mystic is None or self.seer not in self.live_players:
      mystic_done = 1
    else:
      if self.mystic_target is None:
        mystic_done = 0
      else:
        mystic_done = 1
    

    if (self.wolf_target is not None) and seer_done and mystic_done:
      return 1
    else:
      return 0
  
  def check_day_done(self, elapsed):
    "Check if daytime is over. Return 1 if day is done, 0 otherwise."
    
    if elapsed > DAY_LENGTH:
      return 1

  def night(self):
    "Declare a NIGHT episode of gameplay."

    chname, chobj = self.channels.items()[0]

    self.time = "night"
    self.night_timer = time.time()

    # Clear any daytime variables
    self.villager_votes = {}
    self.tally = {}

    # Declare nighttime.
    self.print_alive()
    for text in night_game_texts:
      self.say_public(text)

    # Give private instructions to wolves and seer.
    if self.seer is not None and self.seer in self.live_players:
      for text in night_seer_texts:
        self.say_private(self.seer, text)
    if self.mystic is not None and self.mystic in self.live_players:
      for text in night_mystic_texts:
        self.say_private(self.mystic, text)
    if self.angel is not None and self.angel in self.live_players:
      for text in night_angel_texts:
        self.say_private(self.angel, text)
    if self.ninja is not None and self.ninja in self.live_players and self.ninja_target is not None:
      for text in night_ninja_texts:
        self.say_private(self.ninja, text)
    if self.cupid is not None and self.cupid in self.live_players and self.first_night is True:
      for text in night_cupid_texts:
        self.say_private(self.cupid, text)
    if self.watchman is not None and self.watchman in self.live_players:
      for text in night_watchman_texts:
        self.say_private(self.seer, text)
    for text in night_werewolf_texts:
      for wolf in self.wolves:
        self.say_private(wolf, text)
    if len(self.wolves) == 3:
      self.say_private(self.wolves[0],\
                       ("The other werewolves are %s and %s.  Confer privately."\
                        % (self.wolves[1], self.wolves[2])))
      self.say_private(self.wolves[1],\
                       ("The other werewolves are %s and %s.  Confer privately."\
                        % (self.wolves[0], self.wolves[2])))
      self.say_private(self.wolves[2],\
                       ("The other werewolves are %s and %s.  Confer privately."\
                        % (self.wolves[0], self.wolves[1])))
    elif len(self.wolves) == 2:
      self.say_private(self.wolves[0],\
                       ("The other werewolf is %s.  Confer privately."\
                        % self.wolves[1]))
      self.say_private(self.wolves[1],\
                       ("The other werewolf is %s.  Confer privately."\
                        % self.wolves[0]))
    
    self.fix_modes(True)
    # ... bot is now in 'night' mode;  goes back to doing nothing but
    # waiting for commands.


  def day(self):
    "Declare a DAY episode of gameplay."
    
    if self.first_night is True:
      self.first_night = False
    
    self.day_timer = time.time()
    self.time = "day"
    
    # Discover dead bodies if someone has been killed during the night, depending on the actions of 
    self.say_public("\x034Day\x0f\x02 breaks!  Sunlight pierces the sky.")
    
    if self.seer_target is not None:
      role = ""
      if self.seer_target == self.mystic:
        role = "the mystic."
      elif self.seer_target == self.angel:
        role = "the angel."
      elif self.seer_target == self.ninja:
        role = "the ninja."
      elif self.seer_target == self.cupid:
        role = "the cupid."
      elif self.seer_target == self.village_elder:
        role = "the village elder."
      elif self.seer_target == self.watchman:
        role = "the watchman."
      elif self.seer_target in self.wolves:
        role = "a werewolf!"
      else:
        role = "a villager."
      self.say_private(self.seer, "Your dreams told you that %s is %s" % (self.seer_target, role))
      
    assassinated = False
    if self.ninja_target in self.live_players:
      assassinated = True
    
    if ((self.wolf_target == self.mystic_target) or (self.wolf_target == self.angel) or (self.wolf_target == None)):
      if assassinated is False:
        self.say_public(("The night seems to have transpired peacefully."))
      else:
        self.say_public("The village awakes in horror...")
        self.say_public("to find the body of \x034%s\x0f\x02, killed silently in their sleep!" % self.ninja_target)
        
      if self.watchman is not None:
        if self.wolf_target is None:
          self.say_private(self.watchman, "The werewolves didn't target anyone last night.")
        else:
          self.say_private(self.watchman, "The werewolves tried to kill %s last night, but failed." % self.wolf_target)
      
      if assassinated is True:
        if self.kill_player(self.ninja_target):
          return
    else:
      self.say_public("The village awakes in horror...")
      #If the target hasn't been protected in some way and the ninja hasn't assassinated the same target
      if (self.wolf_target is not self.mystic_target) or (self.wolf_target is not self.angel) or (self.wolf_target is not None):
        if (assassinated is True and self.ninja_target is not self.wolf_target) or (assassinated is False):
          self.say_public(("to find the mutilated body of \x034%s\x0f\x02!!"\
                           % self.wolf_target))
          if assassinated is True:
            self.say_public(("They also find the body of \x034%s\x0f\x02, who mysteriously" + \
                             "seems to have died without any noticeable wounds." % self.ninja_target))
        
      if assassinated is True:
        if self.kill_player(self.ninja_target):
          return
            
      if (self.wolf_target is not self.mystic_target) or (self.wolf_target is not self.angel) or (self.wolf_target is not None):
        if (assassinated is True and self.ninja_target != self.wolf_target) or (assassinated is False):
          if self.kill_player(self.wolf_target):
            return
        
    # Clear all the nighttime variables:
    self.seer_target = None
    self.mystic_target = None
    self.wolf_target = None
    self.wolf_votes = {}

    # Give daytime instructions.
    self.print_alive()
    for text in morning_game_texts:
      self.say_public(text)
    if self.village_elder is not None and self.village_elder in self.live_players:
      for text in day_elder_texts:
        say_private(self.village_elder, text)
    
    self.fix_modes()
    # ... bot is now in 'day' mode;  goes back to doing nothing but
    # waiting for commands.



  def see(self, e, who):
    "Allow a seer to 'see' somebody."
	
    if self.gamestate != self.GAMESTATE_RUNNING:
      self.reply(e, "No game is in progress.")
      return
      
    if who == nm_to_n(e.source()).strip("&"):
      self.reply(e, "You cannot see yourself.")
      return
    
    if self.time != "night":
      self.reply(e, "Are you a seer?  In any case, it's not nighttime.")
    else:
      if self.seer is None or nm_to_n(e.source()) != self.seer:
        self.reply(e, "Huh?")
      else:
        if who not in self.live_players:
          self.reply(e, "That player either doesn't exist, or is dead.")
        else:
          if self.seer_target is not None:
            self.reply(e, "You've already had your vision for tonight.")
          else:
            self.seer_target = who
            
            self.reply(e, "You have decided to see if %s really are what they seem to be." % self.seer_target)
            if self.check_night_done():
              self.day()
    
  def guard(self, e, who):
    "Allow a mystic to protect someone."
    
    if self.gamestate != self.GAMESTATE_RUNNING:
      self.reply(e, "No game is in progress.")
      return
      
    if self.time != "night":
      self.reply(e, "Are you a mystic? In any case, it's not nighttime.")
    else:
      if self.mystic is None or nm_to_n(e.source()) != self.mystic:
        self.reply(e, "Huh?")
      else:
        if who not in self.live_players:
          self.reply(e, "That player either doesn't exist, or is dead.")
        else:
          if self.mystic_target is not None:
            self.reply(e, "You've already protected somebody tonight.")
          else:
            self.mystic_target = who
            
            self.reply(e, "The gods will surely see to it that nothing happens " + \
                          "to %s tonight." % who)
            if self.check_night_done():
              self.day()

  def assassinate(self, e, who):
    "Allow a ninja to assassinate somebody."
    
    if self.gamestate != self.GAMESTATE_RUNNING:
      self.reply(e, "No game is in progress.")
      return
      
    if who == nm_to_n(e.source()).strip("&"):
      self.reply(e, "You cannot assassinate yourself.")
      return
	  
    if self.time != "night":
      self.reply(e, "Are you a ninja?  In any case, it's not nighttime.")
    else:
      if self.ninja is None or nm_to_n(e.source()) != self.ninja:
        self.reply(e, "Huh?")
      else:
        if who not in self.live_players:
          self.reply(e, "That player either doesn't exist, or is dead.")
        else:
          if self.ninja_target is not None:
            self.reply(e, "You've already assassinated somebody this game.")
          else:
            self.ninja_target = who
            
            self.reply(e, "You carry out the assassination silently.")
            self.reply(e, "No one else noticed anything.")
            
            if self.check_night_done():
              self.day()
              
  def lover(self, e, who1, who2):
    "Allow a cupid to lover two players once per game."
    
    if self.gamestate != self.GAMESTATE_RUNNING:
      self.reply(e, "No game is in progress.")
      return
    
    if self.time != "night":
      self.reply(e, "Are you a cupid? In any case, it's not nighttime.")
    else:
      if self.cupid is None or nm_to_n(e.source()) != self.cupid:
        self.reply(e, "Huh?")
      else:
        if who1 not in self.live_players or who2 not in self.live_players:
          self.reply(e, "One or both of the players you are trying to lover " + \
                        "are either nonexistant or dead.")
        else:
          if self.lovers:
            self.reply(e, "You're out of arrows for this game.")
          else:
            self.lovers[0] = who1
            self.lovers[1] = who2
            
            self.reply(e, "Your arrows strike! %s and %s are now lovers." % who1, who2)
            
            self.reply(who1, "Cupid's arrow has struck you! Your lover is %s." % who2)
            self.reply(who2, "Cupid's arrow has struck you! Your lover is %s." % who1)
            
            if self.check_night_done():
              self.day()
              
  def kill(self, e, who):
    "Allow a werewolf to express intent to 'kill' somebody."
	
    if self.gamestate != self.GAMESTATE_RUNNING:
      self.reply(e, "No game is in progress.")
      return
    
    if who == nm_to_n(e.source()).strip("&"):
      self.reply(e, "You cannot kill yourself.")
      return
    
    if self.time != "night":
      self.reply(e, "Are you a werewolf?  In any case, it's not nighttime.")
      return
    if nm_to_n(e.source()) not in self.wolves:
      self.reply(e, "Huh?")
      return
    if who not in self.live_players:
      self.reply(e, "That player either doesn't exist, or is dead.")
      return
    if len(self.wolves) > 1:
      # Multiple wolves are alive:
      self.wolf_votes[nm_to_n(e.source())] = who
      self.reply(e, "Your vote is acknowledged.")

      # If all wolves have voted, look for agreement:
      if len(self.wolf_votes) == len(self.wolves):
        for killee in self.wolf_votes.values():
          if who != killee:
            break
        else:
          self.wolf_target = who
          self.reply(e, "It is done. The werewolves agree.")
          if self.check_night_done():
            self.day()
          return
        self.reply(e, "Hm, I sense disagreement or ambivalence.")
        self.reply(e, "You wolves should decide on one target.")
    else:
      # only one wolf alive, no need to agree with anyone.
      self.wolf_target = who
      self.reply(e, "Your decision is acknowledged.")
      if self.check_night_done():
        self.day()


  def kill_player(self, player):
    "Make a player dead.  Return 1 if game is over, 0 otherwise."

    self.live_players.remove(player)
    self.dead_players.append(player)
    self.fix_modes()

    if player in self.wolves:
      id = "a \x034wolf\x0f\x02!"
      self.wolves.remove(player)
    elif player == self.seer:
      id = "the \x034seer\x0f\x02!"
    elif player == self.mystic:
      id = "the \x034mystic\x0f\x02!"
    elif player == self.angel:
      id = "the \x034angel\x0f\x02!"
    elif player == self.ninja:
      id = "the \x034ninja\x0f\x02!"
    elif player == self.cupid:
      id = "the \x034cupid\x0f\x02!"
    elif player == self.village_elder:
      id = "the \x034village elder\x0f\x02!"
    elif player == self.watchman:
      id = "the \x034watchman\x0f\x02!"
    else:
      id = "a normal villager."
    
    self.say_public(\
        ("*** Examining the body, you notice that this player was %s" % id))
    if self.check_game_over():
      return 1
    else:
      self.say_public(("(%s is now dead, and should stay quiet.)") % player)
      self.say_private(player, "You are now \x034dead\x0f\x02.  You may observe the game,")
      self.say_private(player, "but please stay quiet until the game is over.")
      
      return self.check_lovers(player)
  
  def check_lovers(self, player):
    if self.lovers and (self.lovers[0] in self.live_players or self.lovers[1] in self.live_players):
      if player is self.lovers[0]:
        self.say_public("%s cannot live without their lover %s! In grief, they commit suicide." % self.lovers[0], self.lovers[1])
        return self.kill_player(self.lovers[1])
      elif player is lovers[1]:
        self.say_public("%s cannot live without their lover %s! In grief, they commit suicide." % self.lovers[1], self.lovers[0])
        return self.kill_player(self.lovers[0])
    else: return 0


  def tally_votes(self):
    "Count votes in villager_votes{}, store results in tally{}."

    self.tally = {}
    for key in self.villager_votes.keys():
      lynchee = self.villager_votes[key]
      if self.tally.has_key(lynchee):
        self.tally[lynchee] += 1
      else:
        self.tally[lynchee] = 1


  def check_for_votes(self):
    """If there is a majority of lynch-votes for one player, return
    that player's name.  Else return None."""
    highest = 1
    victims = []
    for lynchee in self.tally.keys():
      if self.tally[lynchee] == highest:
        victims.append(lynchee)
      elif self.tally[lynchee] > highest:
        highest = self.tally[lynchee]
        del victims[:]
        victims.append(lynchee)

    return victims


  def print_tally(self):
    "Publically display the vote tally."
    msg = "Current vote tally: "
    for lynchee in self.tally.keys():
      if self.tally[lynchee] > 1:
        msg = msg + ("(%s : %d votes) " % (lynchee, self.tally[lynchee]))
      else:
        msg = msg + ("(%s : 1 vote) " % lynchee)
    self.say_public(msg)


  def print_alive(self):
    "Declare who's still alive."
    msg = "The following players are still alive: %s"%', '.join(self.live_players)
    self.say_public(msg)
    if self.dead_players:
      msg = "The following players are dead : %s"%', '.join(self.dead_players)
      self.say_public(msg)


  def match_name(self, nick):
    """Match NICK to a username in users(), insensitively.  Return
    matching nick, or None if no match."""

    chname, chobj = self.channels.items()[0]
    users = chobj.users()

    for user in users:
      if (user.strip("&")).upper() == nick.upper():
        return user.strip("&")
    return None

  def lynch_vote(self, e, lynchee, secret = False):
    "Register a vote to lynch LYNCHEE."
	
    lyncher = nm_to_n(e.source())
    # sanity checks
    if self.gamestate != self.GAMESTATE_RUNNING:
        self.reply(e, "No game is in progress.")
        return
    if self.time != "day":
      self.reply(e, "Sorry, lynching only happens during the day.")
    elif int(time.time() - self.day_timer) < (DAY_LENGTH / 2):
      self.reply(e, "Sorry, you can only vote during the voting period.")
    elif lyncher not in self.live_players:
      self.reply(e, "Um, only living players can vote to lynch someone.")
    elif lynchee not in self.live_players:
      self.reply(e, "Um, only living players can be lynched.")
    elif lynchee == lyncher:
      self.reply(e, "Um, you can't lynch yourself.")
    elif secret and self.elder_voted:
      self.reply(e, "You've already used your secret vote.")

    else:
      if not secret:
        self.villager_votes[lyncher] = lynchee
        self.say_public(("%s has voted to lynch %s!" % (lyncher, lynchee)))
        self.tally_votes()
        if len(self.villager_votes) == self.live_players:
          victims = self.check_for_votes()
          if not victims:
            self.print_tally()
            return
          elif len(victims) == 1:
            victim = victims[0]
          else:
            victim = victims[random.randrange(len(victims))]
            
          self.say_public(("The villagers have voted to lynch %s!! "
                             "Mob violence ensues.  This player is now \x034dead\x0f\x02." % victim))
          if not self.kill_player(victim):
          # Day is done;  flip bot back into night-mode.
            self.night()
      else:
        self.say_public("The village elder has voted to lynch %s!" % lynchee)
        if self.tally.has_key(lynchee):
          self.tally[lynchee] += 1
        else:
          self.tally[lynchee] = 1
        self.elder_voted = True
      
  
  def cmd_help(self, args, e):
    cmds = [i[4:] for i in dir(self) if i.startswith('cmd_')]
    self.reply(e, "Valid commands: '%s'" % "', '".join(cmds))

  def cmd_stats(self, args, e):
    if self.gamestate == self.GAMESTATE_RUNNING:
      self.print_alive()
      if self.time == "day":
        self.tally_votes()
        self.print_tally()
    elif self.gamestate == self.GAMESTATE_STARTING:
      self.reply(e, "A new game is starting, current players are %s"
          % (self.live_players,))
    else:
      self.reply(e, "No game is in progress.")

  def cmd_status(self, args, e):
    self.cmd_stats(args, e)

  def cmd_start(self, args, e):
    target = nm_to_n(e.source())
    self.start_game(target)
  
  def cmd_s(self, args, e):
    self.cmd_start(args, e)

  def cmd_end(self, args, e):
    target = nm_to_n(e.source())
    self.end_game(target)

  def cmd_votes(self, args, e):
    non_voters = []
    voters = []
    if self.villager_votes.keys():
      for n in self.live_players:
        if not self.villager_votes.has_key(n):
          non_voters.append(n)
        else:
          voters.append(n)
      if non_voters:
        self.say_public("The following have no votes registered: %s"
            % (non_voters))
	self.say_public("The votes are as follows: %s"
	    % (self.villager_votes))
      else:
        self.say_public("Everyone has voted.")
	self.say_public("The votes are as follows: %s"
	    % (self.villager_votes))
    else:
      self.say_public("Nobody has voted yet.")

  def cmd_del(self, args, e):
    for nick in args:
      if nick not in self.live_players + self.dead_players:
        self.reply(e, "There's nobody playing by the name %s" % nick)
      self._removeUser(nick)

  def cmd_renick(self, args, e):
    if len(args) != 1:
      self.reply(e, "Usage: renick <nick>")
    else:
      self.connection.nick(args[0])

  def cmd_see(self, args, e):
    target = nm_to_n(e.source())
    if len(args) == 1:
      viewee = self.match_name(args[0].strip())
      if viewee is not None:
        self.see(e, viewee.strip())
        return
    self.reply(e, "See whom?")
  
  def cmd_guard(self, args, e):
    target = nm_to_n(e.source())
    if len(args) == 1:
      guarded = self.match_name(args[0].strip())
      if guarded is not None:
        self.guard(e, guarded.strip())
        return
    self.reply(e, "Guard whom?")
    
  def cmd_assassinate(self, args, e):
    target = nm_to_n(e.source())
    if len(args) == 1:
      ass_target = self.match_name(args[0].strip())
      if ass_target is not None:
        self.assassinate(e, ass_target.strip())
        return
    self.reply(e, "Assassinate whom?")
  
  def cmd_lovers(self, args, e):
    target = nm_to_n(e.source())
    if len(args) == 2:
      lover1 = self.match_name(args[0].strip())
      if lover1 is not None:
        lover2 = self.match_name(args[1].strip())
        if lover1 == lover2:
          self.reply(e, "You can't lover someone with themselves!")
          return
        self.lover(e, lover1.strip(), lover2.strip())
        return
    self.reply(e, "Lover who?")
  
  def cmd_secretvote(self, args, e):
    target = nm_to_n(e.source())
    if self.village_elder is None or self.village_elder not in live_players or target != self.village_elder:
      self.reply(e, "Huh?")
    if len(args) == 1:
      lynchee = self.match_name(args[0])
      if lynchee is not None:
        self.lynch_vote(e, lynchee.strip(), True)
        return
    self.reply(e, "Vote for whom?")
    
  def cmd_kill(self, args, e):
    target = nm_to_n(e.source())
    if len(args) == 1:
      killee = self.match_name(args[0].strip())
      if killee is not None:
        self.kill(e, killee)
        return
    self.reply(e, "Kill whom?")

  def cmd_vote(self, args, e):
    target = nm_to_n(e.source())
    if len(args) == 1:
      lynchee = self.match_name(args[0])
      if lynchee is not None:
        self.lynch_vote(e, lynchee.strip())
        return
    self.reply(e, "Lynch whom?")
  
  def cmd_v(self, args, e):
    self.cmd_vote(args, e)

  def cmd_join(self, args, e):
    if self.gamestate == self.GAMESTATE_NONE:
      self.reply(e, 'No game is running, perhaps you would like to start one?')
      return
    if self.gamestate == self.GAMESTATE_RUNNING:
      self.reply(e, 'Game is in progress; please wait for the next game.')
      return
    player = nm_to_n(e.source())
    if player in self.live_players:
      self.reply(e, 'You were already in the game!')
    else:
      self.live_players.append(player)
      self.reply(e, 'You are now in the game.')
      self.fix_modes()
  
  def cmd_j(self, args, e):
    self.cmd_join(args, e)

  def cmd_aboutbot(self, args, e):
    self.reply(e, "I am a bot written in Python "
        "using the python-irclib library")
    self.reply(e, "My source code is available at %s" % url)

  def cmd_moderation(self, args, e):
    if self.game_starter and self.game_starter != nm_to_n(e.source()):
      self.reply(e, "%s started the game, and so has administrative control. "
          "Request denied." % self.game_starter)
      return
    if len(args) != 1:
      self.reply(e, "Usage: moderation on|off")
      return
    if args[0] == 'on':
      self.moderation = True
    elif args[0] == 'off':
      self.moderation = False
    else:
      self.reply(e, "Usage: moderation on|off")
      return
    self.say_public('Moderation turned %s by %s'
        % (args[0], nm_to_n(e.source())))
    self.fix_modes()

  def do_command(self, e, cmd):
    """This is the function called whenever someone sends a public or
    private message addressed to the bot. (e.g. "bot: blah").  Parse
    the CMD, execute it, then reply either to public channel or via
    /msg, based on how the command was received.  E is the original
    event, and FROM_PRIVATE is the nick that sent the message."""
    if cmd=='': return
    cmds = cmd.strip().split(" ")
    cmds[0]=cmds[0].lower()
    if self.debug and e.eventtype() == "pubmsg":
      if cmds[0][0] == '!':
        e._source = cmds[0][1:] + '!fakeuser@fakehost'
        cmds = cmds[1:]

    # Dead players should not speak.
    if nm_to_n(e.source()) in self.dead_players:
      if (cmd != "stats") and (cmd != "status") and (cmd != "help") and (cmd != "end"):
        self.reply(e, "Please -- dead players should keep quiet.")
        return 0

    try:
      cmd_handler = getattr(self, "cmd_" + cmds[0])
    except AttributeError:
      cmd_handler = None

    if cmd_handler:
      cmd_handler(cmds[1:], e)
      return

    # unknown command:  respond appropriately.

    # reply either to public channel, or to person who /msg'd
    if self.time == "night":
      self.reply(e, "SSSHH!  It's night, everyone's asleep!")
    else:
      self.reply(e, "That command makes no sense.")


def usage(exitcode=1):
  print "Usage: wolfbot.py [-d] [<config-file>]"
  sys.exit(exitcode)


def main():
  import getopt

  try:
    opts, args = getopt.gnu_getopt(sys.argv, 'd', ('debug',))
  except getopt.GetoptError:
    usage()

  debug = False
  for opt, val in opts:
    if opt in ('-d', '--debug'):
      debug = True

  if len(args) not in (1, 2):
    usage()

  if len(args) > 1:
    configfile = args[1]
  else:
    configfile = 'wolfbot.conf'

  import ConfigParser
  c = ConfigParser.ConfigParser()
  c.read(configfile)
  cfgsect = 'wolfbot'
  host = c.get(cfgsect, 'host')
  defaultPort = int(c.get(cfgsect, 'port'))
  channel = c.get(cfgsect, 'channel')
  nickname = c.get(cfgsect, 'nickname')
  nickpass = c.get(cfgsect, 'nickpass')

  s = string.split(host, ":", 1)
  server = s[0]
  if len(s) == 2:
    try:
      port = int(s[1])
    except ValueError:
      print "Error: Erroneous port."
      sys.exit(1)
  else:
    port = defaultPort

  bot = WolfBot(channel, nickname, nickpass, server, port, debug)


if __name__ == "__main__":
  try:
    main()
  except KeyboardInterrupt:
    print "Caught Ctrl-C during initialization."
