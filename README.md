# ForgetMe

![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)

**Your forgotten accounts, found and deleted, from one chat in ASI:One.**

ForgetMe checks your email against known data breaches, ranks every account as delete, secure or keep with a plain-English reason, then gives you direct deletion links and emails formal deletion requests to each company, only after you approve. It tracks the response deadline and chases companies that ignore you.

Built for Fetch-A-Thon 3.0 with uAgents, Agentverse, ASI:One and the ASI1 LLM.

## Agents

| Agent | Address | Job |
|---|---|---|
| ForgetMe (Orchestrator) | `agent1qvdaw2cl0jj02dtkmzr5r94n86qx3tjnhhrn93hya9zq8gpy3px6zpmgc0j` | The agent you chat with in ASI:One. Understands intent with ASI1, coordinates the others, shows results. |
| Breach Scout | `agent1qgdrjx4mgg6p8mgr3004n8u39npzn6pkf8vt23zy2exmky4ek0jzzlrkajx` | Checks an email against known data breaches. |
| Risk Ranker | `agent1qfjdhjzh2tm5kc9j2nmh33pg7c2ncnz3g4p3a6un78ke47kdx7mxyf2gw0x` | Scores each account (rules + ASI1): delete, secure or keep, with a reason. |
| Eraser | `agent1qdj9quc8mzkakn5yz7lau8csw9wg95e66p357wrc4p3vv2gx6ek0wj00utp` | Deletion links and formal GDPR/CCPA deletion requests, sent only after approval. |
| Follow-up | `agent1qf59g3ht08etzuj0dcdh5y45mqlfzhayz3yk8kxljmwgwzv6p79vw56krnu` | Tracks the 30-day response deadline and escalates unanswered requests. |

All agents are mailbox agents registered on Agentverse. The Orchestrator implements the Agent Chat Protocol, so the whole workflow runs inside ASI:One with no custom frontend.

## How it works

1. You send your email address to ForgetMe in ASI:One.
2. Breach Scout finds the breaches; Risk Ranker explains and ranks each account.
3. You reply `delete all` (or pick numbers). Eraser prepares a plan: links you can use yourself, and formal requests it can email.
4. You reply `send`. The requests go out, and Follow-up tracks each deadline.

## Privacy by design

- Nothing is sent to any company without your explicit approval.
- No passwords are ever requested or stored.
- Emails are masked in logs.

## Run it

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m scripts.init_env
```

Fill in `.env` (`ASI1_API_KEY` is required; SMTP settings are needed to send emails), then:

```bash
./run_all.sh
```

Open each agent's inspector link from `logs/*.log` once, choose Connect, then Mailbox. Chat with ForgetMe from its Agentverse profile.

**Safety switches in `.env`:** `EMAIL_DRY_RUN=true` sends nothing; `EMAIL_REDIRECT_TO` sends every email to one inbox instead of the companies (demo mode); `FOLLOWUP_DEMO_SECONDS` makes follow-ups fire after N seconds instead of 30 days.

## Business model

Free scan and triage. A paid Concierge tier sends every request, chases non-responders and rescans every quarter.

## Credits

Breach data: [XposedOrNot](https://xposedornot.com) and [Have I Been Pwned](https://haveibeenpwned.com) (CC BY 4.0).
