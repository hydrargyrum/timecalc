
import datetime
import re
import sys

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
		mtc = re.match(r'(.*)_\d$', k)
		if mtc:
			newkey = mtc.expand(r'\1')
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
		self.message = 'Expected no tokens after token %s but got %s' % (self.after_token, self.bad_token)

class SyntaxError(ParserException):
	pass

class BadOperandException(ParserException):
	def __init__(self, operator=None, *a, **kw):
		ParserException.__init__(self, *a, **kw)
		self.operator = operator
		self.message = 'Unsupported operator %r between %s and %s' % (self.operator, self.after_token, self.bad_token)

class CombinedException(ParserException):
	def __init__(self, *a, **kw):
		ParserException.__init__(self, *a, **kw)
		self.message = 'Cannot combine 2 similar %s items: %s and %s' % (self.after_token.type, self.after_token, self.bad_token)


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
			if start + 1 < end and self.tokens[start + 1].type == 'datetime':
				tok = Datetime.combine(self.tokens[start], self.tokens[start + 1])
				return tok, start + 2
			return self.tokens[start], start + 1
		elif self.tokens[start].type == 'factor':
			return self.tokens[start], start + 1
		assert False


dur_text_re = re.compile(
r"(?:"
	r"(?P<years>\d+)"
	r"\s*"
	r"(?:yrs|yr|year|years|y)"
	r"(?:[,\s]\s*|$)"
r")|(?:"
	r"(?P<months>\d+)"
	r"\s*"
	r"(?:mon|mons|month|months)"
	r"(?:[,\s]\s*|$)"
r")|(?:"
	r"(?P<weeks>\d+)"
	r"\s*"
	r"(?:w|wk|wks|week|weeks)"
	r"(?:[,\s]\s*|$)"
r")|(?:"
	r"(?P<days>\d+)"
	r"\s*"
	r"(?:d|day|days)"
	r"(?:[,\s]\s*|$)"
r")|(?:"
	r"(?P<hours>\d+)"
	r"\s*"
	r"(?:h|hr|hrs|hour|hours)"
	r"(?:[,\s]\s*|$)"
r")|(?:"
	r"(?P<minutes>\d+)"
	r"\s*"
	r"(?:m|min|mins|minute|minutes)"
	r"(?:[,\s]\s*|$)"
r")|(?:"
	r"(?P<seconds>\d+)"
	r"\s*"
	r"(?:s|sec|secs|second|seconds)"
	r"(?:[,\s]\s*|$)"
r")|(?:"
	r"(?P<milliseconds>\d+)"
	r"\s*"
	r"(?:ms|milli|millis|millisecond|milliseconds)"
	r"(?:[,\s]\s*|$)"
r")")


duration_re = re.compile("(?P<duration>%s)" % dur_text_re.pattern)

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

	def timedelta(self):
		days = self.items.get('years') * 365 + self.items.get('months') * 30 + self.items.get('weeks') * 7 + self.items.get('days')
		seconds = self.items.get('hours') * 3600 + self.items.get('minutes') * 60 + self.items.get('seconds')
		return datetime.timedelta(days=days, seconds=seconds, microseconds=self.items.get('milliseconds') * 1000)

	def set_timedelta(self, delta):
		factor = 1
		if delta < datetime.timedelta():
			factor = -1
			delta = -delta

		days = delta.days
		self.items['years'], days = divmod(days, 365)
		self.items['months'], days = divmod(days, 30)
		self.items['weeks'], days = divmod(days, 7)
		self.items['days'] = days

		seconds = delta.seconds
		self.items['hours'], seconds = divmod(seconds, 3600)
		self.items['minutes'], seconds = divmod(seconds, 60)
		self.items['seconds'] = seconds

		self.items['milliseconds'] = delta.microseconds / 1000

		for unit in self.units:
			self.items[unit] *= factor

	def __add__(self, other):
		if other.type == 'duration':
			new = Duration()
#			for unit in self.units:
#				new.items[unit] = self.items.get(unit) + other.items.get(unit)
			new.set_timedelta(self.timedelta() + other.timedelta())
			return new
		elif other.type == 'datetime':
			return other + self

		raise BadOperandException('+', self, other)

	def __sub__(self, other):
		if other.type == 'duration':
			new = Duration()
#			for unit in self.units:
#				new.items[unit] = self.items.get(unit) - other.items.get(unit)
			new.set_timedelta(self.timedelta() - other.timedelta())
			return new

		raise BadOperandException('-', self, other)

	def merge(self, other):
		new = Duration()
		for unit in self.units:
			if self.items.get(unit) and other.items.get(unit):
				raise CombinedException(self, other)
			new.items[unit] = self.items.get(unit) + other.items.get(unit)
		return new

	def _plural(self, q, u):
		if q == 1:
			u = u[:-1]
		return '%s %s' % (q, u)

	def __str__(self):
		prefix = ''
		if self.timedelta() < datetime.timedelta():
			prefix = '- '
		return '%s%s' % (prefix, ', '.join(self._plural(abs(self.items[unit]), unit) for unit in self.units if self.items[unit]))

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


