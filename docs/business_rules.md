# Business rules

## Scope

The project simulates a digital marketplace where users can search opportunities, view details, send invitations and confirm bookings.

## User activation

A user is activated when they reach the event `booking_confirmed`.

## Funnel conversion

Funnel conversion is calculated by counting distinct users who reached each step.

```text
step_conversion = users_at_step / users_at_first_step
```

## Step loss

Step loss measures the drop between two consecutive steps.

```text
step_loss = 1 - users_at_current_step / users_at_previous_step
```

## Retention

Retention is measured by checking whether a user had any event after signup.

Examples:

```text
D1 retention = user had event 1 day after signup
D7 retention = user had event 7 days after signup
D30 retention = user had event 30 days after signup
```

## Marketplace liquidity

A marketplace opportunity is considered liquid when an invitation leads to a confirmed booking.

```text
confirmation_rate = confirmed_bookings / invitations_sent
```

## Time to confirmation

Time to confirmation measures how long it takes between an invitation and booking confirmation.

```text
time_to_confirmation_hours = booking_confirmed_at - invitation_sent_at
```

## Filters

- Funnel metrics use distinct users.
- Retention metrics use signup date as cohort start.
- Marketplace metrics use opportunity-level data.
- Events without required IDs are flagged in quality checks.
