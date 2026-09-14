---
name: ads-hints
description: >
  Develop, group and prioritise context hints for OpenAI Ads, and derive
  account-wide negative keywords. Use this skill for topic research, context
  hints, ad targeting, exclusions, negative keywords, or when deciding which
  conversations an ad should appear in.
user-invocable: true
license: MIT
metadata:
  version: "0.1.0"
  category: ads
---

# Context hints

## What they are

Free text describing when an ad is relevant. The platform evaluates it
semantically against live conversations.

What they are **not**: keywords. There are no match types, no per-hint bid and
no per-hint reporting.

> "Provide a list of descriptions or keywords for when the product or service
> might be useful to show."

## How many

The API accepts up to 2000 per ad group. That is a technical ceiling, not a
recommendation.

**Because there is no per-hint reporting, the ad group is the smallest unit of
measurement.** 200 hints in one group means seeing the outcome but never the
cause. A success cannot be repeated and a failure cannot be isolated.

**Guideline: 10 to 25 hints per group, tightly scoped.** Five groups of 15 beat
one group of 75.

A hint belongs in a group only if it serves the same intent as the rest. The
moment you hesitate, it belongs in its own group.

## Phrasing

Hints are free text read semantically. Use natural language, not keyword
syntax.

| Instead of | Better |
|---|---|
| `process automation smb` | `A mid-sized company is looking for ways to automate repetitive workflows` |
| `chatbot price` | `Someone is asking what a chatbot for their website costs` |
| `gdpr ai` | `The topic is using AI in a company in a data-protection-compliant way` |

Descriptions of the conversational situation outperform search terms, because
matching is semantic and questions put to a chat assistant are longer and more
discursive than search queries.

## Forming groups

Group by **intent**, not by product and not by audience.

A service business might arrive at:

| Group | Intent | Landing page |
|---|---|---|
| Automating workflows | concrete need, looking for a solution | service page |
| Introducing AI in a company | orienting, still early | overview page |
| Chatbot for a website | specific product | product page |
| AI and data protection | addressing concerns | compliance page |

Groups with different intent need different bids: someone still orienting is
worth less than someone already comparing vendors.

## Research with external data

Optional. Two things carry over well, one does not.

**Scraping the assistant's actual answers** shows which words it uses, which
sources it cites, and whether local businesses get named at all. That is not a
proxy — it is the thing itself. Useful for vocabulary in a 50-character
headline.

**Search intent classification** (informational, commercial, transactional,
navigational) carries over, because intent is platform-independent. Since this
platform has no match types, clean intent separation at the ad group level is
the main lever available.

**What does not carry over:** click prices from search advertising. Different
auction, different participants. Also be wary of metrics marketed as "AI search
volume" that are in fact derived from web search elements — check the source
before treating them as chat usage data.

## Negative keywords

<!-- Verified: 2026-09-14 against the live API -->

**There is no negative keyword endpoint.** Seven candidate paths were probed
live on 2026-09-14, GET and POST, and all answered `Invalid URL` or
`Invalid method`. The word does not appear anywhere in the published
documentation either. The `set_negative_keywords` tool in this server posts to
`/ad_account/negative_keywords`, which does not exist.

So exclusion happens inside the hints themselves. Describe the intent narrowly
enough that the wrong conversations do not match: "a company wants to automate
repetitive workflows" pulls in far less noise than "automation". Where a hint
attracts the wrong audience, the fix is to rewrite or move it, not to block a
term elsewhere.

What follows was written for the assumed endpoint and is kept because the
thinking still applies to choosing hints, not because the list can be set.

**Formerly assumed: account-wide only, at most 100 entries.** There is
no per-campaign or per-group scoping.

The scarcity is the point: every slot has to earn its place by working broadly.
A term that only bothers one group is not worth an entry.

Common exclusion themes for a B2B service business:

| Theme | Examples |
|---|---|
| Free intent | free, gratis, open source, freeware |
| Job seeking | job, vacancy, salary, apprenticeship, internship |
| DIY | do it yourself, tutorial, how to build |
| Education | degree, course, certificate, training |
| Second hand | used, refurbished |
| Templates | template, sample, download PDF |
| Definitions | definition, what is, meaning |

Check each one: does it also exclude genuine prospects? "Cost" does **not**
belong on the list — asking about cost often signals real intent.

`set_negative_keywords` claims to set them and posts to a path the API does not
have. Until a working endpoint is found, treat the themes above as a checklist
for writing hints: if a theme would match your hint, the hint is too broad.

## Refining

Without per-hint reporting, optimisation works through the group:

1. Find groups with a conspicuously low click rate
2. Review their hints: which describe a different intent from the rest?
3. Move those into their own group — do not delete them
4. Measure for two weeks
5. Pause whatever still underperforms

Move rather than delete, because a hint can perform badly in the wrong company
and well in the right one.
