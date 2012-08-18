#!/usr/bin/python

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

import os
import sys
import random
import re
from xml.dom import minidom

# Constants

HAND_BUST, HAND_NORMAL, HAND_PONTOON, HAND_5CARDTRICK, HAND_5CARD21, HAND_SHEDPONTOON = range(6)
HandDescriptions = ("Bust","Normal","Pontoon","5 card trick","5 card 21","Shed Pontoon")
NumberString = ("first","second","third","fourth","fifth")
HandBonusMultipliers = { HAND_BUST : 0,
                         HAND_NORMAL : 2,
                         HAND_PONTOON : 3,
                         HAND_5CARDTRICK : 4,
                         HAND_5CARD21 : 5,
                         HAND_SHEDPONTOON : 8 }
MaxBetDivisors = ( 100.0, 10.0, 5.0, 4.0, 2.0 )

# Player class

class Player:
    "Class encapsulating a player."

    def __init__(self):
        self.TheHand = [[]]
        self.__Nick = ""
        self.__NickName = ""
        self.__Chips = 0
        self.__Played = 0
        self.__Won = 0
        self.__TotalBetThisGame = []
        self.__InitialBet = []
        self.__HasTwisted = []
        self.__PlayingHand = 0
        self.__SplitCount = 0

    def GetNick(self):
        return self.__Nick

    def SetNick(self,NewNick):
        self.__Nick = NewNick

    def GetDisplayName(self):
        if (self.__NickName != ""):
            return self.__NickName
        else:
            return self.__Nick

    def GetChips(self):
        return self.__Chips

    def IncChips(self,NumChips):
        self.__Chips += NumChips

    def IncPlayed(self):
        self.__Played += 1

    def IncWon(self):
        self.__Won += 1

    def NeedsInitialBet(self):
        if ( (len(self.TheHand[0]) == 1) and (not self.HasSplit()) ):
            # A hand with one card means an initial bet is needed
            return True
        else:
            return False

    def HasSplit(self):
        return (not self.__SplitCount == 0)

    def GetCurrentHand(self):
        return self.__PlayingHand+1

    def NextHand(self):
        self.__PlayingHand += 1

    def GetNumHands(self):
        return (len(self.TheHand))

    def GetNumCards(self,HandNumber):
        return (len(self.TheHand[HandNumber]))
        
    def DealACard(self, TheDealer):
        self.TheHand[self.__PlayingHand].append( TheDealer.DealCard() )

    def Twist(self, TheDealer):
        NewCard = TheDealer.DealCard()
        TheDealer.IRCObject.msg(TheDealer.Channel,"%s twists for a %s." % (self.GetDisplayName(),TheDealer.GetTextualDescription(NewCard)))
        self.TheHand[self.__PlayingHand].append( NewCard )
        self.__HasTwisted[self.__PlayingHand] = True
        if ( self.GetMaxScore(self.__PlayingHand) > 21 ):
            TheDealer.IRCObject.msg(self.GetNick(),"Twisting for a %s causes you to bust!" % TheDealer.GetTextualDescription(NewCard) )
            if ( self.HasSplit() ):
                TheDealer.IRCObject.msg(TheDealer.Channel,"%s busts on their %s hand." %
                                        (self.GetDisplayName(), NumberString[self.__PlayingHand]) )
            else:
                TheDealer.IRCObject.msg(TheDealer.Channel,"%s busts." % self.GetDisplayName())
            TheDealer.HandleNextTurn()
        else:
            self.ShowStatus(TheDealer)
            TheDealer.IRCObject.msg(self.GetNick(),self.BuildOptionsString())

    def Buy(self, TheDealer):
        if ( self.CanBuy() ):
            self.__Chips -= self.__InitialBet[self.__PlayingHand]
            self.__TotalBetThisGame[self.__PlayingHand] += self.__InitialBet[self.__PlayingHand]
            TheDealer.IRCObject.msg(TheDealer.Channel,"%s buys a card, throwing another %d chips in." %
                                    (self.GetDisplayName(), self.__InitialBet[self.__PlayingHand]) )
            NewCard = TheDealer.DealCard()
            self.TheHand[self.__PlayingHand].append( NewCard )
            if ( self.GetMaxScore(self.__PlayingHand) > 21 ):
                TheDealer.IRCObject.msg(self.GetNick(),"Buying a %s causes you to bust!" % TheDealer.GetTextualDescription(NewCard) )
                if ( self.HasSplit() ):
                    TheDealer.IRCObject.msg(TheDealer.Channel,"%s busts on their %s hand." %
                                            (self.GetDisplayName(), NumberString[self.__PlayingHand]))
                else:
                    TheDealer.IRCObject.msg(TheDealer.Channel,"%s busts." % self.GetDisplayName())
                TheDealer.HandleNextTurn()
            else:
                self.ShowStatus(TheDealer)
                TheDealer.IRCObject.msg(self.GetNick(),self.BuildOptionsString())
        else:
            TheDealer.IRCObject.msg(self.GetNick(),"Cannot buy: Either cannot afford it or you've already twisted!")

    def Stick(self, TheDealer):
        if ( self.CanStick() ):
            if ( self.HasSplit() ):
                TheDealer.IRCObject.msg(TheDealer.Channel,"%s sticks on their %s hand." %
                                        ( self.GetDisplayName(), NumberString[self.__PlayingHand] ))
            else:
                TheDealer.IRCObject.msg(TheDealer.Channel,"%s sticks." % self.GetDisplayName())
            TheDealer.HandleNextTurn()
        else:
            TheDealer.IRCObject.msg(self.GetNick(),"Cannot stick on this hand!")
            
    def Burn(self, TheDealer):
        if ( self.CanBurn() ):
            if ( self.HasSplit() ):
                TheDealer.IRCObject.msg(TheDealer.Channel,"%s burns their %s hand, throwing another %d chips in." %
                                        (self.GetDisplayName(), NumberString[self.__PlayingHand], self.__InitialBet[self.__PlayingHand]) )
            else:
                TheDealer.IRCObject.msg(TheDealer.Channel,"%s burns, throwing another %d chips in." %
                                        (self.GetDisplayName(), self.__InitialBet[self.__PlayingHand]) )
            self.__Chips -= self.__InitialBet[self.__PlayingHand]
            self.__TotalBetThisGame[self.__PlayingHand] += self.__InitialBet[self.__PlayingHand]
            self.TheHand[self.__PlayingHand] = []
            self.TheHand[self.__PlayingHand].append( TheDealer.DealCard() )
            self.TheHand[self.__PlayingHand].append( TheDealer.DealCard() )
            self.ShowStatus(TheDealer)
            TheDealer.IRCObject.msg(self.GetNick(),self.BuildOptionsString())
        else:
            TheDealer.IRCObject.msg(self.GetNick(),"Cannot burn with this hand!")
        pass

    def Split(self, TheDealer):
        if ( self.CanSplit() ):
            if ( self.HasSplit() ):
                TheDealer.IRCObject.msg(TheDealer.Channel,"%s splits their %s hand, putting another %d chips on a new hand." %
                                        (self.GetDisplayName(), NumberString[self.__PlayingHand], self.__InitialBet[0] ))
            else:
                TheDealer.IRCObject.msg(TheDealer.Channel,"%s splits, putting another %d chips on a new hand." %
                                        (self.GetDisplayName(), self.__InitialBet[0] ))
            self.__SplitCount += 1
            self.__Chips -= self.__InitialBet[0]
            self.TheHand.append([])
            self.__HasTwisted.append(False)
            self.__InitialBet.append( self.__InitialBet[0] )
            self.__TotalBetThisGame.append( self.__InitialBet[0] )
            NewHandIndex = len(self.TheHand)-1
            self.TheHand[NewHandIndex].append(self.TheHand[self.__PlayingHand].pop())
            self.DealACard(TheDealer)
            self.ShowStatus(TheDealer)
            TheDealer.IRCObject.msg(self.GetNick(),self.BuildOptionsString())
        else:
            TheDealer.IRCObject.msg(self.GetNick(),"Cannot split with this hand!")

    def PlaceBet(self, TheDealer, Bet):
        if ( Bet > self.__Chips ):
            TheDealer.IRCObject.msg(self.GetNick(),"You can't afford that, you only have %d chips!" % self.__Chips)
        else:
            self.__Chips -= Bet
            self.__HasTwisted.append(False)
            self.__InitialBet.append(Bet)
            self.__TotalBetThisGame.append(Bet)
            TheDealer.IRCObject.msg(TheDealer.Channel,"%s throws in %d chips." % (self.GetDisplayName(),Bet))
            TheDealer.HandleNextTurn()

    def GetCardValue(self,TheCard):
        Suit = TheCard / 13
        Value = TheCard % 13

        if ( (Value==0) or (Value==11) or (Value==12) ):
            return 10
        else:
            return Value

    def GetCardType(self,TheCard):
        TheType = TheCard % 13
        return TheType

    def GetNumAces(self,HandNumber):
        AceCount = 0
        for i in self.TheHand[HandNumber]:
            if (self.GetCardValue(i) == 1):
                AceCount+=1
        return AceCount

    def GetHandType(self, HandNumber):
        if (self.GetBaseScore(HandNumber) > 21):
            return HAND_BUST
        elif ((self.GetMaxScore(HandNumber) == 21) and (len(self.TheHand[HandNumber])==2)):
            return HAND_PONTOON
        elif (len(self.TheHand[HandNumber])>=5):
            if (self.GetMaxScore(HandNumber) == 21):
                return HAND_5CARD21
            else:
                return HAND_5CARDTRICK
        elif (len(self.TheHand[HandNumber])==3):
            if ( (self.GetCardValue(self.TheHand[HandNumber][0]) == 7) and
                 (self.GetCardValue(self.TheHand[HandNumber][1]) == 7) and
                 (self.GetCardValue(self.TheHand[HandNumber][2]) == 7)):
                return HAND_SHEDPONTOON
            
        return HAND_NORMAL

    def GetHandTypes(self):
        ReturnList = []
        
        for i in range(self.GetNumHands()):
            ReturnList.append(self.GetHandType(i))

        return ReturnList

    def GetBetThisHand(self,HandNumber):
        return self.__TotalBetThisGame[HandNumber]

    def CanStick(self):
        # Can only stick if less than 15 or has a 5 card trick
        if ( (self.GetMaxScore(self.__PlayingHand) <= 15) and ( len(self.TheHand[self.__PlayingHand]) < 5) ):
            return False
        else:
            return True

    def CanBuy(self):
        # Can only buy if hasn't already twisted...
        if ( not self.__HasTwisted[self.__PlayingHand] ):
            # ... and can afford to do so
            return ( self.__Chips >= self.__InitialBet[self.__PlayingHand] )
        else:
            return False

    def CanBurn(self):
        # Can only burn on hands with 2 cards and no aces, totalling 14...
        if ( (len(self.TheHand[self.__PlayingHand]) == 2) and (self.GetBaseScore(self.__PlayingHand) == 14)):
            # ... and if the player can afford to do so
            return ( self.__Chips >= self.__TotalBetThisGame[self.__PlayingHand] )
        else:
            return False

    def CanSplit(self):
        # Can split if we've split less than 4 times already, we have 2 of the same cards in this hand,
        # and we can afford to do so
        if ( (self.__SplitCount < 4) and
             (self.GetNumCards(self.__PlayingHand) == 2) and
             (self.GetCardType(self.TheHand[self.__PlayingHand][0]) == self.GetCardType(self.TheHand[self.__PlayingHand][1])) and
             (self.__Chips >= self.__InitialBet[self.__PlayingHand]) ):
            return True
        else:
            return False

    def GetBaseScore(self,HandNumber):
        TotalValue = 0
        for i in self.TheHand[HandNumber]:
            TotalValue += self.GetCardValue( i )
        return TotalValue

    def GetMaxScore(self,HandNumber):
        BaseScore = self.GetBaseScore(HandNumber)

        if ( self.GetNumAces(HandNumber) == 0 ):
            return BaseScore
        else:
            if ( (BaseScore+10) <= 21 ):
                return (BaseScore+10)
            else:
                return (BaseScore)

    def ShowStatus(self,TheDealer):
        if ( self.GetNumHands() > 1 ):
            HandString = "You have %d chips, and this hand (%d of %d) is " % (self.__Chips,self.__PlayingHand+1,self.GetNumHands() )
        else:
            HandString = "You have %d chips, and your hand is " % self.__Chips
            
        for i in self.TheHand[self.__PlayingHand]:
            HandString += TheDealer.GetTextualDescription( i )
            HandString += ","

        HandString += " (maximum value %d)." % self.GetMaxScore(self.__PlayingHand)
        TheDealer.IRCObject.msg(self.GetNick(),HandString)

    def BuildOptionsString(self):
        OptionsString = "(t)wist"
        
        if ( self.CanStick() ):
            OptionsString += ",(s)tick"
        if ( self.CanBuy() ):
            OptionsString += ",(b)uy"
        if ( self.CanBurn() ):
            OptionsString += ",b(u)rn"
        if ( self.CanSplit() ):
            OptionsString += ",s(p)lit"

        OptionsString += "?"
        return OptionsString

    def LoadXML(self,xmldoc):
        PlayerList = xmldoc.getElementsByTagName('player')
        for i in PlayerList:
            if (i.getElementsByTagName('nick')[0].childNodes[0].data == self.GetNick()):
                self.__Chips = int(i.getElementsByTagName('chips')[0].childNodes[0].data)
                self.__Played = int(i.getElementsByTagName('pontoon')[0].getElementsByTagName('played')[0].childNodes[0].data)
                self.__Won = int(i.getElementsByTagName('pontoon')[0].getElementsByTagName('won')[0].childNodes[0].data)
                try:
                    self.__NickName = str( i.getElementsByTagName('variables')[0].getElementsByTagName('nickname')[0].childNodes[0].data )
                except IndexError:
                    self.__NickName = ""
                return True
        return False

    def Load(self,Filename):
        f=open(Filename, 'r')
        PlayerData = f.readlines()
        f.close()
        PlayerFound = False
        for i in PlayerData:
            records = re.split(",", i)
            if (records[0] == self.GetNick()):
                self.__Chips = int(records[1])
                self.__Played = int(records[2])
                self.__Won = int(records[3])
                PlayerFound = True
        if ( PlayerFound ):
            return True
        else:
            return False

    def SaveXML(self,xmldoc):
        PlayerList = xmldoc.getElementsByTagName('player')
        for i in PlayerList:
            if (i.getElementsByTagName('nick')[0].childNodes[0].data == self.GetNick()):
                i.getElementsByTagName('chips')[0].childNodes[0].data = str(self.__Chips)
                i.getElementsByTagName('pontoon')[0].getElementsByTagName('played')[0].childNodes[0].data = str(self.__Played)
                i.getElementsByTagName('pontoon')[0].getElementsByTagName('won')[0].childNodes[0].data = str(self.__Won)
        
    def Save(self,Filename):
        f=open(Filename, 'r')
        PlayerData = f.readlines()
        f.close()
        f=open(Filename, 'w')
        for i in PlayerData:
            records = re.split(",", i)
            records[4] = records[4].rstrip('\n')
            if ( records[0] == self.GetNick() ):
                f.write( self.GetNick() + "," + str(self.__Chips) + "," + str(self.__Played) + "," + str(self.__Won) + '\n' )
            else:
                f.write( records[0] + "," + records[1] + "," + records[2] + "," + records[3] + "," + records[4] + '\n')
        f.close()

