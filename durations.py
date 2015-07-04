
import sys
import re

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


def tweak_dict(d):
	for k in d.keys():
		if d[k] is None:
			del d[k]

	for k in d.keys():
		mtc = re.search(r'_\d$', k)
		if mtc:
			newkey = mtc.expand('')
			d[newkey] = d[k]
			del d[k]
	return d


class ParserException(Exception):
	def __init__(self, after_token=None, bad_token=None):
		Exception.__init__(self)
		self.after_token = None
		self.bad_token = None

class ExtraDataException(ParserException):
	def __init__(self, *a, **kw):
		ParserException.__init__(self, *a, **kw)
		self.message = 'bad'

class UnexpectedTokenException(ParserException):
	pass

class BadOperandException(ParserException):
	def __init__(self, operator=None, *a, **kw):
		ParserException.__init__(self, *a, **kw)
		self.operator = operator

class Parser:
	def __init__(self, tokens):
		self.tokens = tokens

	def parse(self):
		e, end = self.parse_expr(0, len(self.tokens))
		if end != len(self.tokens):
			raise ExtraDataException(self.tokens[end - 1], self.tokens[end])
		return e

	def parse_expr(self, start, end):
		t, t_end = self.parse_term(start, end)
		if not len(self.tokens[t_end:]):
			return t, t_end
		elif self.tokens[t_end].type != 'operator' or self.tokens[t_end].op not in '+-':
			return t, t_end

		e, e_end = self.parse_expr(t_end + 1, end)
		op = self.tokens[t_end]
		op.operands.extend([t, e])
		return op, e_end

	def parse_term(self, start, end):
		f, f_end = self.parse_factor(start, end)
		if not len(self.tokens[f_end:]):
			return f, f_end
		elif self.tokens[f_end].type != 'operator' or self.tokens[f_end].op != '*':
			return f, f_end

		t, t_end = self.parse_factor(f_end + 1, end)
		op = self.tokens[f_end]
		op.operands.extend([f, t])
		return op, t_end

	def parse_factor(self, start, end):
		if self.tokens[start].type == 'operator' and self.tokens[start].op == '(':
			e, e_end = self.parse_expr(start + 1, end)
			assert self.tokens[e_end].type == 'operator' and self.tokens[e_end].op == ')'
			return e, e_end + 1
		elif self.tokens[start].type == 'duration':
			durations = []
			s = start
			while s < end:
				if self.tokens[s].type != 'duration':
					break
				durations.append(self.tokens[s])
				s += 1
			dsum = sum(durations, Duration())
			return dsum, s
		elif self.tokens[start].type == 'datetime':
			return self.tokens[start], start + 1
		elif self.tokens[start].type == 'factor':
			return self.tokens[start], start + 1
		assert False


dur_text_re = re.compile(
"(?:"
	"(?P<years>\d+)"
	"\s*"
	"(?:yrs|yr|year|years|y)"
	"(?:[,\s]\s*|$)"
")|(?:"
	"(?P<months>\d+)"
	"\s*"
	"(?:mon|mons|month|months)"
	"(?:[,\s]\s*|$)"
")|(?:"
	"(?P<weeks>\d+)"
	"\s*"
	"(?:w|wk|wks|week|weeks)"
	"(?:[,\s]\s*|$)"
")|(?:"
	"(?P<days>\d+)"
	"\s*"
	"(?:d|day|days)"
	"(?:[,\s]\s*|$)"
")|(?:"
	"(?P<hours>\d+)"
	"\s*"
	"(?:h|hr|hrs|hour|hours)"
	"(?:[,\s]\s*|$)"
")|(?:"
	"(?P<minutes>\d+)"
	"\s*"
	"(?:m|min|mins|minute|minutes)"
	"(?:[,\s]\s*|$)"
")|(?:"
	"(?P<seconds>\d+)"
	"\s*"
	"(?:s|sec|secs|second|seconds)"
	"(?:[,\s]\s*|$)"
")|(?:"
	"(?P<milliseconds>\d+)"
	"\s*"
	"(?:ms|milli|millis|millisecond|milliseconds)"
	"(?:[,\s]\s*|$)"
")")



dur_colon_re = re.compile(
"(?:(?P<days>\d+):)?"
"(?:(?P<hours>\d+):)?"
"(?:(?P<minutes>\d+):)?"
"(?P<seconds>\d+)"
"(?:[.,](?P<milliseconds>\d+))?$")

dur_colon_re = re.compile(
"(?:"
	"(?:"
		"(?:(?P<days_2>\d+):)?"
		"(?:(?P<hours_2>\d+):)"
	")?"
	"(?:(?P<minutes_2>\d+):)"
")?"
"(?P<seconds_2>\d+)"
"(?:[.,](?P<milliseconds_2>\d+))?")

duration_re = re.compile("(?P<duration>(?=.)%s)" % '|'.join([dur_text_re.pattern]))# colon_re.pattern]))

