# Blueprint do dashboard

Este documento descreve o dashboard principal do case Playzone.

Artefato entregue:

```text
dashboard/playzone_product_analytics_dashboard.html
```

## Objetivo

Permitir que recrutadores, líderes de produto e analistas entendam rapidamente:

- quantos usuários chegam ao momento de valor;
- em qual etapa a jornada perde mais usuários;
- quais canais trazem usuários com melhor ativação;
- se usuários ativados retêm melhor;
- quais categorias geram mais liquidez no marketplace;
- se há falhas críticas de qualidade nos dados.

## Estrutura visual

### 1. Leitura executiva

Resumo curto no topo com a decisão principal: onde está o maior gargalo e qual métrica deve orientar priorização.

### 2. Cards principais

- Usuários analisados
- Taxa de ativação ordenada
- Reservas confirmadas
- Taxa de confirmação após convite

### 3. Funil ordenado

Gráfico de barras horizontais com usuários por etapa e conversão acumulada.

### 4. Ativação por canal

Comparação da conversão até `booking_confirmed` por canal de aquisição.

### 5. Retenção por ativação

Tabela D1, D7 e D30 para usuários ativados vs. não ativados.

### 6. Liquidez por categoria

Tabela com oportunidades, convites, reservas confirmadas e taxa de confirmação.

### 7. Cohorts semanais

Mapa de calor simples para leitura de retenção por cohort de cadastro.

## Princípios de design

- A primeira tela deve responder a pergunta principal sem interação.
- O dashboard deve ser estático e portátil, sem dependência externa.
- Números agregados devem reconciliar com os CSVs em `outputs/`.
- Tabelas devem mostrar amostra e denominador para evitar leitura enganosa.
- A metodologia deve aparecer no rodapé para deixar claro como funil e retenção foram calculados.
