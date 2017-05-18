#!/usr/bin/env python3
# coding: utf-8
# license: WTFPLv2 [http://wtfpl.net]

import unittest
from timecalc import *

class TestParseMethods(unittest.TestCase):
	def assertDatetimesEqual(self, a, b):
		self.assertEqual(a.replace(microsecond=0), b.replace(microsecond=0))

	def assertFail(self, text, exc=ParserException):
		self.assertRaises(exc, compute_from_string, text)

	def test_datetimes(self):
		DT = datetime.datetime

		self.assertEqual(compute_from_string('2015/07/09').datetime, DT(2015, 7, 9))
		self.assertEqual(compute_from_string('2015/07/10 00:00').datetime, DT(2015, 7, 10))
		self.assertEqual(compute_from_string('2015/07/11 01:45').datetime, DT(2015, 7, 11, 1, 45))
		self.assertEqual(compute_from_string('2015/07/09 14:30').datetime, DT(2015, 7, 9, 14, 30))
		self.assertEqual(compute_from_string('2015/07/09 14:30:26').datetime, DT(2015, 7, 9, 14, 30, 26))
		self.assertEqual(compute_from_string('2015/07/09 2:15pm').datetime, DT(2015, 7, 9, 14, 15))
		self.assertEqual(compute_from_string('2015/07/09 3am').datetime, DT(2015, 7, 9, 3))
		self.assertEqual(compute_from_string('2015/07/09 12am').datetime, DT(2015, 7, 9))
		self.assertEqual(compute_from_string('2015/07/31 12pm').datetime, DT(2015, 7, 31, 12))

		self.assertEqual(compute_from_string('2015-07-31').datetime, DT(2015, 7, 31))
		self.assertEqual(compute_from_string('2015-07-31 01:23').datetime, DT(2015, 7, 31, 1, 23))
		self.assertEqual(compute_from_string('2015-07-31 01:23:45').datetime, DT(2015, 7, 31, 1, 23, 45))
		self.assertEqual(compute_from_string('2015-07-31T01:23:45').datetime, DT(2015, 7, 31, 1, 23, 45))
		self.assertEqual(compute_from_string('20150731T0123').datetime, DT(2015, 7, 31, 1, 23))
		self.assertEqual(compute_from_string('20150731T012345').datetime, DT(2015, 7, 31, 1, 23, 45))

		self.assertDatetimesEqual(compute_from_string('now').datetime, DT.now())
		self.assertDatetimesEqual(compute_from_string('today').datetime, DT.combine(datetime.date.today(), datetime.time()))
		self.assertEqual(compute_from_string('epoch').datetime, DT(1970, 1, 1))

	def test_fail_datetimes(self):
		self.assertFail('2015-02-29', InvalidDate)
		self.assertFail('2015-01-01 42:00', InvalidDate)
		self.assertFail('2015-01-01 00:99', InvalidDate)
		self.assertFail('fail')

	def test_durations(self):
		TD = datetime.timedelta

		self.assertEqual(compute_from_string('1 second').delta, TD(seconds=1))
		self.assertEqual(compute_from_string('86410 seconds').delta, TD(days=1, seconds=10))
		self.assertEqual(compute_from_string('1 minute').delta, TD(seconds=60))
		self.assertEqual(compute_from_string('1 hour').delta, TD(seconds=3600))
		self.assertEqual(compute_from_string('2 hours').delta, TD(seconds=2 * 3600))
		self.assertEqual(compute_from_string('36 hours').delta, TD(days=1, seconds=12 * 3600))
		self.assertEqual(compute_from_string('1 day').delta, TD(days=1))
		self.assertEqual(compute_from_string('-1 day').delta, TD(days=-1))
		self.assertEqual(compute_from_string('0.5 day').delta, TD(seconds=12 * 3600))
		self.assertEqual(compute_from_string('30 days').delta, TD(days=30))
		self.assertEqual(compute_from_string('1 week').delta, TD(days=7))
		self.assertEqual(compute_from_string('1 month').delta, TD(days=30))
		self.assertEqual(compute_from_string('1 year').delta, TD(days=365))
		self.assertEqual(compute_from_string('1 hour, 1 second').delta, TD(seconds=3601))
		self.assertEqual(compute_from_string('1 year, 1 hour').delta, TD(days=365, seconds=3600))
		self.assertEqual(compute_from_string('1 year, 4 days').delta, TD(days=369))
		self.assertEqual(compute_from_string('1 year, 4 days, 36 hours, 42 seconds').delta, TD(days=370, seconds=12 * 3600 + 42))

	def test_fail_durations(self):
		self.assertFail('1 year, 1 year', DuplicateUnit)

	def test_duration_ops(self):
		TD = datetime.timedelta

		self.assertEqual(compute_from_string('1 second + 2 hours').delta, TD(seconds=7201))
		self.assertEqual(compute_from_string('1 hour, 1 second + 1 hour').delta, TD(seconds=7201))
		self.assertEqual(compute_from_string('1 hour + 1 hour, 1 second').delta, TD(seconds=7201))
		self.assertEqual(compute_from_string('2 hours - 1 hour, 1 second').delta, TD(seconds=3599))
		self.assertEqual(compute_from_string('0 hours').delta, TD(seconds=0))
		self.assertEqual(compute_from_string('0 hours - 1 hour + 1 hour').delta, TD(seconds=0))
		self.assertEqual(compute_from_string('3 * 1 second').delta, TD(seconds=3))
		self.assertEqual(compute_from_string('1 second * 4').delta, TD(seconds=4))
		self.assertEqual(compute_from_string('2 hours * 4').delta, TD(seconds=8 * 3600))
		self.assertEqual(compute_from_string('4 * 1 hour + 1 hour').delta, TD(seconds=5 * 3600))
		self.assertEqual(compute_from_string('4 * 1 hour, 2 seconds').delta, TD(seconds=4 * 3600 + 8))

	def test_number_ops(self):
		self.assertEqual(compute_from_string('42.53').value(), 42.53)
		self.assertEqual(compute_from_string('12 + 0.34').value(), 12.34)
		self.assertEqual(compute_from_string('0.5 * 4').value(), 2)
		self.assertEqual(compute_from_string('1 / 2').value(), 0.5)
		self.assertEqual(compute_from_string('2 hours / 1 second').value(), 7200)

	def test_datetime_ops(self):
		TD = datetime.timedelta

		self.assertEqual(compute_from_string('2015/07/31 - 2015/07/30').delta, TD(days=1))
		self.assertEqual(compute_from_string('2015/07/15 - 2015/08/15').delta, TD(days=-31))
		self.assertEqual(compute_from_string('2015/07/15 12pm - 2015/08/15 00:00').delta, TD(days=-30, seconds=-12 * 3600))
		self.assertEqual(compute_from_string('2015/03/15 01:10 - 2015/02/15 23:20').delta, TD(days=27, seconds=50 * 60 + 3600))
		self.assertEqual(compute_from_string('23:20 - 01:10').delta, TD(seconds=10 * 60 + 22 * 3600))
		self.assertEqual(compute_from_string('01:10 - 23:20').delta, TD(seconds=10 * -60 + 22 * -3600))
		self.assertEqual(compute_from_string('1970/01/10 - epoch').delta, TD(days=9))

	def test_datetime_duration_ops(self):
		DT = datetime.datetime
		TD = datetime.timedelta

		self.assertEqual(compute_from_string('2015/07/31 + 1 day').datetime, DT(2015, 8, 1))
		self.assertEqual(compute_from_string('2015/07/31 + 2 days').datetime, DT(2015, 8, 2))
		self.assertEqual(compute_from_string('2015/02/28 + 1 day').datetime, DT(2015, 3, 1))
		self.assertEqual(compute_from_string('2015/05/04 + 3 hours, 10 seconds').datetime, DT(2015, 5, 4, 3, 0, 10))
		self.assertEqual(compute_from_string('2015/05/04 + 3 hours + 10 seconds').datetime, DT(2015, 5, 4, 3, 0, 10))
		self.assertEqual(compute_from_string('2015/05/04 10:45 + 3 hours + 10 seconds').datetime, DT(2015, 5, 4, 13, 45, 10))
		self.assertEqual(compute_from_string('2015/05/04 10:45 - 3 hours + 10 seconds').datetime, DT(2015, 5, 4, 7, 45, 10))

	def test_fail_ops(self):
		self.assertFail('2015/01/01 + 10', BadOperand)
		self.assertFail('2015/01/01 - 10', BadOperand)
		self.assertFail('2015/01/01 * 10', BadOperand)
		self.assertFail('2015/01/01 / 10', BadOperand)
		self.assertFail('2015/01/01 + 2015/01/01', BadOperand)
		self.assertFail('2015/01/01 * 2015/01/01', BadOperand)
		self.assertFail('2015/01/01 / 2015/01/01', BadOperand)
		self.assertFail('1 day + 10', BadOperand)
		self.assertFail('1 day - 10', BadOperand)
		self.assertFail('1 day - 2015/01/01', BadOperand)
		self.assertFail('1 day * 1 day', BadOperand)
		self.assertFail('2015/01/01 * 1 day', BadOperand)
		self.assertFail('2015/01/01 / 1 day', BadOperand)

if __name__ == '__main__':
	unittest.main()
