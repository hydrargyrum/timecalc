#!/usr/bin/env python
# coding: utf-8
# license: this file is licensed under the WTFPLv2 license (see COPYING.wtfpl)

import datetime
import re
import sys
from collections import OrderedDict

# {{{ parser lib

TERMINAL_CLASSES = []
NONTERMINAL_CLASSES = []

def register(cls):
	if cls.is_terminal:
		TERMINAL_CLASSES.append(cls)
	else:
		NONTERMINAL_CLASSES.append(cls)
	return cls

# {{{ lexer

class Terminal(object):
	is_terminal = True
	is_lazy = False
	re = None
	ignore = False

	def __init__(self, d=None, match=None):
		self.d = d
		self.match = match

	@classmethod
	def name(cls):
		return cls.__name__

	def __repr__(self):
		return '<%s %r>' % (self.name(), self.d)

	def pretty(self):
		return repr(self)


def create_terminal(re_string):
	class NewTerminal(Terminal):
		re = re.compile(re_string)

	return NewTerminal

literal_re = re.escape

def tweak_match_dict(d):
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
	reason = None

	def __init__(self, pos=None, text=None, after_token=None, token=None, exc=None):
		self.pos = pos
		self.text = text
		self.after_token = after_token
		self.token = token
		self.exc = exc

	@staticmethod
	def snippet_str(text, pos, context=30):
		prefix = suffix = ''
		start = pos - context
		end = pos + context

		# TODO gain some space if one side is shorter than context
		if start > 0:
			prefix = '...'
			start += 3
		else:
			start = 0
		if end < len(text):
			suffix = '...'
			end -= 3
		else:
			end = len(text)

		line1 = prefix + text[start:pos]
		line2 = len(line1) * ' ' + '^'
		line1 += text[pos:end] + suffix
		return '\n'.join([line1, line2])

	def location_str(self):
		if self.text:
			return self.snippet_str(self.text, self.pos)
		elif self.token:
			return self.snippet_str(self.token.match.string, self.token.match.start())
		elif self.after_token:
			return self.snippet_str(self.after_token.match.string, self.after_token.match.end())

	def __str__(self):
		if exc:
			reason = '%s: %s' % (self.reason, exc)
		else:
			reason = self.reason
		return '\n'.join([reason, self.location_str()])

class BadToken(ParserException):
	reason = 'Unrecognized token'

def do_lexer(text):
	tokens = []
	start = 0

	while start < len(text):
		best = None
		best_cls = None
		best_match = None
		for cls in TERMINAL_CLASSES:
			mtc = cls.re.match(text, start)
			if mtc:
				new = mtc.end()
			if mtc and (not best or best < new):
				best_match = mtc
				best_cls = cls
				best = new

		if best_match:
			assert best_match.start() != best_match.end()

			if not best_cls.ignore:
				d = tweak_match_dict(best_match.groupdict())
				token = best_cls(d, match=best_match)
				tokens.append(token)
			start = best_match.end()
		else:
			raise BadToken(pos=start, text=text)
	return tokens


# }}}
# {{{ parser

class NonTerminal(object):
	is_terminal = False
	rules = None
	is_dummy = False
	is_lazy = False

	def __init__(self, parts):
		self.parts = parts

	@classmethod
	def name(cls):
		return cls.__name__

	def __repr__(self):
		return '<%s %r>' % (self.name(), self.parts)

	def pretty(self):
		return self.name() + '\n' + '\n'.join('  ' + line for part in self.parts for line in part.pretty().split('\n'))


class Lazy(NonTerminal):
	is_lazy = True

	def __init__(self, name):
		self.name = name

	def lookup(self):
		for s in NONTERMINAL_CLASSES:
			if s.__name__ == self.name:
				return s
		assert False, '%s not found' % self.name


def rule(*syms):
	def deco(func):
		func.syms = syms
		return staticmethod(func)

	return deco

class BadRule(ParserException):
	pass

class BadSymbol(ParserException):
	pass

class ExtraTokensError(ParserException):
	reason = 'Unexpected data after expression'

class NotEnoughTokens(ParserException):
	reason = 'Unexpected end of string'

class ParserSyntaxError(ParserException):
	reason = 'Unexpected symbol'


def parse_rule(syms, tokens, start):
	parts = []
	consumed = False
	try:
		for sym in syms:
			if sym.is_terminal:
				if start >= len(tokens):
					raise BadRule()
				elif isinstance(tokens[start], sym):
					part = tokens[start]
					start = start + 1
				else:
					raise BadRule()
			else:
				start, part = parse_nonterm(sym, tokens, start)
			parts.append(part)
			consumed = True
		return start, parts
	except (BadRule, BadSymbol):
		if consumed:
			if start >= len(tokens):
				raise NotEnoughTokens(after_token=tokens[-1])
			raise ParserSyntaxError(token=tokens[start])
		raise

