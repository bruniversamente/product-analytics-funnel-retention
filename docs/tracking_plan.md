# Tracking plan

Este documento define os eventos usados no case Playzone.

## Eventos principais

| Evento | Significado de produto | Papel na análise |
|---|---|---|
| `app_open` | Usuário abriu a Playzone. | Entrada no produto e retorno para retenção. |
| `signup_completed` | Usuário criou conta. | Cadastro concluído. |
| `profile_completed` | Usuário preencheu informações mínimas do perfil. | Redução de fricção antes de buscar oportunidades. |
| `search_performed` | Usuário buscou uma experiência, jogo ou atividade. | Sinal de intenção. |
| `opportunity_viewed` | Usuário abriu a página de uma oportunidade. | Interesse em uma opção concreta. |
| `invitation_sent` | Usuário enviou convite ou manifestou interesse. | Primeiro passo de conexão no marketplace. |
| `booking_confirmed` | A reserva foi confirmada. | Momento de valor e definição de ativação. |

## Funil de ativação

1. `app_open`
2. `signup_completed`
3. `profile_completed`
4. `search_performed`
5. `opportunity_viewed`
6. `invitation_sent`
7. `booking_confirmed`

## Definição de ativação

Um usuário é considerado ativado quando chega a `booking_confirmed` seguindo a ordem do funil. A ordem importa porque um evento isolado não prova que a jornada funcionou corretamente.

## Campos obrigatórios

- `event_id`
- `user_id`
- `event_timestamp`
- `event_name`
- `session_id`
- `platform`
- `acquisition_channel`

Eventos de oportunidade também devem ter:

- `opportunity_id`
- `category`

## Checagens de qualidade

- `event_id` deve ser único.
- `event_name` deve estar na taxonomia aprovada.
- `event_timestamp` deve ser válido.
- Evento de oportunidade deve ter `opportunity_id`.
- Evento não pode ocorrer antes do `signup_date` do usuário.
- `booking_confirmed` não deve ocorrer antes de `invitation_sent`.
