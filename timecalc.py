#!/usr/bin/env python
# license: this file is licensed under the WTFPLv2 license (see COPYING.wtfpl)

import datetime
import re
import sys

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
		self.after_token = after_token
		self.bad_token = bad_token

	def location_str(self):
		if self.after_token and self.after_token.mtc:
			mtc = self.after_token.mtc
			p1 = mtc.string[max(0, mtc.end() - 15):mtc.end()]
			if mtc.end() - 15 > 0:
				p1 = '...' + p1
			p2 = mtc.string[mtc.end():mtc.end() + 15]
			if mtc.end() + 15 < len(mtc.string):
				p2 = p2 + '...'
			return (p1 + p2, len(p1) * ' ' + '^')

		return ()

class ExtraDataException(ParserException):
	def __init__(self, *a, **kw):
		ParserException.__init__(self, *a, **kw)

	def __str__(self):
		return 'Expected no more tokens after token %r but got %r' % (self.after_token, self.bad_token)

	def short_msg(self):
		return 'Expected no more tokens'

class SyntaxError(ParserException):
	def __str__(self):
		return 'Syntax error after token %r' % self.after_token

class BadOperandException(ParserException):
	def __init__(self, operator=None, *a, **kw):
		ParserException.__init__(self, *a, **kw)
		self.operator = operator

	def __str__(self):
		return 'Unsupported operator %r between %r and %r' % (self.operator, self.after_token, self.bad_token)

class CombinedException(ParserException):
	def __init__(self, *a, **kw):
		ParserException.__init__(self, *a, **kw)

	def __str__(self):
		return 'Cannot combine 2 similar %s items: %r and %r' % (self.after_token.type, self.after_token, self.bad_token)

class MissingToken(ParserException):
	def __str__(self):
		return 'Unexpected end of input after %r' % self.after_token

class UnexpectedTokenType(ParserException):
	def __str__(self):
		return 'Unexpected token type after %r: %r' % (self.after_token, self.bad_token)


class Parser:
	def __init__(self, tokens):
		self.tokens = tokens

	def parse(self):
		e, end = self.parse_expr(0, len(self.tokens))
		if end != len(self.tokens):
			raise ExtraDataException(self.tokens[end - 1], self.tokens[end])
		return e

	def _check_eof(self, start, end):
		if start >= end:
			raise MissingToken()

	def parse_expr(self, start, end):
		t, t_end = self.parse_term(start, end)
		if t_end >= end:
			return t, t_end
		elif self.tokens[t_end].type != 'operator' or self.tokens[t_end].op not in '+-':
			return t, t_end

		if t_end + 1 >= end:
			raise MissingToken(self.tokens[t_end])

		e, e_end = self.parse_expr(t_end + 1, end)
		op = self.tokens[t_end]
		op.operands.extend([t, e])
		return op, e_end

	def parse_term(self, start, end):
		f, f_end = self.parse_factor(start, end)
		if f_end >= end:
			return f, f_end
		elif self.tokens[f_end].type != 'operator' or self.tokens[f_end].op != '*':
			return f, f_end

		if f_end + 1 >= end:
			raise MissingToken(self.tokens[f_end])

		t, t_end = self.parse_factor(f_end + 1, end)
		op = self.tokens[f_end]
		op.operands.extend([f, t])
		return op, t_end

	def parse_factor(self, start, end):
		if self.tokens[start].type == 'operator' and self.tokens[start].op == '(':

			if start + 1 >= end:
				raise MissingToken(self.tokens[start])

			e, e_end = self.parse_expr(start + 1, end)

			if e_end >= end:
				raise MissingToken(self.tokens[e_end - 1])

			if self.tokens[e_end].type != 'operator' or self.tokens[e_end].op != ')':
				raise UnexpectedTokenType(self.tokens[e_end - 1], self.tokens[e_end])

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

	def __init__(self, d=None, mtc=None):
		self.mtc = mtc

		d = tweak_dict(d or {})

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
#		for unit in self.units:
#			d.items[unit] = self.items[unit] * other.factor
		delta = self.timedelta()
		d.set_timedelta(datetime.timedelta(delta.days * other.factor, delta.seconds * other.factor, delta.microseconds * other.factor))
		return d