class Duration:
	units = 'years months weeks days hours minutes seconds milliseconds'.split()
	type = 'duration'

	def __init__(self, d=None):
		if not d:
			d = {}
		d = tweak_dict(d)

		self.items = {}
		for unit in self.units:
			self.items[unit] = float(d.get(unit, 0))

	def __add__(self, other):
		if other.type == 'duration':
			new = Duration()
			for unit in self.units:
				new.items[unit] = self.items.get(unit) + other.items.get(unit)
			return new
		elif other.type == 'datetime':
			pass

		raise BadOperandException('+', self, other)

	def __sub__(self, other):
		if other.type == 'duration':
			new = Duration()
			for unit in self.units:
				new.items[unit] = self.items.get(unit) - other.items.get(unit)
			return new

		raise BadOperandException('-', self, other)

	def merge(self, other):
		new = Duration()
		for unit in self.units:
			pass

	def __repr__(self):
		parts = ['%s %s' % (self.items.get(u), u) for u in self.units if self.items.get(u)]
		return '<Duration %s>' % ', '.join(parts)

	def __mul__(self, other):
		if other.type != 'factor':
			raise BadOperandException('*', self, other)

		d = Duration()
		for unit in self.units:
			d.items[unit] = self.items[unit] * other.factor
		return d



op_re = re.compile(r"(?P<op>[-+*/()])")

class Operator:
	type = 'operator'

	def __init__(self, d):
		self.op = d['op']
		self.operands = []

	def __repr__(self):
		return '<Operator type=%s operands=%r>' % (self.op, self.operands)

	def apply(self):
		left, right = self.operands
		if left.type == 'operator':
			left = left.apply()
		if right.type == 'operator':
			right = right.apply()

		if self.op == '+':
			return left + right
		elif self.op == '-':
			return left - right
		elif self.op == '*':
			return left * right
		assert False


factor_re = re.compile(r"(?P<factor>\d+)")

class Factor:
	type = 'factor'

	def __init__(self, d=None):
		d = d or {}
		self.factor = float(d.get('factor'))

	def __add__(self, other):
		if other.type == 'factor':
			return Factor({'factor': self.factor + other.factor})
		raise BadOperandException('+', self, other)

	def __sub__(self, other):
		if other.type == 'factor':
			return Factor({'factor': self.factor - other.factor})
		raise BadOperandException('-', self, other)

	def __mul__(self, other):
		if other.type == 'factor':
			return Factor({'factor': self.factor * other.factor})
		elif other.type == 'duration':
			return other * self
                raise BadOperandException('*', self, other)

	def __repr__(self):
		return '<Factor=%s>' % self.factor


date_re = re.compile(
"(?P<dt_day>"
	"(?P<date_lit>today)|"
	"(?P<year>\d{2,4})(?P<_datesep>/?)(?P<month>\d{1,2})(?P=_datesep)(?P<day>\d{1,2})"
"\s*)")
time_re = re.compile(
"(?P<dt_time>"
	"(?P<hour>\d{2})(?P<_timesep>:?)(?P<minute>\d{2})(?:(?P=_timesep)(?P<second>\d{2}))?|"
	"(?P<hour_2>\d{1,2})(?::(?P<minute_2>\d{1,2}))?\s*(?P<ampm>am|pm)"
"\s*)")

datetime_re = re.compile(r'(?P<datetime>%s)' % date_re.pattern)

class Datetime:
	type = 'datetime'
	units = 'year month day hour minute second'.split()

	def __init__(self, d):
		d = tweak_dict(d)

		for unit in self.units:
			setattr(self, unit, int(d.get(unit, 0)))
		ampm = d.get('ampm')
		if ampm:
			if ampm == 'am' and self.hour == 12:
				self.hour = 0
			elif ampm == 'pm' and self.hour != 12:
				self.hour += 12

	def __mul__(self, other):
		raise BadOperandException('*', self, other)

	def __add__(self, other):
		if other.type == 'duration':
			return other + self
		raise BadOperandException('+', self, other)

	def __sub__(self, other):
		if other.type == 'duration':
			pass
		raise BadOperandException('-', self, other)

		

full_re = re.compile('|'.join([datetime_re.pattern, duration_re.pattern, factor_re.pattern, op_re.pattern]))

def gen_token(tok):
	if tok.get('duration'):
		return Duration(tok)
	elif tok.get('op'):
		return Operator(tok)
	elif tok.get('factor'):
		return Factor(tok)
	elif tok.get('datetime'):
		return Datetime(tok)
	assert False


def main():
	tokens = []
	for mtc in full_re.finditer(sys.argv[1]):
		print mtc.group(0)
		tokens.append(gen_token(mtc.groupdict()))
	print tokens
	res = Parser(tokens).parse()
	if res.type == 'operator':
		print res
		res = res.apply()
	print res


if __name__ == '__main__':
	main()
