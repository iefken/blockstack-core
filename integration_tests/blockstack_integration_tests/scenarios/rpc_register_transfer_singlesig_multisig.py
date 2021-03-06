#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Blockstack
    ~~~~~
    copyright: (c) 2014-2015 by Halfmoon Labs, Inc.
    copyright: (c) 2016 by Blockstack.org

    This file is part of Blockstack

    Blockstack is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Blockstack is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.
    You should have received a copy of the GNU General Public License
    along with Blockstack. If not, see <http://www.gnu.org/licenses/>.
""" 

import testlib
import pybitcoin
import time
import json
import sys
import blockstack_client
import virtualchain

# activate multisig
"""
TEST ENV BLOCKSTACK_EPOCH_1_END_BLOCK 250
TEST ENV BLOCKSTACK_EPOCH_2_NAMESPACE_LIFETIME_MULTIPLIER 1
"""

wallets = [
    testlib.Wallet( "5JesPiN68qt44Hc2nT8qmyZ1JDwHebfoh9KQ52Lazb1m1LaKNj9", 100000000000 ),
    testlib.Wallet( "5KHqsiU9qa77frZb6hQy9ocV7Sus9RWJcQGYYBJJBb2Efj1o77e", 100000000000 ),
    testlib.Wallet( "5KEpiSRr1BrT8vRD7LKGCEmudokTh1iMHbiThMQpLdwBwhDJB1T", 5500 ),
    testlib.Wallet( "5JuVsoS9NauksSkqEjbUZxWwgGDQbMwPsEfoRBSpLpgDX1RtLX7", 5500 ),
    testlib.MultisigWallet(2, "5JPrkpfLT3rDf1Lgm1DpA2Cfepwf9wCtEbDx1HSEdd4J2R5YMxZ", "5JiALcfvzFsKcvLnHf7ECgLdp6FxbcAXB1GPvEYP7HeigbDCQ9E", "5KScD5XL5Hj83Yjvm3u4HD78vSYwFRyq9StTLPnrWrCTGiqTvVP")
]

consensus = "17ac43c1d8549c3181b200f1bf97eb7d"
zonefile_hash = None

def scenario( wallets, **kw ):

    global zonefile_hash

    testlib.blockstack_namespace_preorder( "test", wallets[1].addr, wallets[0].privkey )
    testlib.next_block( **kw )

    testlib.blockstack_namespace_reveal( "test", wallets[1].addr, 52595, 250, 4, [6,5,4,3,2,1,0,0,0,0,0,0,0,0,0,0], 10, 10, wallets[0].privkey )
    testlib.next_block( **kw )

    testlib.blockstack_namespace_ready( "test", wallets[1].privkey )
    testlib.next_block( **kw )

    wallet = testlib.blockstack_client_initialize_wallet( "0123456789abcdef", wallets[2].privkey, wallets[3].privkey, wallets[0].privkey )
    resp = testlib.blockstack_cli_register( "foo.test", "0123456789abcdef" )
    if 'error' in resp:
        print >> sys.stderr, json.dumps(resp, indent=4, sort_keys=True)
        return False
   
    # wait for the preorder to get confirmed
    for i in xrange(0, 12):
        testlib.next_block( **kw )

    # wait for the poller to pick it up
    print >> sys.stderr, "Waiting 10 seconds for the backend to submit the register"
    time.sleep(15)

    # wait for the register to get confirmed 
    for i in xrange(0, 12):
        # warn the serialization checker that this changes behavior from 0.13
        print "BLOCKSTACK_SERIALIZATION_CHECK_IGNORE value_hash"
        sys.stdout.flush()
        
        testlib.next_block( **kw )

    print >> sys.stderr, "Waiting 10 seconds for the backend to acknowledge registration"
    time.sleep(15)

    # wait for update to get confirmed 
    for i in xrange(0, 12):
        # warn the serialization checker that this changes behavior from 0.13
        print "BLOCKSTACK_SERIALIZATION_CHECK_IGNORE value_hash"
        sys.stdout.flush()
        
        testlib.next_block( **kw )

    print >> sys.stderr, "Waiting 10 seconds for the backend to acknowledge update"
    time.sleep(15)

    # transfer to a new address 
    resp = testlib.blockstack_cli_transfer( "foo.test", wallets[4].addr, "0123456789abcdef" )

    if 'error' in resp:
        print >> sys.stderr, "transfer error: %s" % resp['error']
        return False

    # wait for it to go through 
    for i in xrange(0, 12):
        # warn the serialization checker that this changes behavior from 0.13
        print "BLOCKSTACK_SERIALIZATION_CHECK_IGNORE value_hash"
        sys.stdout.flush()

        testlib.next_block( **kw )

    print >> sys.stderr, "Waiting 10 seconds for the backend to acknowledge the transfer"
    time.sleep(15)

    testlib.next_block(**kw)


def check( state_engine ):

    global zonefile_hash

    # not revealed, but ready 
    ns = state_engine.get_namespace_reveal( "test" )
    if ns is not None:
        print "namespace reveal exists"
        return False 

    ns = state_engine.get_namespace( "test" )
    if ns is None:
        print "no namespace"
        return False 

    if ns['namespace_id'] != 'test':
        print "wrong namespace"
        return False 
    
    # registered 
    name_rec = state_engine.get_name( "foo.test" )
    if name_rec is None:
        print "name does not exist"
        return False 

    # owned by
    owner_address = wallets[4].addr
    if name_rec['address'] != owner_address or name_rec['sender'] != virtualchain.make_payment_script(owner_address):
        print "sender is wrong"
        return False 

    # all queues are drained 
    queue_info = testlib.blockstack_client_queue_state()
    if len(queue_info) > 0:
        print "Still in queue:\n%s" % json.dumps(queue_info, indent=4, sort_keys=True)
        return False

    # doesn't show up in listing
    names_owned = testlib.blockstack_cli_names()
    if 'error' in names_owned:
        print "rpc names: %s" % names_owned['error']
        return False

    if len(names_owned['names_owned']) > 0:
        print "still owned: %s" % names_owned['names_owned']
        return False
    
    return True
