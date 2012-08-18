irc-pontoon
----

A simple IRC bot using Python and Twisted Matrix, incorporating a multi-player (player verus player) variant of Pontoon ("Blackjack") which is played in the IRC channel.

Before you start
----

You will need [Twisted Python](http://twistedmatrix.com)

Running
----

Run the bot by typing:

````
./PontoonBot.py
````

It will join the IRC server at the address specified in __main__, and connect to the channel defined at the top of the file.

How to play
----

Shed pontoon is a variation on traditional pontoon, the main difference being the players play against each other rather than against the dealer, although the dealer is currently responsible for dealing cards and paying winning hands. It currently uses a card shoe combining 6 decks, with a shuffle marker. Cards are shuffled only when the marker is hit, and a new marker is placed randomly between the last 60-75 cards of the shoe.

Nicknames
----

Players may elect to have a nickname, and change it as they wish. This is done using the command:

````
/msg <bot-name> set nickname <new-nickname>
`````

Just passing a space character as a nickname will effectively unset any nickname.

Winning hand types
----

Winners are decided based upon the best hands, and winning players are payed bonuses according to their hand type:

* Shed pontoon - 3 7s of any suit ( 7x bonus )
* 5 card trick totalling 21 ( 4x bonus )
* 5 card trick ( 3x bonus )
* Traditional pontoon - Ace and a ten or picture card ( 2x bonus )
* Clown Wagon bonus - Only remaining player and hand is 16 ( 1.5x bonus )
* High cards - Highest total ( No bonus; just pays the stake back )

Starting the game
----

A game is started with the command (entered into the irc channel):

````
!pontoon <playerlist>
````

For example: 

````
!pontoon dave kevin bob
````

Note that all players must be present in the channel _and_ have an entry in the players.xml file.  Subsequent `!pontoon` commands with no arguments will start a game with the players specified previously, and rotate this list every game.

Each player is then dealt a card, and a turn of betting begins.

Playing the game
----

Dealing proceeds in the order passed to the `!pontoon` command. Initial bets are placed for each player. When this round is over, the next round begins where players attempt to get the best hand possible.

Maximum initial bets
----

Maximum bets are governed by how many people are in the game. This is to avoid single player games racking up huge wins due to increased odds.  This is set as:

* 1 player - 1% of players' total chips
* 2 players - 10% of players' total chips
* 3 players - 20% of players' total chips
* 4 players - 25% of players' total chips
* 5+ players - 50% of players' total chips

Further betting rounds
----

After initial bets, players compete to try and attain the best possible hand before either sticking or busting. Shed pontoon supports sticking, twisting, buying, burning and splitting (up to 4 times). After each player has finished playing, winning calculations are performed, and bets paid.

*STICK*  
If a player has 16 or over, they may stick.

*TWIST*  
A player may twist to get another card from the dealer. Once a player twists, buying a card is not possible.

*BUY*  
Buying a card costs the player their initial bet, and has the advantages that the other players can't see the card, and also will contribute to their winning pot if this hand wins.

*BURN*  
If a player has 2 cards with a total of 14 (not including aces) they may elect to 'burn'. This costs them their initial bet, and gets them a fresh hand. There is no limit to the amount of times a player may burn if they get multiple hands meeting the burn criteria.

*SPLIT*  
If a player is dealt 2 cards of the same denomination, they may choose to split. This creates a new hand and places the initial bet on the second hand. This may be done up to 4 times, and each hand is then played in turn, normally.

Winning calculations
----

At the end of the game, the winning hand(s) are paid. If there are multiple winning hands they all win. In the case of players having several hands (ie they have split) each hand is counted independently. So for example:

Bob, 21, Pontoon
Bob, 20, Normal
Dave, 16, Normal

Bob would win on both hands and Dave would lose on his 16. However, if the hands were:

Bob, 21, Pontoon
Kevin, 21, Pontoon
Bob, 18, Normal

Both Bob and Kevin would win on their pontoon hands but Bob would lose on his 18 hand.

If 2 players have split and have the same hands, they would both win on both hands providing no other hands beat them, ie:

Bob, 21, Pontoon
Bob, 18, Normal
Dave, 21, Pontoon
Dave, 18, Normal

Would pay Bob and Dave on both hands, but if Kevin had a 19 hand, Bob and Dave would only win on their pontoons.
