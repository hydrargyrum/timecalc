
import re

textre = re.compile(
"(?:"
	"(?P<years>\d+)"
	"\s*"
	"(?:y|yr|yrs|year|years)"
	"(?:[,\s]\s*|$)"
")?(?:"
	"(?P<months>\d+)"
	"\s*"
	"(?:mon|mons|month|months)"
	"(?:[,\s]\s*|$)"
")?(?:"
	"(?P<weeks>\d+)"
	"\s*"
	"(?:w|wk|wks|week|weeks)"
	"(?:[,\s]\s*|$)"
")?(?:"
	"(?P<days>\d+)"
	"\s*"
	"(?:d|day|days)"
	"(?:[,\s]\s*|$)"
")?(?:"
	"(?P<hours>\d+)"
	"\s*"
	"(?:h|hr|hrs|hour|hours)"
	"(?:[,\s]\s*|$)"
")?(?:"
	"(?P<minutes>\d+)"
	"\s*"
	"(?:m|min|mins|minute|minutes)"
	"(?:[,\s]\s*|$)"
")?(?:"
	"(?P<seconds>\d+)"
	"\s*"
	"(?:s|sec|secs|second|seconds)"
	"(?:[,\s]\s*|$)"
")?(?:"
	"(?P<milliseconds>\d+)"
	"\s*"
	"(?:ms|milli|millis|millisecond|milliseconds)"
	"(?:[,\s]\s*|$)"
")?$")

colonre = re.compile(
"(?:(?P<days>\d+):)?"
"(?:(?P<hours>\d+):)?"
"(?:(?P<minutes>\d+):)?"
"(?P<seconds>\d+)"
"(?:[.,](?P<milliseconds>\d+))?$")

colonre = re.compile(
"(?:"
	"(?:"
		"(?:(?P<days>\d+):)?"
		"(?:(?P<hours>\d+):)"
	")?"
	"(?:(?P<minutes>\d+):)"
")?"
"(?P<seconds>\d+)"
"(?:[.,](?P<milliseconds>\d+))?$")


def parse(s, regex=colonre):
	match = regex.match(s)
	if not match:
		return {}
	
	result = {}
	matchd = match.groupdict()
	for k in matchd:
		if matchd[k]:
			result[k] = int(matchd[k])
	if matchd['milliseconds']:
		result['milliseconds'] = float('0.%s' % matchd['milliseconds']) * 1000
	return result

def duractiondict_to_seconds(d):
	get = lambda k: d.get(k, 0)
	days = get('days') + get('weeks') * 7 + get('months') * 30 + get('years') * 365
	secs = get('seconds') + get('minutes') * 60 + get('hours') * 3600 + days * 86400
	return secs + get('milliseconds') / 1000.


seconds_units = dict(seconds=1, minutes=60, hours=60*60, days=24*60*60, weeks=24*60*60*7, months=int(24*60*60*365.25/12), years=int(24*60*365.25))

def duractiondict_to_seconds_alt(d):
	month_s = int(86400 * 365.25 / 12)
	get = lambda k: d.get(k, 0)
	days = get('days') + get('weeks') * 7
	secs = get('seconds') + get('minutes') * 60 + get('hours') * 3600 + days * 86400 + get('years') * month_s * 12 + get('months') * month_s
	return secs + get('milliseconds') / 1000.

def duractiondict_to_seconds_alt(d):
	total = sum(d[k] * seconds_units[k] for k in d)
	return total + d.get('milliseconds', 0) / 1000.

def seconds_to_durationdict(secs):
	import math
	result = {}
	for unit in 'years months weeks days hours minutes'.split():
		ratio, secs = divmod(secs, seconds_units[unit])
		if ratio >= 1:
			result[unit] = ratio
	
	millis_s, secs = math.modf(secs)
	if secs:
		result['seconds'] = int(secs)
	if millis_s:
		result['milliseconds'] = int(millis_s * 1000)
	
	return result

def duractiondict_to_string(d):
	strings = []
	for unit in 'years months weeks days hours minutes seconds milliseconds'.split():
		if unit in d:
			if d[unit] > 1:
				strings.append('%d %s' % (d[unit], unit))
			else:
				strings.append('%d %s' % (d[unit], unit[:-1]))
	return ' '.join(strings)


if 0:
	print parse('10')
	print parse('10.005')
	print parse('20:10')
	print parse('30:20:10')
	print parse('40:30:20:10')
	print parse('40:30:20:10,005')

	print parse('10s', regex=textre)
	print parse('10s 5ms', regex=textre)
	print parse('20 minutes, 1 sec', regex=textre)
	print parse('30hrs, 20mins, 10s', regex=textre)
	print parse('40days 30seconds', regex=textre)
	print parse('40d 30h 20m 5ms', regex=textre)

	print duractiondict_to_seconds(parse('10'))
	print duractiondict_to_seconds(parse('10.005'))
	print duractiondict_to_seconds(parse('01:00:10.005'))
	print duractiondict_to_seconds(parse('1yr', regex=textre))
	print duractiondict_to_seconds(parse('1month', regex=textre))
	print duractiondict_to_seconds_alt(parse('1month', regex=textre))

def main():
	import sys
	if len(sys.argv) < 2:
		return
	if sys.argv[1] == '-d':
		print duractiondict_to_string(seconds_to_durationdict(float(sys.argv[2])))
	else:
		durationdict = parse(sys.argv[1], regex=textre)
		if not durationdict:
			durationdict = parse(sys.argv[1], regex=colonre)
		if not durationdict:
			return
		print duractiondict_to_seconds_alt(durationdict)

if __name__ == '__main__':
	main()