# Pack class

class Pack:
    "Class holding the card shoe."

    def __init__(self, NumPacks = 6):
        self.NumPacks = NumPacks
        self.ShuffleMarker = 0
        self.__NeedsShuffle = False
        self.Shuffle()

    def Shuffle(self):
        self.ThePack = []
        for i in range(self.NumPacks):
            self.ThePack.extend( range(52) )
        self.ShuffleMarker = random.randrange( 60, 75 )
        self.ShuffleMarker = len(self.ThePack) - self.ShuffleMarker
        random.shuffle(self.ThePack)
        self.__NeedsShuffle = False

    def SelectCard(self,TheDealer):
        TheCard = self.ThePack.pop()
        if ( len(self.ThePack) == self.ShuffleMarker ):
            self.__NeedsShuffle = True
            TheDealer.IRCObject.msg(TheDealer.Channel,"Shuffle card hit, pack will be shuffled after this hand.")
        return TheCard

    def GetShuffleMarker(self):
        return self.ShuffleMarker
    
    def NeedsShuffle(self):
        return self.__NeedsShuffle

    def PrintPack(self):
        print self.ThePack

# Dealer class

class Dealer:
    "Class encapsulating the game's dealer."

    def __init__(self, NumDecks = 1):
        self.ThePack = Pack()
        self.NextPlayer = -1
        self.GameInProgress = False
        self.Players = []

    def IsPlayerInFile(self,PlayerNick):
        PlayerList = self.PlayerXML.getElementsByTagName('player')
        for i in PlayerList:
            if (i.getElementsByTagName('nick')[0].childNodes[0].data == PlayerNick):
                return True
        return False

    def GetNumPlayers(self):
        return len(self.Players)

    def GetMaxBet(self, ThePlayer):
        if ( self.GetNumPlayers() >=5 ):
            Divisor = MaxBetDivisors[4]
        else:
            Divisor = MaxBetDivisors[ self.GetNumPlayers() -1 ]
        Roundup = ( 1.0 - (1/Divisor) )
        return int( Roundup + (ThePlayer.GetChips() / Divisor) )

    def StartGame(self,IRCObject,Channel,PlayerNames):

        self.IRCObject = IRCObject
        self.Channel = Channel

        # Create players and load data
        self.Players = []
        self.IRCObject.describe(self.Channel,"puts the dealer's hat on!")

        self.PlayerXML = minidom.parse('./players.xml')

        for i in range( len(PlayerNames) ):
            NewPlayer = Player()
            NewPlayer.SetNick( PlayerNames[i] )

            # Create this from XML data
            if ( not NewPlayer.LoadXML( self.PlayerXML ) ):
                self.IRCObject.msg(self.Channel,"Failed to load %s from players file, game aborted!" % NewPlayer.GetNick() )
                return

            # Check if we have chips
            if ( NewPlayer.GetChips() == 0 ):
                self.IRCObject.msg(self.Channel,"%s has no chips, game aborted!" % NewPlayer.GetNick() )
                return

            # All OK
            NewPlayer.DealACard(self)
            NewPlayer.ShowStatus(self)
            self.Players.append( NewPlayer )

        # Start the game
        self.NextPlayer = -1
        self.GameInProgress = True
        self.HandleNextTurn()

    def GetTextualDescription(self,TheCard):
        Suits = ("Hearts","Clubs","Diamonds","Spades")
        
        Suit = TheCard / 13
        Value = TheCard % 13

        if (( Value < 11 ) and ( Value > 1 )):
            CardDescription = str(Value) + " of " + Suits[Suit]
        else:
            if ( Value == 1 ):
                CardDescription = "Ace"
            elif ( Value == 11 ):
                CardDescription = "Jack"
            elif ( Value == 12 ):
                CardDescription = "Queen"
            elif ( Value == 0 ):
                CardDescription = "King"
            
            CardDescription += " of " + Suits[Suit]

        return CardDescription

    def HandleNextTurn(self):

        # See if current player has played all his hands
        if ( self.Players[self.NextPlayer].GetCurrentHand() < self.Players[self.NextPlayer].GetNumHands() ):
            self.Players[self.NextPlayer].NextHand()
            self.Players[self.NextPlayer].DealACard(self)
        else:
            self.NextPlayer +=1
            
        if (self.NextPlayer == len(self.Players)):
            self.NextPlayer = 0
            if ( not self.Players[self.NextPlayer].NeedsInitialBet() ):
                self.Reveal()
            else:
                # betting round over, deal another card
                for i in self.Players:
                    i.DealACard(self)
                    i.ShowStatus(self)
                self.IRCObject.msg(self.Channel,"Betting round over, %s to go." % self.Players[self.NextPlayer].GetDisplayName())
                self.IRCObject.msg(self.Players[self.NextPlayer].GetNick(),self.Players[self.NextPlayer].BuildOptionsString())
        else:
            if ( (self.NextPlayer == 0) and (not self.Players[self.NextPlayer].HasSplit()) ):
                self.IRCObject.msg(self.Channel,"Betting round, %s to go." % self.Players[self.NextPlayer].GetDisplayName())
                
            if ( self.Players[self.NextPlayer].NeedsInitialBet() ):
                MaxBet = self.GetMaxBet(self.Players[self.NextPlayer])
                self.IRCObject.msg(self.Players[self.NextPlayer].GetNick(),"Initial bet in chips (1 - %d)?" % MaxBet)
            else:
                self.Players[self.NextPlayer].ShowStatus(self)
                self.IRCObject.msg(self.Players[self.NextPlayer].GetNick(),self.Players[self.NextPlayer].BuildOptionsString())

    # Handle incoming messages (bets, twist, stick, burn, split)
    def HandleEvents(self,Nick,message):
        if ( Nick == self.Players[self.NextPlayer].GetNick() ):
            if ( self.Players[self.NextPlayer].NeedsInitialBet() ):
                MaxBet = self.GetMaxBet(self.Players[self.NextPlayer])
                # We're expecting a number
                if ( (int(message) <= 0) or (int(message) > MaxBet) ):
                    # Bet out of range
                    self.IRCObject.msg(Nick,"Please bet between 1 and %d" % MaxBet)
                else:
                    # Place bet
                    self.Players[self.NextPlayer].PlaceBet(self,int(message))
            else:
                if ( message == "s" ):
                    self.Players[self.NextPlayer].Stick(self)
                elif ( message == "t" ):
                    self.Players[self.NextPlayer].Twist(self)
                elif ( message == "b" ):
                    self.Players[self.NextPlayer].Buy(self)
                elif ( message == "u" ):
                    self.Players[self.NextPlayer].Burn(self)
                elif ( message == "p" ):
                    self.Players[self.NextPlayer].Split(self)
        else:
            self.IRCObject.msg(Nick,"Waiting for %s to take their turn!" % self.Players[self.NextPlayer].GetDisplayName())

    # End of game
    def Reveal(self):

        # Display game results into channel
        self.IRCObject.msg(self.Channel,"End of game results:")
        
        for i in self.Players:
            NumHands = i.GetNumHands()
            HandNumber = 0
            for j in i.GetHandTypes():
                if ( j == HAND_BUST ):
                    if ( NumHands > 1 ):
                        HandString = "%s bust on their %s hand." % (i.GetDisplayName(), NumberString[HandNumber])
                    else:
                        HandString = "%s bust." % i.GetDisplayName()
                else:
                    HandString = "%s has " % i.GetDisplayName()
                    if ( NumHands > 1 ):
                        for k in i.TheHand[HandNumber]:
                            HandString += self.GetTextualDescription(k)
                            HandString += ","
                        HandString += " on their %s hand." % NumberString[HandNumber]
                    else:
                        for k in i.TheHand[0]:
                            HandString += self.GetTextualDescription(k)
                            HandString += ","

                    HandString += " (%d, %s)." % (i.GetMaxScore(HandNumber),HandDescriptions[j])
                    
                self.IRCObject.msg(self.Channel, HandString)
                HandNumber +=1

        # Create list of (handtype,score,handnumber,player) tuples
        HandList = []
        
        for i in self.Players:
            i.IncPlayed()
            HandNumber = 0
            for j in i.GetHandTypes():
                HandList.append((i.GetHandType(HandNumber),
                                 i.GetMaxScore(HandNumber),
                                 HandNumber,
                                 i))
                HandNumber += 1

        # Filter into appropriate lists
        ShedPontoonHands       = [i for i in HandList if i[0] == HAND_SHEDPONTOON]
        FiveCardTwentyOneHands = [i for i in HandList if i[0] == HAND_5CARD21]
        FiveCardTrickHands     = [i for i in HandList if i[0] == HAND_5CARDTRICK]
        PontoonHands           = [i for i in HandList if i[0] == HAND_PONTOON]
        NormalHands21          = [i for i in HandList if i[0] == HAND_NORMAL and i[1] == 21]
        NormalHands20          = [i for i in HandList if i[0] == HAND_NORMAL and i[1] == 20]
        NormalHands19          = [i for i in HandList if i[0] == HAND_NORMAL and i[1] == 19]
        NormalHands18          = [i for i in HandList if i[0] == HAND_NORMAL and i[1] == 18]
        NormalHands17          = [i for i in HandList if i[0] == HAND_NORMAL and i[1] == 17]
        NormalHands16          = [i for i in HandList if i[0] == HAND_NORMAL and i[1] == 16]
        BustHands              = [i for i in HandList if i[0] == HAND_BUST]

        # Append to final winning list in order
        WinningHands = []

        if ( len(ShedPontoonHands) > 0 ):
            WinningHands.append(ShedPontoonHands)
        if ( len(FiveCardTwentyOneHands) > 0 ):
            WinningHands.append(FiveCardTwentyOneHands)
        if ( len(FiveCardTrickHands) > 0 ):
            WinningHands.append(FiveCardTrickHands)
        if ( len(PontoonHands) > 0 ):
            WinningHands.append(PontoonHands)
        if ( len(NormalHands21) ):
            WinningHands.append(NormalHands21)
        if ( len(NormalHands20) ):
            WinningHands.append(NormalHands20)
        if ( len(NormalHands19) ):
            WinningHands.append(NormalHands19)
        if ( len(NormalHands18) ):
            WinningHands.append(NormalHands18)
        if ( len(NormalHands17) ):
            WinningHands.append(NormalHands17)
        if ( len(NormalHands16) ):
            WinningHands.append(NormalHands16)

        # Check to see if it's not all bust
        if ( len(WinningHands) > 0 ):
            
            # List of nicks with the top hand
            WinningNicks = []
            for i in WinningHands[0]:
                if (WinningNicks.count(i[3].GetNick()) == 0):
                    WinningNicks.append(i[3].GetNick())
            WinningNicks.sort()

            # Pay primary hands
            for i in WinningHands[0]:
                
                # Scraped through on 16 while everyone else bust; "clown wagon" bonus
                if ( (len(WinningHands[0]) == 1 ) and ( i[0] == HAND_NORMAL ) and ( i[1] == 16 ) ):
                    Multiplier = 2.5
                    BonusString = "1.5x Clown Wagon bonus"
                else:
                    Multiplier = HandBonusMultipliers[i[0]]
                    BonusString = "%dx %s bonus" % ( Multiplier-1, HandDescriptions[i[0]] )
                    
                i[3].IncChips( int( i[3].GetBetThisHand(i[2]) * Multiplier) )
                i[3].IncWon()
                
                if ( i[3].GetNumHands() > 1 ):
                    self.IRCObject.msg( self.Channel,
                                        "%s wins %d chips on their %s hand (%s)." % (i[3].GetDisplayName(),
                                                                                     i[3].GetBetThisHand(i[2]) * (Multiplier-1),
                                                                                     NumberString[i[2]],
                                                                                     BonusString ))
                else:
                    self.IRCObject.msg(self.Channel,
                                       "%s wins %d chips (%s)." % (i[3].GetDisplayName(),
                                                                   i[3].GetBetThisHand(i[2]) * (Multiplier-1),
                                                                   BonusString ))
                    
            # No longer need primary winners
            WinningHands.pop(0)

            # If there's any more winners, pay subsequent hands if they equal the winning nicks
            CanPay = True
            
            for i in WinningHands:
                ThisHandNicks = []
                for j in i:
                    if (ThisHandNicks.count(j[3].GetNick()) == 0):
                        ThisHandNicks.append( j[3].GetNick() )
                ThisHandNicks.sort()
                
                for j in i:
                    if ((ThisHandNicks == WinningNicks) and (CanPay==True)):
                        j[3].IncChips( j[3].GetBetThisHand(j[2]) * HandBonusMultipliers[j[0]] )
                        BonusString = "%dx %s bonus" % ( HandBonusMultipliers[j[0]]-1, HandDescriptions[j[0]] )
                        if ( j[3].GetNumHands() > 1 ):
                            self.IRCObject.msg(self.Channel,"%s wins %d chips on their %s hand (%s)." %
                                               (j[3].GetDisplayName(),
                                                j[3].GetBetThisHand(j[2]) * (HandBonusMultipliers[j[0]]-1),
                                                NumberString[j[2]],
                                                BonusString ))
                        else:
                            self.IRCObject.msg(self.Channel,"%s wins %d chips (%s)." %
                                               (j[3].GetDisplayName(),
                                                j[3].GetBetThisHand(j[2]) * (HandBonusMultipliers[j[0]]-1),
                                                NumberString[j[2]],
                                                BonusString ))
                    else:
                        CanPay = False
                        if ( j[3].GetNumHands() > 1 ):
                            self.IRCObject.msg(self.Channel,"%s loses %d chips on their %s hand." %
                                               ( j[3].GetDisplayName(),
                                                 j[3].GetBetThisHand(j[2]),
                                                 NumberString[j[2]]) )
                        else:
                            self.IRCObject.msg(self.Channel,"%s loses %d chips." % (j[3].GetDisplayName(),j[3].GetBetThisHand(j[2])))

        # Do bust hands
        for i in BustHands:
            if ( i[3].GetNumHands() > 1 ):
                self.IRCObject.msg(self.Channel,"%s loses %d chips on their %s hand." %
                                   (i[3].GetDisplayName(),
                                    i[3].GetBetThisHand(i[2]),
                                    NumberString[i[2]]))
            else:
                self.IRCObject.msg(self.Channel,"%s loses %d chips." % (i[3].GetDisplayName(),
                                                                        i[3].GetBetThisHand(i[2])))
            
        # Save data
        for i in self.Players:
            i.SaveXML(self.PlayerXML)
        XMLFile = file('./players.xml','w+')
        self.PlayerXML.writexml(XMLFile)

        # New pack shuffling
        if ( self.ThePack.NeedsShuffle() ):
            self.IRCObject.describe(self.Channel,"shuffles the pack")
            self.ThePack.Shuffle()
            self.IRCObject.msg(self.Channel,"New shuffle marker placed at card index %d." % self.ThePack.GetShuffleMarker() )

        self.GameInProgress = False

    # Deal
    def DealCard(self):
        return self.ThePack.SelectCard(self)

