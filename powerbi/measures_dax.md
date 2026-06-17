# Suggested DAX measures

These measures can be used after loading the analytical tables into Power BI.

## User metrics

```DAX
Active Users =
DISTINCTCOUNT(fact_events[user_id])
```

```DAX
New Users =
DISTINCTCOUNT(dim_users[user_id])
```

```DAX
Confirmed Users =
CALCULATE(
    DISTINCTCOUNT(fact_events[user_id]),
    fact_events[event_name] = "booking_confirmed"
)
```

```DAX
Activation Rate =
DIVIDE([Confirmed Users], [New Users])
```

## Funnel events

```DAX
Users - App Open =
CALCULATE(
    DISTINCTCOUNT(fact_events[user_id]),
    fact_events[event_name] = "app_open"
)
```

```DAX
Users - Signup Completed =
CALCULATE(
    DISTINCTCOUNT(fact_events[user_id]),
    fact_events[event_name] = "signup_completed"
)
```

```DAX
Users - Profile Completed =
CALCULATE(
    DISTINCTCOUNT(fact_events[user_id]),
    fact_events[event_name] = "profile_completed"
)
```

```DAX
Users - Search Performed =
CALCULATE(
    DISTINCTCOUNT(fact_events[user_id]),
    fact_events[event_name] = "search_performed"
)
```

```DAX
Users - Opportunity Viewed =
CALCULATE(
    DISTINCTCOUNT(fact_events[user_id]),
    fact_events[event_name] = "opportunity_viewed"
)
```

```DAX
Users - Invitation Sent =
CALCULATE(
    DISTINCTCOUNT(fact_events[user_id]),
    fact_events[event_name] = "invitation_sent"
)
```

```DAX
Users - Booking Confirmed =
CALCULATE(
    DISTINCTCOUNT(fact_events[user_id]),
    fact_events[event_name] = "booking_confirmed"
)
```

## Marketplace metrics

```DAX
Invitations Sent =
COUNTROWS(
    FILTER(
        fact_marketplace_actions,
        NOT(ISBLANK(fact_marketplace_actions[invitation_sent_at]))
    )
)
```

```DAX
Confirmed Bookings =
COUNTROWS(
    FILTER(
        fact_marketplace_actions,
        NOT(ISBLANK(fact_marketplace_actions[booking_confirmed_at]))
    )
)
```

```DAX
Confirmation Rate =
DIVIDE([Confirmed Bookings], [Invitations Sent])
```

```DAX
Average Time to Confirmation Hours =
AVERAGEX(
    FILTER(
        fact_marketplace_actions,
        NOT(ISBLANK(fact_marketplace_actions[invitation_sent_at]))
            && NOT(ISBLANK(fact_marketplace_actions[booking_confirmed_at]))
    ),
    DATEDIFF(
        fact_marketplace_actions[invitation_sent_at],
        fact_marketplace_actions[booking_confirmed_at],
        HOUR
    )
)
```

## Notes

For cohort charts, create a calendar table and a user cohort table before building the final model.
