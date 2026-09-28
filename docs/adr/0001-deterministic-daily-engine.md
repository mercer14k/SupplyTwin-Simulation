# ADR 0001: NumPy daily engine instead of SimPy

Accepted. The core needs daily policy decisions and common random draws for paired comparisons, not arbitrary sub-day events. A small pure NumPy engine makes event ordering, proportional capacity allocation, conservation and replay easier to inspect. NumPy replaces SimPy here; a custom engine avoids an unnecessary event abstraction. Cost: no sub-day queues or event scheduling beyond integer-day shipment arrivals. Add SimPy only if time resolution becomes an explicit requirement.