def parse_nonterm(nonterm, tokens, start):
	lazy_replace = lambda t: t.lookup() if t.is_lazy else t

	for rulename in sorted(dir(nonterm)):
		cb = getattr(nonterm, rulename)
		if not (callable(cb) and hasattr(cb, 'syms')):
			continue
		try:
			syms = map(lazy_replace, cb.syms)
			start, parts = parse_rule(syms, tokens, start)
		except (BadRule, BadSymbol):
			pass
		else:
			break
	else:
		raise BadSymbol()
	return start, cb(*parts)

def do_parser(entry, tokens):
	start, ast = parse_nonterm(entry, tokens, 0)
	if start < len(tokens):
		raise ExtraTokensError(token=tokens[start])
	return ast

# }}}
# }}}
# {{{ timecalc parser

@register
class Number(Terminal):
	type = 'number'
	re = re.compile(r'(?P<number>-?\d+(?:\.\d*)?)')

	def __init__(self, d=None, match=None, n=None):
		super(Number, self).__init__(d, match)
		self.n = n

	def value(self):
		if self.n is not None:
			return self.n
		return float(self.d['number'])

	def __add__(self, other):
		if other.type == 'number':
			return Number(n=self.value() + other.value())

	def __sub__(self, other):
		if other.type == 'number':
			return Number(n=self.value() - other.value())

	def __mul__(self, other):
		if other.type == 'number':
			return Number(n=self.value() * other.value())
		elif other.type == 'duration':
			return other * self

	def __div__(self, other):
		if other.type == 'number':
			return Number(n=self.value() / other.value())

	def __str__(self):
		return str(self.value())

@register
class Unit(Terminal):
	re = re.compile(
	'(?P<milliseconds>milliseconds?|ms)|'
	'(?P<seconds>seconds?|secs?|s)|'
	'(?P<minutes>minutes?|mins?)|'
	'(?P<hours>hours?|hrs?)|'
	'(?P<days>days?|d)|'
	'(?P<weeks>weeks?|wks?|w)|'
	'(?P<months>months?|mons?)|'
	'(?P<years>years?|yrs?|y)')

	def value(self):
		return self.d.keys()[0]

@register
class DatetimeLiteral(Terminal):
	re = re.compile('(?P<lit>now|epoch)')

	def value(self):
		if self.d['lit'] == 'now':
			return datetime.datetime.now()
		elif self.d['lit'] == 'epoch':
			return datetime.datetime(1970, 1, 1)

@register
class DateLiteral(Terminal):
	re = re.compile('(?P<lit>today)')

	def value(self):
		if self.d['lit'] == 'today':
			return datetime.date.today()

@register
class ISO8601(Terminal):
	re = re.compile(r'''(?P<year>\d{4})(?P<datesep>-?)
	(?:
		(?P<month>\d{2})(?P=datesep)(?P<day>\d{2})|
		(?P<yearday>\d{3})|
		W(?P<week>\d{2})(?P=datesep)(?P<weekday>\d)
	)
	(?:
		(?:\s+|T)(?P<hour>\d{2})(?P<timesep>:?)(?P<minute>\d{2})
			(?:(?P=timesep)(?P<second>\d{2}))?
	)?''', re.X)

	def _value(self):
		year = int(self.d.get('year', 0))
		if 'month' in self.d:
			month = int(self.d.get('month', 0))
			day = int(self.d.get('day', 0))
			date = datetime.date(year, month, day)
		elif 'yearday' in self.d:
			yearday = int(self.d.get('yearday', 0))
			date = datetime.date(year, 1, 1) + datetime.timedelta(days=yearday - 1)
		elif 'week' in self.d:
			week = int(self.d.get('week', 0))
			weekday = int(self.d.get('weekday'))
			date = datetime.date(year, 1, 1)
			date += datetime.timedelta(days=(week - 1) * 7)
			date += datetime.timedelta(days=weekday - date.isoweekday())

		hour = int(self.d.get('hour', 0))
		minute = int(self.d.get('minute', 0))
		second = int(self.d.get('second', 0))
		time = datetime.time(hour, minute, second)

		return datetime.datetime.combine(date, time)

	def value(self):
		try:
			return self._value()
		except ValueError, e:
			raise InvalidDate(token=self, exc=e)

