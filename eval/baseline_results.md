# Baseline: naive row RAG vs the routed approach

**Naive RAG: 4/20. Routed: 20/20.**

Number questions pass when the answer text contains the values of a hand-written reference SQL query.
Similarity questions pass when at least 80 % of the returned claims are relevant.

| Question | Naive RAG (top 20 rows) | Routed (SQL or vector search) |
|---|---|---|
| How many claims are in the file? | ❌ wrong | ✅ correct |
| How many claims were rejected in 2024? | ❌ wrong | ✅ correct |
| How many claims were rejected in 2024, by product? | ❌ wrong | ✅ correct |
| What is the total paid amount for motor claims in 2023? | ❌ wrong | ✅ correct |
| Which canton has the most claims? | ❌ wrong | ✅ correct |
| What is the average claimed amount for home fire claims? | ❌ wrong | ✅ correct |
| How many open claims are there for each product? | ❌ wrong | ✅ correct |
| What is the median settlement time in days for paid claims? | ❌ wrong | ✅ correct |
| How many claims mention a washing machine? | ❌ wrong | ✅ correct |
| How many home storm claims were there in December 2024? | ❌ wrong | ✅ correct |
| What is the total claimed amount of rejected liability claims? | ❌ wrong | ✅ correct |
| How many claims came through the Online channel in 2025? | ❌ wrong | ✅ correct |
| List the 5 largest paid home claims with their claim id and paid amount. | ❌ wrong | ✅ correct |
| How many policies have more than 3 claims? | ❌ wrong | ✅ correct |
| What is the average customer age for motor theft claims? | ✅ correct | ✅ correct |
| Find claims similar to: a bike stolen from a shared basement that wasn't locked | ❌ 70% relevant | ✅ 100% relevant |
| Show claims similar to a washing machine flooding the bathroom | ✅ 100% relevant | ✅ 100% relevant |
| Find claims where a parked car was damaged by bad weather | ✅ 100% relevant | ✅ 100% relevant |
| Find claims like: a guest hurt themselves falling at my house | ❌ 0% relevant | ✅ 100% relevant |
| Show me examples of claims where someone damaged a neighbour's things | ✅ 100% relevant | ✅ 100% relevant |
