# 🧭 ESTRATÉGIAS — Como o coletor do Feed Especial lê o Instagram

Registro das estratégias em uso (e em teste) para o bot enxergar o feed.
Quando o Instagram mudar o layout, é AQUI que conferimos o que já existe e
registramos a próxima. **As estratégias não se substituem: são tentadas em
ordem, e a primeira que funcionar vale.** Atualizar o status conforme os testes.

_Atualizado em: 16/07/2026_

---

## 1. Leitura de curtidas/comentários (nesta ordem)

| # | Estratégia | Exemplo que ela entende | Status |
|---|---|---|---|
| 1 | Número + palavra (pt/es/en) | "24,3 mil curtidas" · "1.234 Me gusta" · "2.4K likes" · "Ver todos os 987 comentários" | ✅ validada |
| 2 | "e outras N pessoas" | "Curtido por fulano e outras 24.301 pessoas" · "y N personas más" · "and N others" | ✅ validada |
| 3 | Sequência de números soltos | "Seguir \| 6,6 mil \| 436 \| 185" → curtidas, comentários, compartilhamentos (layout novo) | 🧪 em teste |

- Sufixos entendidos: `mil`/`k` (milhar) e `mi`/`m` (milhão); separadores `.` e `,` nos dois papéis.
- A estratégia 3 só entra quando a 1 e a 2 não acharam nada — nada foi removido.

## 2. Visibilidade (quando um post pode ser julgado)

| # | Estratégia | O que resolve | Status |
|---|---|---|---|
| A | Julgar só com **≥60% do post na tela** | Post "espiando" na borda ainda não tem contadores/carrossel montados pelo Instagram — não queima como "já visto" | 🧪 em teste |
| B | **Resgate pelo rodapé de dados** | Post subindo com o topo cortado, mas com os contadores ainda visíveis embaixo — captura antes de o scroll "comer estrada" | 🧪 em teste |

## 3. Detecção de carrossel (qualquer uma basta)

1. Botão de avançar (`aria-label` Próximo / Avançar / Siguiente / Next)
2. Mais de 1 slide (`ul li img` / listas de apresentação)
3. Link com `img_index`

## 4. Comportamento do scroll ("jardineiro do algoritmo")

- Publicação **aprovada** no filtro → pausa de 2,5–5 s (ensina o algoritmo da conta-isca)
- **Reprovada** → passa em 0,6–1,4 s
- Rolagem de 500–900 px por ciclo, aleatória; reiniciar a sessão entre coletas renova a entrega

---

> **Ao mudar/adicionar uma estratégia:** registrar aqui, rodar uma coleta e conferir o
> **Resumo do LOG** (vistas · aprovadas · recusas por motivo) antes de marcar ✅ validada.