@register
class Date(Terminal):
	re = re.compile(r'(?P<year>\d{2,4})(?P<_datesep>[/-]?)(?P<month>\d{1,2})(?P=_datesep)(?P<day>\d{1,2})')

	def value(self):
		y = int(self.d.get('year'))
		m = int(self.d.get('month'))
		d = int(self.d.get('day'))
		return datetime.date(y, m, d)

@register
class Time(Terminal):
	re = re.compile(r'''(?P<hour>\d{1,2})
	(?:
		(?P<_timesep>[:.])(?P<minute>\d{2})
		(?:(?P=_timesep)(?P<second>\d{2}))?
		\s*(?P<ampm>am|pm)?|

		\s*(?P<ampm_2>am|pm)
	)''', re.X)

	def value(self):
		h = int(self.d.get('hour', 0))
		m = int(self.d.get('minute', 0))
		s = int(self.d.get('second', 0))
		ampm = self.d.get('ampm')
		if ampm:
			if ampm == 'am' and h == 12:
				h = 0
			elif ampm == 'pm' and h != 12:
				h += 12
		return datetime.time(h, m, s)


Comma = register(create_terminal(','))

OpenParen = register(create_terminal(r'\('))
CloseParen = register(create_terminal(r'\)'))

@register
class Minus(Terminal):
	re = re.compile('-')

	@staticmethod
	def apply(left, right):
		return left - right

@register
class Plus(Terminal):
	re = re.compile(r'\+')

	@staticmethod
	def apply(left, right):
		return left + right

@register
class Multiplication(Terminal):
	re = re.compile(r'\*')

	@staticmethod
	def apply(left, right):
		return left * right

@register
class Division(Terminal):
	re = re.compile('/')

	@staticmethod
	def apply(left, right):
		return left / right

@register
class Whitespace(Terminal):
	re = re.compile(r'\s+')
	ignore = True

@register
class DurationPart(NonTerminal):
	@rule(Number, Unit)
	def r(n, u):
		return (n, u)

@register
class DurationEx(NonTerminal):
	@rule(Comma, DurationPart, Lazy('DurationEx'))
	def r0(_, part, rest):
		return [part] + rest

	@rule()
	def r1():
		return []

class Duration(object):
	type = 'duration'

	@staticmethod
	def create(parts):
		return Duration(Duration.parts2delta(parts))

	@staticmethod
	def parts2delta(parts):
		items = {}
		for n, u in parts:
			if u.value() in items:
				raise DuplicateUnit(token=u)
			items[u.value()] = n.value()

		days = items.get('years', 0) * 365 + items.get('months', 0) * 30 + items.get('weeks', 0) * 7 + items.get('days', 0)
		seconds = items.get('hours', 0) * 3600 + items.get('minutes', 0) * 60 + items.get('seconds', 0)
		return datetime.timedelta(days=days, seconds=seconds, microseconds=items.get('milliseconds', 0) * 1000)

	@staticmethod
	def delta2parts(delta):
		items = OrderedDict()
		factor = 1
		if delta < datetime.timedelta():
			factor = -1
			delta = -delta

		days = delta.days
		items['years'], days = divmod(days, 365)
		items['months'], days = divmod(days, 30)
		items['weeks'], days = divmod(days, 7)
		items['days'] = days

		seconds = delta.seconds
		items['hours'], seconds = divmod(seconds, 3600)
		items['minutes'], seconds = divmod(seconds, 60)
		items['seconds'] = seconds

		items['milliseconds'] = delta.microseconds / 1000

		for unit in items:
			items[unit] *= factor
		return items

	def __init__(self, delta):
		self.delta = delta

	def __add__(self, other):
		if other.type == 'datetime':
			return other + self
		elif other.type == 'duration':
			return Duration(self.delta + other.delta)

	def __sub__(self, other):
		if other.type == 'duration':
			return Duration(self.delta - other.delta)

	def __mul__(self, other):
		if other.type == 'number':
			v = other.value()
			if not isinstance(v, float):
				return Duration(self.delta * other.value())
			else:
				return Duration(datetime.timedelta(seconds=self.delta.total_seconds() * v))

	def __div__(self, other):
		if other.type == 'duration':
			factor = self.delta.total_seconds() / other.delta.total_seconds()
			return Number(n=factor)
		elif other.type == 'number':
			v = float(other.value())
			return Duration(datetime.timedelta(seconds=self.delta.total_seconds() / v))

	def __repr__(self):
		return repr(self.delta2parts(self.delta))

	@staticmethod
	def _plural(val, unit):
		if val == 1:
			unit = unit[:-1]
		return '%s %s' % (val, unit)

	def __str__(self):
		items = self.delta2parts(self.delta)
		parts = [self._plural(items[k], k) for k in items if items[k]]
		return ', '.join(parts)


