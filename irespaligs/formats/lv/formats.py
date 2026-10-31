# Latvian formats: dd.mm.yyyy, decimal comma, space as thousands separator.
# The same values are used for English (see ../en/formats.py) so the app looks
# the same for all Latvian residents, whatever UI language they choose.
DATE_FORMAT = "d.m.Y"
SHORT_DATE_FORMAT = "d.m.Y"
DATETIME_FORMAT = "d.m.Y H:i"
SHORT_DATETIME_FORMAT = "d.m.Y H:i"
MONTH_DAY_FORMAT = "j. F"
DATE_INPUT_FORMATS = ["%d.%m.%Y", "%Y-%m-%d"]
DATETIME_INPUT_FORMATS = ["%d.%m.%Y %H:%M", "%d.%m.%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"]
FIRST_DAY_OF_WEEK = 1  # Monday
DECIMAL_SEPARATOR = ","
THOUSAND_SEPARATOR = "\xa0"  # non-breaking space
NUMBER_GROUPING = 3