op_re = re.compile(r"(?P<op>[-+*()])")

class Operator:
	type = 'operator'

	def __init__(self, d, mtc=None):
		self.mtc = mtc
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

	def __init__(self, d=None, mtc=None):
		self.mtc = mtc
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
	r"(?P<date_lit>today|now|epoch)|"
	r"(?P<year>\d{2,4})(?P<_datesep>[/-]?)(?P<month>\d{1,2})(?P=_datesep)(?P<day>\d{1,2})"
r")")
time_re = re.compile(
r"(?P<dt_time>"
	r"(?P<hour>\d{2})"
	r"(?:"
		r"(?P<_timesep>:?)(?P<minute>\d{2})(?:(?P=_timesep)(?P<second>\d{2}))?\s*(?P<ampm>am|pm)?|"
		r"\s*(?P<ampm_2>am|pm)"
	r")"
r")")

datetime_re = re.compile(r'(?P<datetime>%s|%s)' % (date_re.pattern, time_re.pattern))

class Datetime:
	type = 'datetime'
	units = 'year month day hour minute second'.split()

	def __init__(self, d=None, mtc=None):
		self.mtc = mtc

		d = tweak_dict(d or {})

		self.items = {}

		if d.get('date_lit') == 'now':
			self.set_datetime(datetime.datetime.now())
		elif d.get('date_lit') == 'today':
			self.set_datetime(datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))
		elif d.get('date_lit') == 'epoch':
			self.set_datetime(datetime.datetime(1970, 1, 1))
		else:
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
			new = Datetime()
			new.set_datetime(self.datetime() + other.timedelta())
			return new

		raise BadOperandException('+', self, other)

	def __sub__(self, other):
		if other.type == 'duration':
			new = Datetime()
			new.set_datetime(self.datetime() - other.timedelta())
			return new
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
		return '<Datetime %s>' % self.datetime()

whitespace_re = re.compile(r'(?P<ws>\s+)')

full_re = re.compile('|'.join([duration_re.pattern, datetime_re.pattern, factor_re.pattern, op_re.pattern, whitespace_re.pattern]))

def gen_token(mtc):
	tok = mtc.groupdict()
	if tok.get('duration'):
		return Duration(tok, mtc)
	elif tok.get('op'):
		return Operator(tok, mtc)
	elif tok.get('factor'):
		return Factor(tok, mtc)
	elif tok.get('datetime'):
		return Datetime(tok, mtc)
	raise NotImplementedError()


def do_apply(instring):
	tokens = []
	start = 0

	while start < len(instring):
		mtc = full_re.match(instring, start)
		if mtc:
			if not mtc.group('ws'):
				token = gen_token(mtc)
				tokens.append(token)
			assert mtc.start() != mtc.end()
			start = mtc.end()
		else:
			last = None
			if len(tokens):
				last = tokens[-1]
			raise SyntaxError(last)

	res = Parser(tokens).parse()
	if res.type == 'operator':
		res = res.apply()

	print res

def do_one(instring):
	try:
		do_apply(instring)
	except ParserException as e:
		print e
		print '\n'.join(e.location_str())

def repl():
	import readline

	while True:
		try:
			instring = raw_input('> ')
		except (KeyboardInterrupt, EOFError):
			print
			return
		if not instring:
			continue

		do_one(instring)

def main():
	if len(sys.argv) == 1:
		repl()
	elif len(sys.argv) == 2:
		do_one(sys.argv[1])
	else:
		print >> sys.stderr, 'usage: %s [EXPR]' % sys.argv[0]
		sys.exit(1)

if __name__ == '__main__':
	main()
