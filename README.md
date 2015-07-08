# timecalc

timecalc is a basic calculator for time and durations. It can:

* add durations:

```
> 1 day + 1445 minutes
2 days, 5 minutes
```

* subtract durations:

```
> 1 hour, 5 minutes - 555 seconds
55 minutes, 45 seconds
```

* multiply durations:

```
> 40 mins * 4
2 hours, 40 minutes
```

* add durations to dates:

```
> 2015/07/08 + 3 weeks
2015-07-29 00:00:00
```

* subtract durations from dates:

```
> 2015/07/08 11pm - 15 hours
2015-07-08 08:00:00
```

* subtract dates:

```
> 2015/07/08 - 2015/07/06 12pm
1 day, 12 hours
```

* do all of the above at once:

```
> 2 * ((100 days + 2015/07/08) - (2015/07/01 - 48 hours ))
7 months, 1 week, 5 days
```

## invocation

If given an argument, timecalc will eval it and exit, else, it will start a REPL prompt to eval multiple expressions.

## Known bugs

Sometimes, the parser is a bit sloppy, parentheses can be added to group stuff, and spaces be added for better separation.

## License

timecalc is licensed under the [WTFPLv2](http://wtfpl.net).