# Pontoon
class Pontoon:
    "Pontoon class"

    def __init__(self):
        self.TheDealer = Dealer()
        self.SetVariableRegexp = re.compile('\s*set\s+(\w+)\s+(.*)')
        self.ClearVariableRegexp = re.compile('\s*clear\s+(\w+)\s+(.*)')
        
    def StartGame(self,IRCObject,Channel,PlayerList):
        self.TheDealer.StartGame(IRCObject,Channel,PlayerList)

    def Stats(self,IRCObject,Channel):

        PlayerXML   = minidom.parse('./players.xml')
        PlayerList  = PlayerXML.getElementsByTagName('player')
        WinnerTable = []
        
        IRCObject.msg(Channel,"Player                           Chips    Bank Played  Won Win ratio")
        IRCObject.msg(Channel,"------                           -----    ---- ------  --- ---------")
        
        for i in PlayerList:
            Nick     = str( i.getElementsByTagName('nick')[0].childNodes[0].data )
            try:
                NickName = str( i.getElementsByTagName('variables')[0].getElementsByTagName('nickname')[0].childNodes[0].data )
            except IndexError:
                NickName = ""
            Chips    = int( i.getElementsByTagName('chips')[0].childNodes[0].data )
            Bank     = int( i.getElementsByTagName('bank')[0].childNodes[0].data )
            Played   = int( i.getElementsByTagName('pontoon')[0].getElementsByTagName('played')[0].childNodes[0].data )
            Won      = int( i.getElementsByTagName('pontoon')[0].getElementsByTagName('won')[0].childNodes[0].data )
            try:
                Ratio = (Won / (float(Played))) * 100
            except ZeroDivisionError:
                Ratio = 0
            WinnerTable.append( (Nick,NickName,Chips,Bank,Played,Won,Ratio) )

        WinnerTable.sort( lambda x,y: cmp(x[6],y[6]) )
        WinnerTable.reverse()
        
        for i in WinnerTable:
            if ( i[1] != "" ):
                FullName = i[0] + " (" + i[1] + ")"
            else:
                FullName = i[0]
            IRCObject.msg(Channel,"%-30s %7d %7d %6d %4d %8.2f%%" % (FullName, i[2], i[3], i[4], i[5], i[6]))

    def GameInProgress(self):
        return self.TheDealer.GameInProgress

    def SetPlayerVariable(self,IRCObject,Nick,Variable,Value):
        PlayerXML   = minidom.parse('./players.xml')
        PlayerList  = PlayerXML.getElementsByTagName('player')
        Value       = Value.rstrip()

        for i in PlayerList:
            ThisNick = str( i.getElementsByTagName('nick')[0].childNodes[0].data )
            if ( ThisNick == Nick ):
                try:
                    if ( not i.getElementsByTagName('variables')[0].getElementsByTagName(Variable)[0].hasChildNodes() ):
                        NewChild = PlayerXML.createTextNode(Value)
                        i.getElementsByTagName('variables')[0].getElementsByTagName(Variable)[0].appendChild(NewChild)
                    else:
                        i.getElementsByTagName('variables')[0].getElementsByTagName(Variable)[0].childNodes[0].data = Value

                    XMLFile = file('./players.xml','w+')
                    PlayerXML.writexml(XMLFile)
                    IRCObject.msg(Nick,"%s variable updated." % Variable)
                except IndexError:
                    IRCObject.msg(Nick,"Error writing variable (does it exist?).")

    def HandleMessages(self,IRCObject,FromNick,Message):
        VarSetMatch = self.SetVariableRegexp.match(Message)
        if ( VarSetMatch != None ):
            # Set variables
            if ( not self.GameInProgress() ):
                self.SetPlayerVariable(IRCObject,FromNick,VarSetMatch.group(1),VarSetMatch.group(2))
            else:
                IRCObject.msg(FromNick,"Sorry, cannot set variables during a game.")
        else:
            # Pass on to dealer
            if ( self.GameInProgress() ):
                self.TheDealer.HandleEvents(FromNick,Message)
