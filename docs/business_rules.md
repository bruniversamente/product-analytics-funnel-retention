# Regras de negócio

## Escopo

O projeto simula a Playzone, uma plataforma digital de experiências, jogos e atividades. Usuários podem abrir o app, criar cadastro, completar perfil, buscar oportunidades, visualizar detalhes, enviar convites e confirmar reservas.

## Definição de ativação

Um usuário é considerado ativado quando chega ao evento `booking_confirmed` depois de passar pelo funil principal em ordem temporal.

## Funil ordenado

O funil deve respeitar a sequência abaixo por usuário:

```text
app_open -> signup_completed -> profile_completed -> search_performed -> opportunity_viewed -> invitation_sent -> booking_confirmed
```

Um usuário só conta em uma etapa se a etapa anterior ocorreu antes dela.

```text
conversion_from_start = users_at_step / users_at_first_step
conversion_from_previous = users_at_current_step / users_at_previous_step
step_loss = 1 - conversion_from_previous
```

## Retenção

Retenção mede retorno ao app, não qualquer evento depois do cadastro.

```text
D1 retention = usuário teve app_open 1 dia após cadastro
D7 retention = usuário teve app_open 7 dias após cadastro
D30 retention = usuário teve app_open 30 dias após cadastro
```

Essa definição evita contar a própria jornada inicial de ativação como retenção.

## Liquidez do marketplace

Uma oportunidade é considerada líquida quando um convite leva a uma reserva confirmada.

```text
confirmation_rate = confirmed_bookings / invitations_sent
```

## Tempo até confirmação

Tempo entre o convite enviado e a reserva confirmada.

```text
time_to_confirmation_hours = booking_confirmed_at - invitation_sent_at
```

## Filtros e cuidados

- Métricas de funil usam usuários distintos.
- Métricas de retenção usam `signup_date` como data inicial da cohort.
- Métricas de marketplace usam grão de oportunidade.
- Eventos fora da taxonomia aprovada devem ser sinalizados.
- Eventos de oportunidade sem `opportunity_id` devem ser sinalizados.
- Reservas antes de convite devem ser tratadas como falha crítica de qualidade.