@register
class DatetimeEx1(NonTerminal):
	@rule(Time)
	def r0(t):
		return t.value()

	@rule()
	def r1():
		pass

@register
class DatetimeEx2(NonTerminal):
	@rule(Date)
	def r0(d):
		return d.value()

	@rule(DateLiteral)
	def r0b(d):
		return d.value()

	@rule()
	def r1():
		pass

@register
class Datetime(NonTerminal):
	type = 'datetime'

	@rule(DatetimeLiteral)
	def r0(d):
		return Datetime(d.value())

	@rule(ISO8601)
	def r0b(d):
		return Datetime(d.value())

	@rule(Date, DatetimeEx1)
	def r1(d, rest):
		return Datetime(Datetime.combine(d.value(), rest))

	@rule(DateLiteral, DatetimeEx1)
	def r1b(d, rest):
		return Datetime(Datetime.combine(d.value(), rest))

	@rule(Time, DatetimeEx2)
	def r2(t, rest):
		return Datetime(Datetime.combine(rest, t.value()))

	@staticmethod
	def combine(date, time):
		if date is None:
			date = datetime.date.today()
		if time is None:
			time = datetime.time(0, 0)
		return datetime.datetime.combine(date, time)

	def __init__(self, dt):
		self.datetime = dt

	def __repr__(self):
		return repr(self.datetime)

	def __str__(self):
		return str(self.datetime)

	def __add__(self, other):
		if other.type == 'duration':
			dt = self.datetime + other.delta
			return Datetime(dt)

	def __sub__(self, other):
		if other.type == 'duration':
			dt = self.datetime - other.delta
			return Datetime(dt)
		elif other.type == 'datetime':
			delta = self.datetime - other.datetime
			return Duration(delta)

	def __mul__(self, other):
		pass

	def __div__(self, other):
		pass


class NumDuration(NonTerminal):
	@rule(Unit, DurationEx)
	def r0(u, rest):
		return (u, rest)

	@rule()
	def r1():
		return

@register
class Factor(NonTerminal):
	@rule(Datetime)
	def r0(d):
		return d

	@rule(Number, NumDuration)
	def r1(n, rest):
		if rest is None:
			return n
		else:
			u, rest = rest
			return Duration.create([(n, u)] + rest)

	@rule(OpenParen, Lazy('Expression'), CloseParen)
	def r2(_, expr, __):
		return expr

@register
class TermD(NonTerminal):
	@rule(Multiplication, Factor, Lazy('TermD'))
	def r0_m(op, right, rest):
		return [op, right, rest]

	@rule(Division, Factor, Lazy('TermD'))
	def r0_d(op, right, rest):
		return [op, right, rest]

	@rule()
	def r1():
		pass

def make_ast_lr(left, rest):
	if not rest:
		return left

	op, right, rest = rest
	left = [op, left, right]
	return make_ast_lr(left, rest)

@register
class Term(NonTerminal):
	@rule(Factor, TermD)
	def r(left, ted):
		return make_ast_lr(left, ted)

@register
class ExpressionD(NonTerminal):
	@rule(Plus, Term, Lazy('ExpressionD'))
	def r0_p(op, right, rest):
		return [op, right, rest]

	@rule(Minus, Term, Lazy('ExpressionD'))
	def r0_m(op, right, rest):
		return [op, right, rest]

	@rule()
	def r1():
		pass

@register
class Expression(NonTerminal):
	@rule(Term, ExpressionD)
	def r(left, exd):
		return make_ast_lr(left, exd)

GRAMMAR_ENTRY = Expression

class InvalidDate(ParserException):
	reason = 'Cannot parse date'

class BadOperand(ParserException):
	def __init__(self, op, left, right):
		ParserException.__init__(self, token=op)
		self.reason = "Bad operands for '%s'" % op.match.group()

class DuplicateUnit(ParserException):
	reason = 'Unit is already used'

# }}}
# {{{ timecalc main

def do_compute(ast):
	if isinstance(ast, list):
		op, left, right = ast
		left = do_compute(left)
		right = do_compute(right)
		res = op.apply(left, right)
		if res is None:
			raise BadOperand(op, left, right)
		return res
	else:
		return ast


def compute_from_string(text):
	tokens = do_lexer(text)
	ast = do_parser(GRAMMAR_ENTRY, tokens)
	return do_compute(ast)

def do_one(text):
	try:
		print compute_from_string(text)
	except ParserException as e:
		print e

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

# }}}

if __name__ == '__main__':
	main()
