chronocalc
==========

chronocalc is a basic calculator for time and durations. It can:

* add durations::

	> 1 day + 1445 minutes
	2 days, 5 minutes

* subtract durations::

	> 1 hour, 5 minutes - 555 seconds
	55 minutes, 45 seconds

* multiply/divide durations::

	> 40 mins * 4
	2 hours, 40 minutes
	> 1 day / 2
	12 hours

* add durations to dates::

	> 2015/07/08 + 3 weeks
	2015-07-29 00:00:00

* subtract durations from dates::

	> 2015/07/08 11pm - 15 hours
	2015-07-08 08:00:00

* compute duration between two dates::

	> 2015/07/08 - 2015/07/06 12pm
	1 day, 12 hours

* compute the ratio of two durations::

	> 1 day / 1 minute
	1440.0

* do all of the above at once::

	> 2 * ((100 days + 2015/07/08) - (2015/07/01 - 48 hours))
	7 months, 1 week, 5 days

Invocation
----------

If given an argument, chronocalc will eval it and exit, else, it will start a REPL (Read-Eval-Print Loop) prompt to eval multiple expressions.

Input format
------------

Grammar
+++++++

In EBNF format::

	digit ::= "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9";
	number ::= [ "-" ], digit, {digit}, [ ".", {digit} ];

	unit ::= "milliseconds" | "millisecond" | "ms" 
	       | "seconds" | "second" | "sec" | "secs" | "s"
	       | "minutes" | "minutes" | "mins" | "min"
	       | "hours" | "hour" | "hrs" | "hr"
	       | "days" | "day" | "d"
	       | "weeks" | "week" | "wks" | "wk" | "w"
	       | "months" | "month" | "mons" | "mon"
	       | "years" | "year" | "yrs" | "yr" | "y";

	duration ::= number, unit, { ",", number, unit };

	iso8601d ::= digit, digit, digit, digit, "-", digit, digit, "-", digit, digit (* YYYY-MM-DD *)
		   | digit, digit, digit, digit, "-", digit, digit, digit (* YYYY-DDD day in year *)
		   | digit, digit, digit, digit, "-W", digit, digit, "-", digit (* YYYY-Www-D week in year, day in week *)
		   | digit, digit, digit, digit, digit, digit, digit, digit (* YYYYMMDD *)
		   | digit, digit, digit, digit, digit, digit, digit (* YYYYDDD day in year *)
		   | digit, digit, digit, digit, digit, digit, digit (* YYYYwwD week in year, day in week *);
	iso8601t ::= "digit, digit, ":", digit, digit, [ ":", digit, digit ] (* HH:MM:SS *)
		   | "digit, digit, digit, digit, [ digit, digit ] (* HHMMSS *);
	iso8601 ::= iso8601d, [ ( "T" | ?whitespace? ), iso8601t ];

	date ::= digit, digit, digit, digit, ( "/" | "-" ), digit, [ digit ], ( "/", "-" ), digit, [ digit ];
	time ::= digit, [ digit ], ( "am" | "pm" )
	       | digit, [ digit ], ":", digit, [ digit ], [ ":", digit, [ digit ] ], [ "am" | "pm" ];

	datetime ::= date, [ time ] | [ date ], time | iso8601;

	factor ::= duration | datetime | number | "(", expression, ")";
	term ::= term, [ ( "*" | "/" ), factor ];
	expression ::= expression, [ ( "+" | "-" ), term ];

Examples
++++++++

These are example of the datetimes and durations formats accepted by chronocalc::

	now
	today
	epoch
	2015-01-01 01:23
	2015-01-01 12:34:56
	20150101T123456
	2015/01/01
	2015/01/01 13:34
	2015/01/01 1:34pm
	12:34
	3am
	1 day
	1y, 3w, 4hrs, 5s
	1 year, 2 months, 3 days, 4 weeks, 5 hours, 6 minutes, 7 seconds, 8 milliseconds

FAQ
---

* Q: Are timezones handled?
* A: Not yet. Using them will return a syntax error.

* Q: Are leap seconds handled?
* A: Not at all, and probably won't be. "2015/07/01 - 2015/06/30 23:59:59" returns "1 second".

* Q: Is the format YYYY/MM/DD or YYYY/DD/MM?
* A: YYYY/MM/DD.

* Q: When inputting date "20150101", it is parsed as number "20150101".
* A: That's not a question, and that's effectively a number. To force a datetime form, use "20150101 00:00" instead.

Dependencies
------------

chronocalc depends on `relativedelta <https://dateutil.readthedocs.io/en/stable/relativedelta.html>`_ for computing durations.

License
-------

chronocalc is licensed under the `WTFPLv2 <http://wtfpl.net>`_. See COPYING.WTFPL file.
