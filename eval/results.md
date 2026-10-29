# Evaluation results

## Exercise 2 (Excel): 20/20 passed

SQL questions pass when the returned values match a hand-written reference query.
Similarity questions pass when at least 80% of returned claims are relevant.

| Question | Route | Expected | Result |
|---|---|---|---|
| How many claims are in the file? | sql | sql | PASS (values match) |
| How many claims were rejected in 2024? | sql | sql | PASS (values match) |
| How many claims were rejected in 2024, by product? | sql | sql | PASS (values match) |
| What is the total paid amount for motor claims in 2023? | sql | sql | PASS (values match) |
| Which canton has the most claims? | sql | sql | PASS (values match) |
| What is the average claimed amount for home fire claims? | sql | sql | PASS (values match) |
| How many open claims are there for each product? | sql | sql | PASS (values match) |
| What is the median settlement time in days for paid claims? | sql | sql | PASS (values match) |
| How many claims mention a washing machine? | sql | sql | PASS (values match) |
| How many home storm claims were there in December 2024? | sql | sql | PASS (values match) |
| What is the total claimed amount of rejected liability claims? | sql | sql | PASS (values match) |
| How many claims came through the Online channel in 2025? | sql | sql | PASS (values match) |
| List the 5 largest paid home claims with their claim id and paid amount. | sql | sql | PASS (values match) |
| How many policies have more than 3 claims? | sql | sql | PASS (values match) |
| What is the average customer age for motor theft claims? | sql | sql | PASS (values match) |
| Find claims similar to: a bike stolen from a shared basement that wasn't locked | semantic | semantic | PASS (20/20 relevant) |
| Show claims similar to a washing machine flooding the bathroom | semantic | semantic | PASS (20/20 relevant) |
| Find claims where a parked car was damaged by bad weather | semantic | semantic | PASS (20/20 relevant) |
| Find claims like: a guest hurt themselves falling at my house | semantic | semantic | PASS (20/20 relevant) |
| Show me examples of claims where someone damaged a neighbour's things | semantic | semantic | PASS (20/20 relevant) |

## Exercise 3 (guide): 17/17 passed

A question passes when the cited page is the expected one, or when nothing is cited for questions the guide does not cover. Profile questions must also give the rule for the reader's situation (EU: 8 days, non-EU: 3 days).

| Question | Reader on | Expected page | Cited page | Result |
|---|---|---|---|---|
| Combien de jours ai-je pour déclarer mon arrivée à la commune ? | arrivee | arrivee | arrivee | PASS |
| Do I need to exchange my EU driving licence? | arrivee | permis | permis | PASS |
| Is it free? | permis | permis | permis | PASS |
| How much are family allowances per child? | bail | allocations | allocations | PASS |
| Quelle est la classe d'impôt d'un couple marié ? | - | impots_classes | impots_classes | PASS |
| What documents do I need to register my car? | assurance_auto | vehicule | vehicule | PASS |
| Combien coûte un abonnement de bus ? | arrivee | transport | transport | PASS |
| Mon assurance habitation couvre-t-elle la responsabilité civile ? | arrivee | assurance_habitation | assurance_habitation | PASS |
| How do I get a LuxTrust certificate? | - | luxtrust | luxtrust | PASS |
| How many days of paid leave does an employee get per year? | emploi | conges | conges | PASS |
| Can I deduct the interest on my mortgage? | achat | interets | interets | PASS |
| Quel est le montant maximum de la garantie locative ? | recherche_logement | bail | bail | PASS |
| What is the best pizza place in Esch? | arrivee | not covered | not found | PASS |
| How do I apply for a US visa? | - | not covered | not found | PASS |
| My bike was stolen from the common cellar, does my home insurance cover it? | assurance_habitation | assurance_habitation | assurance_habitation | PASS |
| How many days do I have to declare my arrival at the commune? | arrivee | arrivee | arrivee | PASS |
| How many days do I have to declare my arrival at the commune? | arrivee | arrivee | arrivee | PASS |
