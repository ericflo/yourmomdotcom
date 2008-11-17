import sys
import os
import random
import re

from collections import defaultdict

from twisted.words.protocols import irc
from twisted.internet import reactor, protocol

markov = defaultdict(list)
STOP_WORD = "\n"

def add_to_brain(msg, chain_length, write_to_file=False):
    if write_to_file:
        f = open('training_text.txt', 'a')
        f.write(msg + '\n')
        f.close()
    buf = [STOP_WORD] * chain_length
    for word in msg.split():
        markov[tuple(buf)].append(word)
        del buf[0]
        buf.append(word)
    markov[tuple(buf)].append(STOP_WORD)

def generate_sentence(msg, chain_length, max_words=10000):
    buf = msg.split()[:chain_length]
    if len(msg.split()) > chain_length:
        message = buf[:]
    else:
        message = []
        for i in xrange(chain_length):
            message.append(random.choice(markov[random.choice(markov.keys())]))
    for i in xrange(max_words):
        try:
            next_word = random.choice(markov[tuple(buf)])
        except IndexError:
            continue
        if next_word == STOP_WORD:
            break
        message.append(next_word)
        del buf[0]
        buf.append(next_word)
    return ' '.join(message)

class MomBot(irc.IRCClient):
    def _get_nickname(self):
        return self.factory.nickname
    nickname = property(_get_nickname)
    
    def signedOn(self):
        self.join(self.factory.channel)
        print "Signed on as %s." % (self.nickname,)
    
    def joined(self, channel):
        print "Joined %s." % (channel,)
    
    def privmsg(self, user, channel, msg):
        if not user:
            return
        if self.nickname in msg:
            msg = re.compile(self.nickname + "[:,]* ?", re.I).sub('', msg)
            prefix = "%s: " % (user.split('!', 1)[0], )
        else:
            prefix = ''
        add_to_brain(msg, self.factory.chain_length, write_to_file=True)
        if prefix or random.random() <= self.factory.chattiness:
            sentence = generate_sentence(msg, self.factory.chain_length,
                self.factory.max_words)
            if sentence:
                self.msg(self.factory.channel, prefix + sentence)

class MomBotFactory(protocol.ClientFactory):
    protocol = MomBot
    
    def __init__(self, channel, nickname='YourMomDotCom', chain_length=3,
        chattiness=1.0, max_words=10000):
        self.channel = channel
        self.nickname = nickname
        self.chain_length = chain_length
        self.chattiness = chattiness
        self.max_words = max_words
    
    def clientConnectionLost(self, connector, reason):
        print "Lost connection (%s), reconnecting." % (reason,)
        connector.connect()
    
    def clientConnectionFailed(self, connector, reason):
        print "Could not connect: %s" % (reason,)

if __name__ == "__main__":
    try:
        chan = sys.argv[1]
    except IndexError:
        print "Please specify a channel name."
        print "Example:"
        print "  python yourmomdotcom.py django-hotclub"
    chain_length = 2
    if os.path.exists('training_text.txt'):
        f = open('training_text.txt', 'r')
        for line in f:
            add_to_brain(line, chain_length)
        print 'Brain Reloaded'
        f.close()
    reactor.connectTCP('irc.freenode.net', 6667, MomBotFactory('#' + chan, 'YourMomDotCom', chain_length, chattiness=0.05))
    reactor.run()