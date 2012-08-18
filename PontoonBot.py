#!/usr/local/bin/python

# (c) 2004 Dave Footitt.

# This file is part of irc-pontoon.

# irc-pontoon is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# irc-pontoon is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with irc-pontoon.  If not, see <http://www.gnu.org/licenses/>.

import sys
import time
import re
import shelve
import random

from xml.dom import minidom
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from twisted.python import log
from twisted.internet import defer

# Games
from Pontoon import Pontoon

# Bot name and channel
BOTNAME         = "CardNinja"
IRCCHANNEL      = "#my_channel"

class LogBot(irc.IRCClient):
    """A logging IRC bot."""

    def __init__(self):
        self.nickname = BOTNAME
        self.PontoonGame = Pontoon()
        self._pendingWho = []
	self._pendingWhoIs = []
        self._PlayerList = []
        
    def connectionMade(self):
        irc.IRCClient.connectionMade(self)

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)

    def who(self, name):
        """List names of users who match a particular pattern.
    
        @type name: C{str}
        @param name: The pattern against which to match.
    
        @rtype: C{Deferred} of C{list} of C{tuples}
        @return: A list of 8-tuples consisting of
    
        channel, user, host, server, nick, flags, hopcount, real name
    
        all of which are strings, except hopcount, which is an integer.
        """
        d = defer.Deferred()
        self._pendingWho.append(([], d))
        self.sendLine("WHO " + name)
        return d

    def whois(self, name):
	d = defer.Deferred()
	self._pendingWhoIs.append(([],d))
	self.sendLine("WHOIS " + name)
	return d

    # callbacks for events

    def StartPontoon(self, who):
        Found = True
        NicksInChannel = map(lambda i: i[3], who)
        for i in self._PlayerList:
            if (NicksInChannel.count(i) == 0):
                Found = False
                break
            
        if (not Found):
            self.msg(IRCCHANNEL,"%s is not in the channel." % i)
        else:
            self.PontoonGame.StartGame(self,IRCCHANNEL,self._PlayerList)

    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        self.join(self.factory.channel)

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        pass

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        user = user.split('!', 1)[0]
        if ( channel == self.nickname ):
            self.PontoonGame.HandleMessages( self, user, msg )
        else:
            if msg.startswith("!bank"):
                if (not self.PontoonGame.GameInProgress()):
                    self.handleBank(user,msg)
                else:
                    self.msg(IRCCHANNEL,"Cannot do bank transfers during game.")
            elif msg.startswith("!pontoon"):
                PlayerList = msg.split()
                if (len(PlayerList) == 1 ):
                    # Auto-deal on just '!pontoon'
                    if ( len(self._PlayerList ) >= 1 ):
                        self._PlayerList.append(self._PlayerList.pop(0))
                        self.who(IRCCHANNEL).addCallback(self.StartPontoon)
                    else:
                        self.msg(IRCCHANNEL,"Player list is empty, cannot auto-deal.")
                elif (PlayerList[1] == "stats"):
                    self.PontoonGame.Stats(self,IRCCHANNEL)
                else:
                    PlayerList.remove("!pontoon")
                    if ( PlayerList.count(self.nickname) > 0 ):
                        self.msg(IRCCHANNEL,"I cannot play!")
                    elif ( len(PlayerList) < 1 ):
                        self.msg(IRCCHANNEL,"Not enough players specified.")
                    else:
                        MultiplePlayersDetected = False
                        for i in PlayerList:
                            if (PlayerList.count(i) > 1 ):
                                MultiplePlayersDetected = True
                        if ( MultiplePlayersDetected ):
                            self.msg(IRCCHANNEL,"Cannot have multiple instances of a player.")
                        else:
                            self._PlayerList = PlayerList
                            self.who(IRCCHANNEL).addCallback(self.StartPontoon)

    def action(self, user, channel, msg):
        """This will get called when the bot sees someone do an action."""
        user = user.split('!', 1)[0]

    def handleBank(self, user, msg):
        playerXML = minidom.parse('./players.xml')
        PlayerList = playerXML.getElementsByTagName('player')
        for i in PlayerList:
            if (i.getElementsByTagName('nick')[0].childNodes[0].data == user):
                args = msg.split()
                # !bank +100 : Deposit 100
                # !bank -100 : Withdraw 100
                chips = int(i.getElementsByTagName('chips')[0].childNodes[0].data)
                bank = int(i.getElementsByTagName('bank')[0].childNodes[0].data)
                if (len(args) <=1):
                    self.msg(IRCCHANNEL,"You have %d chips (%d banked)." % (chips,bank))
                else:
                    try:
                        amount = int(args[1])
                        if (amount > 0):
                            if (amount < chips):
                                chips -= amount
                                bank += amount
                                self.msg(IRCCHANNEL,"Deposit OK (Chips %d, Bank %d)" % (chips,bank))
                            else:
                                raise ValueError
                        elif (amount < 0):
                            amount = abs(amount)
                            if (amount <= bank):
                                chips += amount
                                bank -= amount
                                self.msg(IRCCHANNEL,"Withdraw OK (Chips %d, Bank %d)" % (chips,bank))
                            else:
                                raise ValueError
                        else:
                            raise ValueError

                        i.getElementsByTagName('chips')[0].childNodes[0].data = str(chips)
                        i.getElementsByTagName('bank')[0].childNodes[0].data = str(bank)
                        XMLFile = file('./players.xml','w+')
                        playerXML.writexml(XMLFile)
                         
                    except ValueError:
                        self.msg(IRCCHANNEL,"Silly")

    def irc_NICK(self, prefix, params):
        """Called when an IRC user changes their nickname."""
        old_nick = prefix.split('!')[0]
        new_nick = params[0]

    def irc_RPL_WHOREPLY(self, prefix, params):
        params = params[2:]
        params[-1:] = params[-1].split(None, 1)
        params[-2] = int(params[-2])
        self._pendingWho[0][0].append(tuple(params))

    def irc_RPL_ENDOFWHO(self, prefix, params):
        who, d = self._pendingWho.pop(0)
        d.callback(who)

    def irc_RPL_WHOISUSER(self, prefix, params):
	params = params[1]
	self._pendingWhoIs[0][0].append(params)

    def irc_RPL_ENDOFWHOIS(self, prefix, params):
	who, d = self._pendingWhoIs.pop(0)
	d.callback(who)

class LogBotFactory(protocol.ClientFactory):
    """A factory for LogBots.

    A new protocol instance will be created each time we connect to the server.
    """       

    # the class of the protocol to build when new connection is made
    protocol = LogBot

    def __init__(self, channel):
		self.channel = channel
		self.connectRetries = 0
		self.connectSleep = 7
		self.maxConnect = 23

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
   	self.connectRetries = 0
        connector.connect()
   	print 'clientConnectionLost'
	
    def clientConnectionFailed(self, connector, reason):
	# Sleep for for a few secs, then reconnect
	# abort if all retries are exhausted
        print 'clientConnectionFailed connectRetries = ', self.connectRetries
        self.connectRetries += 1
        if ( self.connectRetries <= self.maxConnect ):
            time.sleep(self.connectSleep)			
            connector.connect()
        else:
            reactor.stop()

if __name__ == '__main__':
    # initialize logging
    log.startLogging(sys.stdout)

    # create factory protocol and application
    f = LogBotFactory(IRCCHANNEL)

    # connect factory to this host and port
    reactor.connectTCP("localhost", 6667, f)

    # run bot
    reactor.run()