op_re = re.compile(r"(?P<op>[-+*()])")

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
r"(?P<dt_day>"
	r"(?P<date_lit>today)|"
	r"(?P<year>\d{2,4})(?P<_datesep>[/-]?)(?P<month>\d{1,2})(?P=_datesep)(?P<day>\d{1,2})"
r")")
time_re = re.compile(
r"(?P<dt_time>"
	r"(?P<hour>\d{2})(?P<_timesep>:?)(?P<minute>\d{2})(?:(?P=_timesep)(?P<second>\d{2}))?\s*(?P<ampm>am|pm)?"
r")")

datetime_re = re.compile(r'(?P<datetime>%s|%s)' % (date_re.pattern, time_re.pattern))

class Datetime:
	type = 'datetime'
	units = 'year month day hour minute second'.split()

	def __init__(self, d=None):
		d = tweak_dict(d or {})

		self.items = {}
		for unit in self.units:
			self.items[unit] = int(d.get(unit, 0))
		ampm = d.get('ampm')
		if ampm:
			if ampm == 'am' and self.items['hour'] == 12:
				self.items['hour'] = 0
			elif ampm == 'pm' and self.items['hour'] != 12:
				self.items['hour'] += 12

	@classmethod
	def combine(cls, a, b):
		res = Datetime()
		for unit in cls.units:
			if a.items.get(unit) and b.items.get(unit):
				raise CombinedException(a, b)
			res.items[unit] = a.items.get(unit) + b.items.get(unit)
		return res

	def datetime(self):
		return datetime.datetime(self.items['year'], self.items['month'], self.items['day'], self.items['hour'], self.items['minute'], self.items['second'])

	def set_datetime(self, dt):
		for unit in self.units:
			self.items[unit] = getattr(dt, unit)

	def __mul__(self, other):
		raise BadOperandException('*', self, other)

	def __add__(self, other):
		if other.type == 'duration':
			return self._add_duration(other, True)

		raise BadOperandException('+', self, other)

	def _add_duration(self, other, positive):
			new = Datetime()
			dt = self.datetime()
			delta_args = {}
			for unit in ('weeks', 'days', 'hours', 'minutes', 'seconds', 'milliseconds'):
				delta_args[unit] = other.items.get(unit)
			delta = datetime.timedelta(**delta_args)

			if positive:
				dt += delta
				year, month = divmod(dt.month + other.items.get('months') - 1, 12)
				year += dt.year + other.items.get('years')
			else:
				dt -= delta
				year, month = divmod(dt.month - other.items.get('months') - 1, 12)
				year += dt.year - other.items.get('years')

			dt = dt.replace(year=int(year), month=int(month + 1))
			new.set_datetime(dt)
			return new


	def __sub__(self, other):
		if other.type == 'duration':
			return self._add_duration(other, False)
		elif other.type == 'datetime':
			d_self = self.datetime()
			m_self = d_self.year * 12 + d_self.month
			d_other = other.datetime()
			m_other = d_other.year * 12 + d_other.month

			years, months = divmod(m_self - m_other, 12)
			#d_self = d_self.replace(year

			delta = self.datetime() - other.datetime()
			res = Duration()

			res.set_timedelta(delta)
			return res

			# negative timedelta still have positive sec and usec
			factor = 1
			if delta < datetime.timedelta():
				factor = -1
				delta = -delta

			res.items['days'] = delta.days * factor
			res.items['seconds'] = delta.seconds * factor
			res.items['milliseconds'] = delta.microseconds * factor / 1000

			return res

		raise BadOperandException('-', self, other)

	def __str__(self):
		return str(self.datetime())

	def __repr__(self):
		return '<Datetime %r>' % self.datetime()

whitespace_re = re.compile(r'(?P<ws>\s+)')

full_re = re.compile('|'.join([datetime_re.pattern, duration_re.pattern, factor_re.pattern, op_re.pattern, whitespace_re.pattern]))

def gen_token(tok):
	if tok.get('duration'):
		return Duration(tok)
	elif tok.get('op'):
		return Operator(tok)
	elif tok.get('factor'):
		return Factor(tok)
	elif tok.get('datetime'):
		return Datetime(tok)
	raise NotImplementedError()


def main():
	tokens = []
	start = 0
	input = sys.argv[1]

	while start < len(input):
		mtc = full_re.match(input, start)
		if mtc:
			if not mtc.group('ws'):
				token = gen_token(mtc.groupdict())
				tokens.append(token)
			assert mtc.start() != mtc.end()
			start = mtc.end()
		else:
			last = None
			if len(tokens):
				last = tokens[-1]
			raise SyntaxError(last, input[start:])

	res = Parser(tokens).parse()
	if res.type == 'operator':
		res = res.apply()

	print res


if __name__ == '__main__':
	main()
