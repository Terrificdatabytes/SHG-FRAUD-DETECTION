# SHG Loan Diversion Screening

A small tool that checks a borrower's transactions before a self-help group (SHG) loan is paid out, and tells a human officer whether the money looks likely to be passed on to someone outside the group.

It runs on made-up (synthetic) data only. It is a prototype for a demo, not something to use for real credit decisions.

## The problem in one picture

Some loans are not used by the person who took them. The money goes out to an outside account within a day or two, and part of it comes back later in small pieces.

```
Genuine loan

  Bank ---> Member ---+---> Seed shop
                      +---> Tool seller
                      +---> Labour
  (money is spent in different places and does not come back)


Diverted loan

  Bank ---> Member ---> Outside account ---> Third party
              ^                                  |
              |                                  |
              +---------- small returns ---------+
  (money leaves fast, goes to a few accounts, and loops back)
```

The tool looks for the second picture.

## What happens when you screen an application

```
  1. Upload       2. Protect        3. Draw the        4. Measure       5. Score        6. A person
  the bank/UPI    privacy           money map          patterns         the risk        decides
  report          names and         every transfer     speed of         0-100% with
  + consent       numbers become    is a link          pass-through,    a confidence
                  secret codes      between accounts   return loops     range
```

Every screening takes about a tenth of a second. The answer is one of three:

| Result | Meaning | What the officer does |
|---|---|---|
| Low risk | Nothing unusual | Normal approval |
| Needs review | Not enough evidence either way | Field visit first |
| High risk | Looks like diversion | Hold the loan, verify in the field |

Nobody is rejected automatically. A flagged loan can only be approved if the officer writes down a reason.

## What the system actually measures

For each borrower it works out things like:

- how much of the money received leaves again within 72 hours
- how many different accounts the outgoing money goes to
- how much of it goes outside the group
- whether money comes back to where it started (a loop)

These go into a small neural network (an MLP). It is not a graph neural network and it does not compute persistent homology. The "loop" feature is a simple approximation: the sending and receiving roles of the same account are separated in time so a return flow shows up as a loop.

A loop alone is not proof. Honest members also have loops, for example family transfers. That is why a person always checks.

## What is in the dashboard

| Page | What you see |
|---|---|
| Executive Overview | Key numbers, screening results, risk ranking, money flow, village hot-spots |
| New Loan Application | Screen a sample applicant (A to J) or upload a CSV |
| Review Queue | Open alerts, and a form to confirm, dismiss or escalate |
| SHG / Member Detail | One applicant's score, or a whole group |
| Topology Evidence | Loop pictures: genuine versus diverted |
| Village Risk | Which villages to visit first |
| Explanation and Audit Report | Every case with its reason, downloadable as CSV |
| Model Performance | How each method did on the test data |
| System and Compliance | Health, safeguards, tamper-evident audit trail |
| How It Works | Animated explanation for people seeing it for the first time |

## How well does it work

Test set: 310 members, 24 of them true diversion cases, none shared with the training data.

| Method | Cases caught | Flags that were correct |
|---|---|---|
| Gradient boosting | 100% | 100% |
| Topology MLP (the deployed model) | 100% | 24% |
| MLP without loop features | 25% | 100% |
| Simple rule (pass-through over 50%) | 79% | 51% |

Be honest about this table:

- Gradient boosting beats the neural network here. The synthetic data is easier than real data, so these numbers say nothing about real-world accuracy.
- The deployed model catches every case but raises 74 false alarms, because the cut-off chosen on validation data did not carry over to the test data.
- The 10 demo applicants all get the expected verdict (10 of 10 pass).

## Privacy and audit

- Names, phone numbers and account IDs are turned into secret codes (HMAC-SHA256 with a per-install secret) before anything is saved.
- Screening only starts after consent is recorded.
- Every action is written to an audit log where each row is linked to the one before it, so edits can be detected.

## Run it

You need Python 3.11 or newer.

```
pip install -r requirements.txt
python scripts/make_data.py          # builds the demo data (only if data/shg.db is missing)
python scripts/run_acceptance.py     # checks the 10 demo cases
streamlit run app.py
```

Then open http://localhost:8501.

To retrain the model: `./train.sh`. To run the tests: `pytest -q`.

### On Google Colab

Open `SHG_Fraud_Monitor_Colab.ipynb` and run all cells. It prints a public link. For your own domain through a Cloudflare tunnel, save the tunnel token as a Colab secret named `CF_TUNNEL_TOKEN`.

### On Render

Build command:

```
./render_build.sh
```

Start command:

```
streamlit run app.py --server.address 0.0.0.0 --server.port $PORT --server.headless true --server.enableCORS false --server.enableXsrfProtection false
```

Set `PYTHON_VERSION` to `3.12.8` and use an instance with at least 2 GB of memory. The database is rebuilt on every deploy, so saved decisions are lost on restart.

## Folder map

```
app.py            the dashboard entry point
views/            one file per dashboard page, plus theme.py (look and feel)
core/             screening, features, model, privacy, audit log
scripts/          make_data.py, run_acceptance.py, make_gifs.py
demo_cases/       ten sample applicants, A to J
artifacts/        trained models and measured results
assets/           the two animated diagrams
tests/            automated tests
```

## Known limits

- The data is synthetic. Nothing here has been tested on real transactions.
- Labels are per member, not per transaction.
- Fairness across groups, data drift and speed on a physical Raspberry Pi have not been checked.
- The audit log can detect edits but is not an external, unchangeable ledger.
- A real pilot would need governed real data, an independent security and fairness review, and sign-off from the bank and regulator.
