import base64
import os
import time
import signal
import exceptions

import websocket
import xmltodict

import config
from debug import debugPrint, Flags
from isycodes import EVENT_CTRL
from logsupport import ConsoleWarning, ConsoleError

seq = 0
reportablecodes = ["DON", "DFON", "DOF", "DFOF", "ST", "OL", "RR", "CLISP", "CLISPH", "CLISPC", "CLIFS", "CLIMD",
				   "CLIHUM", "CLIHCS", "BRT", "DIM"]
watchlist = []
varlist = []
streamid = ''
watchstarttime = 0
ws = 0


def on_message(ws, message):
	global streamid, seq, varlist, watchlist
	m = xmltodict.parse(message)

	if 'SubscriptionResponse' in m:
		sr = m['SubscriptionResponse']
		if streamid <> sr['SID']:
			streamid = sr['SID']
			config.fromDaemon.put(("Log", "Now using event stream: " + streamid, ConsoleWarning))
			print 'StreamID: ', streamid

	elif 'Event' in m:
		e = m['Event']

		esid = e['@sid']
		if streamid <> esid:
			config.fromDaemon.put(("Log", "Now using event stream: " + str(esid), ConsoleWarning))
			streamid = esid  # todo this can't happen - change of streamid without warning

		eseq = int(e['@seqnum'])
		if seq <> eseq:
			config.fromDaemon.put(
				("Log", "Event mismatch - Expected: " + str(seq) + " Got: " + str(eseq), ConsoleWarning))
			# todo indicates a missed event - so should rebase the data?
			seq = eseq + 1
		else:
			seq += 1

		while not config.toDaemon.empty():
			msg = config.toDaemon.get()
			if len(msg) == 0:
				debugPrint('DaemonCtl', 'Empty message from console: ')
			elif msg[0] == 'flagchange':
				Flags[msg[1]] = msg[2]
			elif msg[0] == 'Status':
				watchlist = msg[1:]
				debugPrint('DaemonCtl', time.time(), "New watchlist(watcher): ", watchlist)
			elif msg[0] == 'Vars':
				varlist = msg[1:]
				debugPrint('DaemonCtl', "New varlist(watcher): ", varlist)
			else:
				debugPrint('DaemonCtl', 'Bad message from console: ', msg)

		eventcode = e['control']
		if eventcode in EVENT_CTRL:
			prcode = EVENT_CTRL[eventcode]
		else:
			prcode = "**" + eventcode + "**"

		action = e['action']
		node = e['node']
		eI = e['eventInfo']

		if (eventcode in reportablecodes) and node in watchlist:
			debugPrint('DaemonCtl', time.time(), "Status update in stream: ", eseq, ":", prcode, " : ", node, " : ", eI,
					   " : ", action)
			debugPrint('DaemonStream', time.time(), "Raw stream item: ", e)

			if action is dict:
				debugPrint('DaemonStream', "V5 stream - pull up action value: ", action)
				action = action["#text"]  # todo the new xmltodict will return as data['action']['#text']
			config.fromDaemon.put(("Node", node, action, seq))
			debugPrint('DaemonCtl', "Qsize at daemon ", config.fromDaemon.qsize())
		elif (prcode == 'Trigger') and (action == '6'):
			vinfo = eI['var']
			vartype = int(vinfo['@type'])
			varid = int(vinfo['@id'])
			varval = int(vinfo['val'])
			debugPrint('DaemonCtl', 'Var change:', ('Unkn', 'Integer', 'State')[vartype], ' variable ', varid,
					   ' set to ', varval)
			if (vartype, varid) in varlist:
				config.fromDaemon.put(("VarChg", vartype, varid, varval))
				debugPrint('DaemonCtl', 'Qsize at daemon', config.fromDaemon.qsize(), ' VarChg:', vartype, ':', varid,
						   ':', varval)
		else:
			debugPrint('DaemonStream', time.time(), "Other  update in stream: ", eseq, ":", prcode, " : ",
					   node, " : ", eI, " : ", action)
			debugPrint('DaemonStream', time.time(), "Raw stream item: ", m)

		del e['@seqnum']
		del e['@sid']
		del e['control']
		del e['action']
		del e['node']
		del e['eventInfo']
		if e:
			config.fromDaemon.put(("Log", "Extra info in event: " + str(e), ConsoleWarning))

	else:
		config.fromDaemon.put(("Log", "Strange item in event stream: " + str(m), ConsoleWarning))


def on_error(ws, error):
	if type(error) is not exceptions.SystemExit:
		config.fromDaemon.put(("Log", "Websocket error: " + type(error) + str(error), ConsoleError))
		# todo should fatal out?
		print 'errws', error

def on_close(ws):
	debugPrint('DaemonCtl', "Websocket stream closed")

def on_open(ws):
	debugPrint('DaemonCtl', "Websocket stream opened")

def Watcher():
	global watchlist, varlist, ws

	def signalhandler(sig, frame):
		global ws
		t = os.getpid()
		debugPrint('DaemonCtl', "Watcher daemon signalled to terminate - pid: ", t)
		ws.close()
		exit()
		print 'huh?'


	a = base64.b64encode(config.ISYuser + ':' + config.ISYpassword)
	watchstarttime = time.time()
	watchlist = []
	varlist = []
	debugPrint('DaemonCtl', "Watcher: ", watchstarttime, os.getpid())
	signal.signal(signal.SIGTERM, signalhandler)
	config.Daemon_pid = os.getpid()
	# websocket.enableTrace(True)
	ws = websocket.WebSocketApp('ws://' + config.ISYaddr + '/rest/subscribe', on_message=on_message, on_error=on_error,
								on_close=on_close, on_open=on_open,
								subprotocols=['ISYSUB'], header={'Authorization': 'Basic ' + a})
	ws.run_forever()
