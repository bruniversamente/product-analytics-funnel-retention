# Data dictionary

## `sample_users.csv`

| Field | Description |
|---|---|
| `user_id` | Synthetic user identifier. |
| `signup_date` | Date when the user signed up. |
| `persona` | User profile: Host or Guest. |
| `region` | Broad synthetic region. |
| `acquisition_channel` | Acquisition channel. |
| `platform` | Platform used by the user. |

## `sample_events.csv`

| Field | Description |
|---|---|
| `event_id` | Unique event identifier. |
| `user_id` | User related to the event. |
| `event_timestamp` | Event timestamp. |
| `event_name` | Name of the tracked product event. |
| `session_id` | Session identifier. |
| `platform` | Platform where the event happened. |
| `acquisition_channel` | Acquisition channel attributed to the user. |
| `opportunity_id` | Opportunity related to the event, when applicable. |
| `category` | Opportunity category, when applicable. |

## `sample_marketplace_actions.csv`

| Field | Description |
|---|---|
| `opportunity_id` | Synthetic opportunity identifier. |
| `category` | Opportunity category. |
| `created_at` | Opportunity creation timestamp. |
| `host_user_id` | User who created or hosted the opportunity. |
| `guest_user_id` | User who interacted with the opportunity. |
| `invitation_sent_at` | Timestamp when an invitation was sent. |
| `booking_confirmed_at` | Timestamp when the booking was confirmed. |
| `status` | Final opportunity status. |
