# Tracking plan

This file defines the product events used in the analysis.

## Core events

- `app_open`: user opened the product.
- `signup_completed`: user created an account.
- `profile_completed`: user added the minimum profile information.
- `search_performed`: user searched for an opportunity.
- `opportunity_viewed`: user opened an opportunity page.
- `invitation_sent`: user sent an invitation.
- `booking_confirmed`: marketplace connection was confirmed.

## Activation funnel

1. `app_open`
2. `signup_completed`
3. `profile_completed`
4. `search_performed`
5. `opportunity_viewed`
6. `invitation_sent`
7. `booking_confirmed`

## Activation definition

A user is considered activated when the event `booking_confirmed` exists for that user.

## Required fields

- `event_id`
- `user_id`
- `event_timestamp`
- `event_name`
- `session_id`
- `platform`
- `acquisition_channel`

Opportunity events should also include:

- `opportunity_id`
- `category`

## Quality checks

- Event IDs should be unique.
- Event names should match the approved taxonomy.
- Timestamps should be valid.
- Opportunity events should have an opportunity ID.
- Funnel order should make business sense per user.
