"""Template-driven question generators for concepts that are procedural.

Definitions come from the lecture text (see `concepts.py`), but several intro
skills are procedural rather than definitional: solving for equilibrium,
predicting the effect of a shock, and telling a shift apart from a movement.
Those are generated from parameterised templates whose logic mirrors the
worked examples in the lectures, so the answers remain course-accurate while
the numbers and scenarios vary between quizzes.
"""

from __future__ import annotations

import random
from functools import partial
from typing import Dict, List, Optional

# Markets used in the lecture notes, so scenarios stay familiar.
MARKETS = [
    {"good": "campus lunch bowls", "unit": "bowls", "lecture": 5},
    {"good": "lattes at a campus coffee shop", "unit": "lattes", "lecture": 5},
    {"good": "Maine lobster rolls", "unit": "rolls", "lecture": 4},
    {"good": "used bicycles", "unit": "bicycles", "lecture": 5},
    {"good": "concert tickets", "unit": "tickets", "lecture": 5},
    {"good": "bags of roasted coffee", "unit": "bags", "lecture": 4},
]

EQUILIBRIUM_CITATION = "Lecture 5, §6 A Numerical View of Market Equilibrium"
SHOCK_CITATION = "Lecture 5, §7 How a Market Shock Appears in the Equations"
STATICS_CITATION = "Lecture 5, §18 A Four-Step Framework"


def _in_lectures(rows: List, lectures: Optional[List[int]], index: int) -> List:
    """Keep only the scenarios drawn from the requested lectures."""
    if not lectures:
        return list(rows)
    return [row for row in rows if row[index] in lectures]


def _linear_market(rng: random.Random) -> Dict:
    """Draw QD = a - bP and QS = c + dP with a positive integer solution."""
    while True:
        b = rng.choice([2, 3, 4, 5])
        d = rng.choice([1, 2, 3, 4])
        price = rng.choice([5, 8, 10, 12, 15, 20, 24, 25])
        c = rng.choice([10, 20, 25, 30, 40])
        # a is pinned so that a - b*P == c + d*P exactly at `price`.
        a = c + (b + d) * price
        quantity = c + d * price
        if quantity > 0 and a > 0:
            return {"a": a, "b": b, "c": c, "d": d, "price": price, "quantity": quantity}


def _unique_numeric_options(
    correct: int, candidates: List[int], rng: random.Random
) -> List[int]:
    """Pick three distinct, positive, plausible distractors."""
    options: List[int] = []
    for value in candidates:
        value = int(value)
        if value > 0 and value != correct and value not in options:
            options.append(value)
        if len(options) == 3:
            break
    # Backfill with nearby values if the error models collided.
    offset = 2
    while len(options) < 3:
        for value in (correct + offset, correct - offset):
            if value > 0 and value != correct and value not in options:
                options.append(value)
                if len(options) == 3:
                    break
        offset += rng.choice([1, 2, 3])
    return options[:3]


def equilibrium_price_question(rng: random.Random) -> Dict:
    """Solve a - bP = c + dP for the equilibrium price."""
    market = _linear_market(rng)
    a, b, c, d = market["a"], market["b"], market["c"], market["d"]
    good = rng.choice(MARKETS)["good"]
    correct = market["price"]
    distractors = _unique_numeric_options(
        correct,
        [
            (a + c) // (b + d),        # added the intercepts instead of subtracting
            (a - c) // max(b - d, 1),  # subtracted the slopes instead of adding
            (a - c) // (b + d) + 5,
            market["quantity"],        # answered with quantity instead of price
        ],
        rng,
    )
    return {
        "kind": "calc_equilibrium",
        "topic": "equilibrium",
        "question": (
            f"In the market for {good}, quantity demanded and quantity supplied are\n"
            f"QD = {a} - {b}P and QS = {c} + {d}P.\n"
            f"What is the equilibrium price?"
        ),
        "correct": f"P* = {correct}",
        "distractors": [f"P* = {v}" for v in distractors],
        "explanation": (
            f"Equilibrium requires QD = QS, so {a} - {b}P = {c} + {d}P. "
            f"Collecting terms gives {a - c} = {b + d}P, so P* = {a - c}/{b + d} = {correct}."
        ),
        "citation": EQUILIBRIUM_CITATION,
    }


def equilibrium_quantity_question(rng: random.Random) -> Dict:
    """Solve for equilibrium quantity by substituting P* back in."""
    market = _linear_market(rng)
    a, b, c, d = market["a"], market["b"], market["c"], market["d"]
    good = rng.choice(MARKETS)["good"]
    correct = market["quantity"]
    distractors = _unique_numeric_options(
        correct,
        [market["price"], a - b * market["price"] + market["price"], a, c],
        rng,
    )
    return {
        "kind": "calc_equilibrium",
        "topic": "equilibrium",
        "question": (
            f"In the market for {good},\n"
            f"QD = {a} - {b}P and QS = {c} + {d}P.\n"
            f"What is the equilibrium quantity?"
        ),
        "correct": f"Q* = {correct}",
        "distractors": [f"Q* = {v}" for v in distractors],
        "explanation": (
            f"First solve for the equilibrium price: {a} - {b}P = {c} + {d}P gives "
            f"P* = {market['price']}. Substituting into either equation, "
            f"Q* = {c} + {d}({market['price']}) = {correct}."
        ),
        "citation": EQUILIBRIUM_CITATION,
    }


def disequilibrium_question(rng: random.Random) -> Dict:
    """Identify a shortage or surplus at an off-equilibrium price."""
    market = _linear_market(rng)
    a, b, c, d = market["a"], market["b"], market["c"], market["d"]
    good = rng.choice(MARKETS)["good"]
    equilibrium_price = market["price"]

    below = rng.random() < 0.5
    step = rng.choice([2, 3, 4, 5])
    posted = equilibrium_price - step if below else equilibrium_price + step
    if posted <= 0:
        posted = equilibrium_price + step
        below = False

    demanded = a - b * posted
    supplied = c + d * posted
    gap = abs(demanded - supplied)
    label = "shortage" if below else "surplus"
    other = "surplus" if below else "shortage"
    direction = "upward" if below else "downward"

    distractors = [
        f"A {other} of {gap} units",
        f"A {label} of {demanded if below else supplied} units",
        "The market is already in equilibrium",
    ]
    return {
        "kind": "calc_equilibrium",
        "topic": "shortage-surplus",
        "question": (
            f"In the market for {good},\n"
            f"QD = {a} - {b}P and QS = {c} + {d}P.\n"
            f"If the price is held at P = {posted}, what is the result?"
        ),
        "correct": f"A {label} of {gap} units",
        "distractors": distractors,
        "explanation": (
            f"At P = {posted}, QD = {a} - {b}({posted}) = {demanded} and "
            f"QS = {c} + {d}({posted}) = {supplied}. "
            f"Since Q{'D' if below else 'S'} exceeds Q{'S' if below else 'D'}, there is a "
            f"{label} of {gap} units, which puts {direction} pressure on the price. "
            f"Equilibrium is at P* = {equilibrium_price}."
        ),
        "citation": "Lecture 5, §11-14 Shortages and Surpluses",
    }


def demand_shock_question(rng: random.Random) -> Dict:
    """Recompute equilibrium after a parallel shift in demand."""
    market = _linear_market(rng)
    a, b, c, d = market["a"], market["b"], market["c"], market["d"]
    good = rng.choice(MARKETS)["good"]
    shift = rng.choice([1, 2, 3]) * (b + d)  # keeps the new solution integral
    increase = rng.random() < 0.5
    new_a = a + shift if increase else a - shift
    new_price = (new_a - c) // (b + d)
    if new_price <= 0:
        increase, new_a = True, a + shift
        new_price = (new_a - c) // (b + d)
    new_quantity = c + d * new_price
    word = "increases" if increase else "decreases"

    distractors = _unique_numeric_options(
        new_price,
        [market["price"], market["price"] + shift, new_price + shift, new_quantity],
        rng,
    )
    return {
        "kind": "calc_equilibrium",
        "topic": "comparative-statics",
        "question": (
            f"The market for {good} starts at\n"
            f"QD = {a} - {b}P and QS = {c} + {d}P.\n"
            f"A change in tastes means quantity demanded {word} by {shift} units at "
            f"every price. What is the new equilibrium price?"
        ),
        "correct": f"P* = {new_price}",
        "distractors": [f"P* = {v}" for v in distractors],
        "explanation": (
            f"A shift of {shift} units at every price changes the intercept only: "
            f"QD' = {new_a} - {b}P. Setting QD' = QS gives {new_a} - {b}P = {c} + {d}P, "
            f"so P* = {new_a - c}/{b + d} = {new_price} "
            f"({'up' if increase else 'down'} from {market['price']})."
        ),
        "citation": SHOCK_CITATION,
    }


# ---------------------------------------------------------------- statics --

_STATICS_OUTCOMES = {
    ("demand", "increase"): ("rises", "rises"),
    ("demand", "decrease"): ("falls", "falls"),
    ("supply", "increase"): ("falls", "rises"),
    ("supply", "decrease"): ("rises", "falls"),
}

STATICS_SCENARIOS = [
    ("A new study reports health benefits from drinking coffee, and consumers "
     "want more coffee at every price.", "demand", "increase",
     "Lecture 5, §19 Example 1: Increased Demand for Coffee", 5),
    ("Roasting technology improves, lowering the cost of producing each bag of "
     "coffee.", "supply", "increase",
     "Lecture 5, §20 Example 2: Lower Production Costs", 5),
    ("A frost damages a large share of the coffee harvest.", "supply", "decrease",
     "Lecture 5, §21 Example 3: A Negative Supply Shock", 5),
    ("OPEC members agree to cut oil production.", "supply", "decrease",
     "Lecture 4, §18 Economics in the News: Oil and OPEC", 4),
    ("Incomes fall during a recession and restaurant meals are a normal good.",
     "demand", "decrease", "Lecture 3, §10.1 Income", 3),
    ("The price of tea, a substitute for coffee, rises sharply.", "demand",
     "increase", "Lecture 3, §10.2 Prices of Related Goods", 3),
    ("A government subsidy lowers the cost of every input lobster boats use.",
     "supply", "increase", "Lecture 4, §16.3 Taxes, Subsidies, and Regulation", 4),
    ("Many new coffee shops open in town.", "supply", "increase",
     "Lecture 4, §16.6 Number of Firms", 4),
    ("A popular film makes vinyl records fashionable again.", "demand",
     "increase", "Lecture 3, §10.3 Preferences, Expectations, and Buyers", 3),
    ("A new tax is imposed on every unit firms produce.", "supply", "decrease",
     "Lecture 4, §16.3 Taxes, Subsidies, and Regulation", 4),
]


def comparative_statics_question(
    rng: random.Random, lectures: Optional[List[int]] = None
) -> Dict:
    """Predict the effect of a shock on equilibrium price and quantity."""
    pool = _in_lectures(STATICS_SCENARIOS, lectures, index=4) or STATICS_SCENARIOS
    scenario, curve, direction, citation, _lecture = rng.choice(pool)
    price_effect, quantity_effect = _STATICS_OUTCOMES[(curve, direction)]
    shift_word = "rightward" if direction == "increase" else "leftward"

    def phrase(price: str, quantity: str) -> str:
        return f"Equilibrium price {price} and equilibrium quantity {quantity}"

    correct = phrase(price_effect, quantity_effect)
    all_options = [
        phrase(p, q) for p in ("rises", "falls") for q in ("rises", "falls")
    ]
    distractors = [option for option in all_options if option != correct]
    return {
        "kind": "comparative_statics",
        "topic": "comparative-statics",
        "question": (
            f"{scenario}\nHolding everything else constant, what happens in this market?"
        ),
        "correct": correct,
        "distractors": distractors,
        "explanation": (
            f"This is a change in a non-price determinant of {curve}, so the {curve} "
            f"curve shifts {shift_word} ({curve} {direction}s). Reading the new "
            f"intersection against the unchanged {'supply' if curve == 'demand' else 'demand'} "
            f"curve, equilibrium price {price_effect} and equilibrium quantity "
            f"{quantity_effect}."
        ),
        "citation": citation,
    }


# --------------------------------------------------- shift versus movement --

SHIFT_SCENARIOS = [
    ("The price of coffee rises and consumers buy fewer cups.",
     "A movement along the demand curve (a change in quantity demanded)",
     "demand-shifts",
     "A change in the good's own price moves buyers along a fixed demand curve. "
     "Demand itself has not changed.",
     "Lecture 3, §9 Movement Along a Demand Curve", 3),
    ("Household incomes rise and consumers buy more restaurant meals at every price.",
     "A shift of the demand curve",
     "demand-shifts",
     "Income is a non-price determinant of demand, so the whole demand curve shifts "
     "rightward for a normal good.",
     "Lecture 3, §10.1 Income", 3),
    ("The price of lattes falls and coffee shops choose to sell fewer of them.",
     "A movement along the supply curve (a change in quantity supplied)",
     "supply-shifts",
     "A change in the good's own price moves firms along a fixed supply curve. "
     "Supply itself has not changed.",
     "Lecture 4, §15 Movements Along Supply and Shifts of Supply", 4),
    ("The wage paid to baristas increases.",
     "A shift of the supply curve",
     "supply-shifts",
     "Input prices are a non-price determinant of supply, so the whole supply curve "
     "shifts leftward.",
     "Lecture 4, §16.1 Input Prices", 4),
    ("A better harvesting technology raises output per hour on coffee farms.",
     "A shift of the supply curve",
     "supply-shifts",
     "Technology is a non-price determinant of supply, so the whole supply curve "
     "shifts rightward.",
     "Lecture 4, §16.2 Technology and Productivity", 4),
    ("The price of gasoline falls and drivers fill up more often.",
     "A movement along the demand curve (a change in quantity demanded)",
     "demand-shifts",
     "The good's own price changed, so this is a change in quantity demanded, not a "
     "change in demand.",
     "Lecture 3, §11 Real-World Connection: Gasoline Demand", 3),
    ("Consumers expect the price of bicycles to rise sharply next month.",
     "A shift of the demand curve",
     "demand-shifts",
     "Expectations about future prices are a non-price determinant of demand, so "
     "current demand shifts.",
     "Lecture 3, §10.3 Preferences, Expectations, and Buyers", 3),
    ("A new regulation raises the cost of complying for every lobster boat.",
     "A shift of the supply curve",
     "supply-shifts",
     "Regulation changes production costs, a non-price determinant of supply, so the "
     "supply curve shifts leftward.",
     "Lecture 4, §16.3 Taxes, Subsidies, and Regulation", 4),
    ("Coffee farmers expect prices to be much higher next season, so they hold "
     "back some of this season's harvest.",
     "A shift of the supply curve",
     "supply-shifts",
     "Expectations about future prices are a non-price determinant of supply, so "
     "current supply shifts leftward.",
     "Lecture 4, §16.4 Expectations", 4),
    ("Unusually good weather produces a bumper lobster catch along the Maine "
     "coast.",
     "A shift of the supply curve",
     "supply-shifts",
     "Natural conditions are a non-price determinant of supply, so the supply "
     "curve shifts rightward.",
     "Lecture 4, §16.5 Natural Conditions", 4),
    ("Several coffee roasters leave the industry, reducing the number of firms.",
     "A shift of the supply curve",
     "supply-shifts",
     "The number of firms is a non-price determinant of supply, so market supply "
     "shifts leftward.",
     "Lecture 4, §16.6 Number of Firms", 4),
    ("The world price of oil rises and refiners increase the quantity of petrol "
     "they bring to market.",
     "A movement along the supply curve (a change in quantity supplied)",
     "supply-shifts",
     "The good's own price changed, so firms move along the existing supply curve; "
     "supply itself has not shifted.",
     "Lecture 4, §15 Movements Along Supply and Shifts of Supply", 4),
    ("More students move into the neighbourhood, increasing the number of coffee "
     "buyers.",
     "A shift of the demand curve",
     "demand-shifts",
     "The number of buyers is a non-price determinant of demand, so market demand "
     "shifts rightward.",
     "Lecture 3, §10.3 Preferences, Expectations, and Buyers", 3),
]

SHIFT_OPTIONS = [
    "A movement along the demand curve (a change in quantity demanded)",
    "A shift of the demand curve",
    "A movement along the supply curve (a change in quantity supplied)",
    "A shift of the supply curve",
]


def shift_vs_movement_question(
    rng: random.Random,
    topics: Optional[List[str]] = None,
    lectures: Optional[List[int]] = None,
) -> Dict:
    """Tell a shift of a curve apart from a movement along it."""
    pool = SHIFT_SCENARIOS
    if topics:
        # A demand-shifts quiz should not be handed a supply scenario.
        narrowed = [row for row in pool if row[2] in topics]
        pool = narrowed or pool
    narrowed = _in_lectures(pool, lectures, index=5)
    pool = narrowed or pool
    scenario, correct, topic, reason, citation, _lecture = rng.choice(pool)
    return {
        "kind": "shift_vs_movement",
        "topic": topic,
        "question": f"{scenario}\nWhich best describes what has happened?",
        "correct": correct,
        "distractors": [o for o in SHIFT_OPTIONS if o != correct],
        "explanation": reason,
        "citation": citation,
    }


# ------------------------------------------------------ reasoning and data --

NORMATIVE_STATEMENTS = [
    "The government ought to make tuition free for all students.",
    "Congestion pricing is unfair to low-income drivers.",
    "A country should always protect its domestic industries from imports.",
    "Coffee farmers deserve a higher share of the retail price.",
    "Inflation above two percent is unacceptable.",
]

POSITIVE_STATEMENTS = [
    "A higher cigarette tax reduces the quantity of cigarettes purchased.",
    "Congestion pricing in London reduced traffic in the charging zone.",
    "College graduates earn more on average than non-graduates.",
    "A frost that destroys part of the coffee harvest raises the price of coffee.",
    "The unemployment rate rose by half a percentage point last quarter.",
    "When the price of gasoline rises, households drive fewer miles.",
]


def positive_normative_question(rng: random.Random) -> Dict:
    """Distinguish a value judgement from a testable claim."""
    ask_normative = rng.random() < 0.5
    if ask_normative:
        correct = rng.choice(NORMATIVE_STATEMENTS)
        distractors = rng.sample(POSITIVE_STATEMENTS, 3)
        prompt = "Which of the following is a normative statement?"
        explanation = (
            f'"{correct}" makes a value judgement about what ought to be, so it cannot '
            "be settled by evidence alone. The other three are positive statements: "
            "claims about what is, which can in principle be tested against data."
        )
    else:
        correct = rng.choice(POSITIVE_STATEMENTS)
        distractors = rng.sample(NORMATIVE_STATEMENTS, 3)
        prompt = "Which of the following is a positive statement?"
        explanation = (
            f'"{correct}" is a claim about what is, and it can in principle be tested '
            "against evidence. The other three are normative: they assert what ought "
            "to be and rest on value judgements."
        )
    return {
        "kind": "positive_normative",
        "topic": "economic-reasoning",
        "question": prompt,
        "correct": correct,
        "distractors": distractors,
        "explanation": explanation,
        "citation": "Lecture 2, §10 Positive and Normative Economics",
    }


CAUSATION_SCENARIOS = [
    ("Towns with more firefighters tend to have more fire damage.",
     "Larger towns have both more fires and more firefighters, so town size drives "
     "both variables.",
     ["Hiring firefighters causes fire damage.",
      "Fire damage has no relationship to the number of firefighters.",
      "The correlation proves firefighters are ineffective."],
     "This is an omitted-variable problem: a third factor (town size) moves both "
     "series, so the correlation says nothing about cause."),
    ("Countries with more ice cream sales also have more drownings.",
     "Warm weather increases both ice cream sales and swimming.",
     ["Eating ice cream causes drownings.",
      "Drownings cause people to buy ice cream.",
      "The relationship must be a coincidence with no explanation."],
     "An omitted variable - the season - drives both series, so the correlation is "
     "not evidence of causation."),
    ("Students who attend review sessions score higher on exams.",
     "Students who were already more motivated are the ones who choose to attend.",
     ["Review sessions must be the sole cause of higher scores.",
      "Higher exam scores cause students to attend review sessions.",
      "The correlation shows review sessions have no effect."],
     "This is a selection problem: attendance is not random, so the comparison mixes "
     "the effect of the sessions with pre-existing differences between students."),
    ("Countries with more mobile phones per person have higher average incomes.",
     "Richer countries can afford more phones, so income drives phone ownership "
     "rather than the other way round.",
     ["Buying mobile phones makes a country rich.",
      "The relationship is impossible and the data must be wrong.",
      "Mobile phones have no economic effect of any kind."],
     "This is a reverse-causality problem: the correlation is real, but the causal "
     "arrow plausibly runs from income to phone ownership, not the reverse."),
    ("Hospitals with more staff per patient report more recorded infections.",
     "Better-staffed hospitals detect and record more of the infections that "
     "occur.",
     ["Hiring more staff causes infections.",
      "Infections cause hospitals to hire more staff that same year.",
      "The correlation proves staffing levels do not matter."],
     "This is a measurement problem: what is recorded depends on how hard anyone "
     "looks, so the correlation reflects detection rather than incidence."),
]


def correlation_causation_question(rng: random.Random) -> Dict:
    """Explain why a correlation need not be causal."""
    observation, correct, distractors, explanation = rng.choice(CAUSATION_SCENARIOS)
    return {
        "kind": "correlation_causation",
        "topic": "economic-reasoning",
        "question": (
            f"{observation}\nWhich explanation best shows why this correlation need "
            f"not imply causation?"
        ),
        "correct": correct,
        "distractors": list(distractors),
        "explanation": explanation,
        "citation": "Lecture 2, §11 Correlation and Causation",
    }


MARGINAL_SCENARIOS = [
    ("A coffee shop is deciding whether to stay open for one more hour. The extra "
     "hour would bring in $80 of revenue and cost $65 in wages and electricity.",
     "Stay open, because marginal benefit ($80) exceeds marginal cost ($65).",
     ["Close, because the shop has already covered its fixed costs.",
      "Close, because $65 is a large share of $80.",
      "Stay open only if the shop is profitable overall for the day."],
     "The decision rule compares the marginal benefit of the extra hour with its "
     "marginal cost. Because $80 > $65, the extra hour adds $15 of net benefit. "
     "Costs already incurred are irrelevant to the marginal decision."),
    ("A student is deciding whether to study one more hour. The extra hour would "
     "raise the expected exam score by 2 points, and the best alternative use of "
     "that hour is worth the equivalent of 5 points of well-being.",
     "Do not study the extra hour, because marginal cost exceeds marginal benefit.",
     ["Study the extra hour, because more studying always helps.",
      "Study the extra hour, because the exam score is what matters.",
      "The decision cannot be made without knowing total study hours."],
     "Marginal benefit (2 points) is below marginal cost (the 5-point value of the "
     "next-best use of the hour), so the extra hour is not worth it. The total time "
     "already spent studying does not enter the marginal comparison."),
    ("A bakery has already paid $500 in rent for the month. Baking one more tray "
     "of bread would cost $18 in ingredients and labour and bring in $30.",
     "Bake the tray, because marginal benefit ($30) exceeds marginal cost ($18).",
     ["Do not bake it, because the rent has not yet been recovered.",
      "Do not bake it, because $500 of rent makes the bakery unprofitable.",
      "Bake it only if total revenue for the month exceeds $500."],
     "The rent is already paid and does not change with this decision, so it is "
     "irrelevant at the margin. The tray adds $30 of revenue for $18 of cost, a "
     "$12 net gain."),
    ("A commuter is deciding whether to take one more trip by taxi this week. The "
     "trip saves 40 minutes, which they value at $20, and the fare is $26.",
     "Do not take the taxi, because marginal cost ($26) exceeds marginal benefit "
     "($20).",
     ["Take the taxi, because saving time is always worthwhile.",
      "Take the taxi, because they have already taken several this week.",
      "The answer depends on how much they have already spent on taxis."],
     "The decision rule compares the marginal benefit of this trip ($20 of time "
     "saved) with its marginal cost ($26). Because the cost is higher, the trip is "
     "not worth taking, and earlier trips do not change that."),
    ("A coffee shop already sells 100 lattes a day. The 101st latte would cost "
     "$2.40 in ingredients and labour and sell for $5.00.",
     "Sell it, because marginal revenue ($5.00) exceeds marginal cost ($2.40).",
     ["Do not sell it, because 100 lattes is the planned output.",
      "Do not sell it, because average cost matters more than marginal cost.",
      "Sell it only if the shop's total profit is already positive."],
     "Firms make production decisions at the margin: produce another unit whenever "
     "the revenue it brings in exceeds the extra cost of making it. Here the 101st "
     "latte adds $2.60 of profit."),
    ("A museum is deciding whether to stay open one extra hour. The hour would "
     "cost $300 in staffing and attract visitors paying $260 in total.",
     "Close on time, because marginal cost ($300) exceeds marginal benefit ($260).",
     ["Stay open, because more visitors are always better.",
      "Stay open, because the museum's fixed costs are already paid.",
      "The decision depends on the museum's total annual attendance."],
     "The extra hour costs $300 and brings in $260, so it reduces net benefit by "
     "$40. Fixed costs already incurred do not change the marginal comparison."),
]


def marginal_decision_question(rng: random.Random) -> Dict:
    """Apply the marginal benefit vs marginal cost decision rule."""
    scenario, correct, distractors, explanation = rng.choice(MARGINAL_SCENARIOS)
    return {
        "kind": "marginal_decision",
        "topic": "marginal-analysis",
        "question": f"{scenario}\nWhat does marginal analysis recommend?",
        "correct": correct,
        "distractors": list(distractors),
        "explanation": explanation,
        "citation": "Lecture 2, §9 Marginal Benefits, Marginal Costs, and the Decision Rule",
    }


OPPORTUNITY_COST_SCENARIOS = [
    ("You have a free ticket to a concert tonight. Your next-best alternative is a "
     "shift at work paying $60, which you value at $60. You would have paid up to "
     "$100 to attend the concert.",
     "$60 - the value of the next-best alternative you give up.",
     ["$0, because the ticket was free.",
      "$100, because that is what the concert is worth to you.",
      "$160, the ticket value plus the forgone wage."],
     "Opportunity cost is the value of the next-best alternative forgone. The ticket "
     "price is irrelevant here because it was free; what you give up is the $60 shift."),
    ("A student spends a year at college. Tuition and fees are $20,000, and the job "
     "they would otherwise have taken pays $25,000.",
     "$45,000 - tuition plus the forgone earnings.",
     ["$20,000, because only tuition is an actual payment.",
      "$25,000, because forgone earnings are the only real cost.",
      "$5,000, the difference between forgone earnings and tuition."],
     "Economic cost includes both explicit payments ($20,000 of tuition) and implicit "
     "costs ($25,000 of forgone earnings), giving a total opportunity cost of $45,000."),
    ("You bought a $40 ticket to a show last month; the ticket cannot be resold or "
     "refunded. On the night, you would rather stay home, which you value at $15.",
     "$0 for the ticket, because it is a sunk cost; the cost of going is the $15 "
     "evening at home.",
     ["$40, because that is what the ticket cost.",
      "$55, the ticket price plus the value of staying home.",
      "$25, the difference between the ticket price and staying home."],
     "A sunk cost cannot be recovered and so should not enter the decision. The "
     "only opportunity cost of attending is the next-best alternative forgone - the "
     "$15 evening at home."),
    ("A firm owns a warehouse outright. It could rent the warehouse out for $3,000 "
     "a month, but instead uses it to store its own inventory.",
     "$3,000 a month - the rent forgone by using the space itself.",
     ["$0, because the firm already owns the warehouse and pays no rent.",
      "The original purchase price of the warehouse, spread over its life.",
      "It cannot be determined without knowing the firm's revenue."],
     "Economic cost includes implicit costs. Even though no payment changes hands, "
     "using the warehouse means giving up $3,000 of rent each month, and that "
     "forgone rent is the opportunity cost."),
    ("A student can spend Saturday working a shift worth $90, studying (worth an "
     "estimated $120 to them), or hiking (worth $70). They choose to study.",
     "$90 - the value of the next-best alternative, the shift.",
     ["$160, the value of both alternatives they gave up.",
      "$70, the value of the hike.",
      "$120, the value of what they chose."],
     "Opportunity cost counts only the next-best alternative forgone, not the sum "
     "of everything given up. The best alternative to studying was the $90 shift."),
    ("A city owns a vacant lot. It can build a car park that would generate "
     "$80,000 a year, a playground worth an estimated $50,000 a year in community "
     "value, or sell the lot for a one-off $400,000. It builds the playground.",
     "$80,000 a year - the value of the next-best alternative, the car park.",
     ["$130,000 a year, the value of both rejected options.",
      "$50,000 a year, the value of the playground itself.",
      "$400,000, the sale price of the lot."],
     "Opportunity cost counts only the next-best alternative forgone. Among the "
     "rejected options, the car park's $80,000 a year is the highest-value annual "
     "alternative, so that is the opportunity cost."),
    ("A friend gives you a voucher for a $50 dinner that cannot be exchanged or "
     "sold. You use it on an evening when your alternative was a free concert you "
     "value at $30.",
     "$30 - the value of the concert you gave up.",
     ["$50, the face value of the voucher.",
      "$0, because the voucher was a gift.",
      "$80, the voucher value plus the concert value."],
     "Because the voucher cannot be exchanged or sold, using it costs you nothing "
     "you could otherwise have had. The only thing given up is the $30 concert."),
    ("An employee turns down a promotion that pays $12,000 more per year in order "
     "to keep their current schedule, which they value at $15,000 a year.",
     "$12,000 a year - the extra pay forgone.",
     ["$15,000 a year, the value of the schedule they kept.",
      "$3,000 a year, the difference between the two values.",
      "$0, because they did not change jobs."],
     "The opportunity cost of keeping the current role is the next-best "
     "alternative given up: the $12,000 of additional pay. (That they value the "
     "schedule at $15,000 is why the choice makes sense, not the cost of it.)"),
    ("A farmer can plant a field with wheat, worth $9,000, or barley, worth "
     "$7,000, but the field will take only one crop. They plant wheat.",
     "$7,000 - the value of the barley crop forgone.",
     ["$9,000, the value of the wheat crop.",
      "$16,000, the value of both crops.",
      "$2,000, the difference between the two crops."],
     "The opportunity cost of planting wheat is the value of the next-best use of "
     "the field, which is the $7,000 barley crop."),
]


def opportunity_cost_question(rng: random.Random) -> Dict:
    """Compute an opportunity cost including implicit costs."""
    scenario, correct, distractors, explanation = rng.choice(OPPORTUNITY_COST_SCENARIOS)
    return {
        "kind": "calc_opportunity_cost",
        "topic": "opportunity-cost",
        "question": f"{scenario}\nWhat is the opportunity cost of the choice?",
        "correct": correct,
        "distractors": list(distractors),
        "explanation": explanation,
        "citation": "Lecture 2, §3 Opportunity Cost",
    }


PROFIT_SCENARIOS = [
    ("A coffee shop sells 180 lattes a day at $5 each. Its daily explicit costs are "
     "$600, and the owner gives up a $150-a-day job to run the shop.",
     900, 600, 150),
    ("A bakery sells 240 loaves a week at $6 each. Weekly explicit costs are $1,000, "
     "and the owner forgoes $300 a week in alternative earnings.",
     1440, 1000, 300),
]


def profit_question(rng: random.Random) -> Dict:
    """Distinguish accounting profit from economic profit."""
    scenario, revenue, explicit, implicit = rng.choice(PROFIT_SCENARIOS)
    accounting = revenue - explicit
    economic = accounting - implicit
    ask_economic = rng.random() < 0.5
    correct_value = economic if ask_economic else accounting
    other_value = accounting if ask_economic else economic
    label = "economic profit" if ask_economic else "accounting profit"
    return {
        "kind": "calc_profit",
        "topic": "firms-costs",
        "question": f"{scenario}\nWhat is the {label}?",
        "correct": f"${correct_value:,}",
        "distractors": [
            f"${other_value:,}",
            f"${revenue:,}",
            f"${revenue - implicit:,}",
        ],
        "explanation": (
            f"Revenue is ${revenue:,} and explicit costs are ${explicit:,}, so "
            f"accounting profit is ${accounting:,}. Economic profit also subtracts the "
            f"implicit cost of the owner's forgone earnings (${implicit:,}), giving "
            f"${economic:,}. The question asks for {label}, so the answer is "
            f"${correct_value:,}."
        ),
        "citation": "Lecture 4, §8 Understanding Costs",
    }


COST_STRUCTURE_SCENARIOS = [
    ("Monthly rent on the coffee shop's storefront", "A fixed cost",
     "Rent does not change with the number of lattes produced this month, so it is a "
     "fixed cost in the short run."),
    ("Milk and coffee beans used to make each latte", "A variable cost",
     "Input use rises and falls with output, so these are variable costs."),
    ("The insurance premium paid once a year regardless of output", "A fixed cost",
     "The premium is owed whatever the shop produces, so it is a fixed cost."),
    ("Hourly wages for baristas scheduled according to how busy the shop is",
     "A variable cost",
     "Hours scheduled move with output, so these wages are a variable cost."),
]

COST_OPTIONS = ["A fixed cost", "A variable cost", "A sunk revenue", "A marginal benefit"]


def cost_structure_question(rng: random.Random) -> Dict:
    """Classify a cost as fixed or variable in the short run."""
    item, correct, explanation = rng.choice(COST_STRUCTURE_SCENARIOS)
    return {
        "kind": "cost_structure",
        "topic": "firms-costs",
        "question": (
            f"In the short run, how should a firm classify the following?\n{item}"
        ),
        "correct": correct,
        "distractors": [o for o in COST_OPTIONS if o != correct],
        "explanation": explanation,
        "citation": "Lecture 4, §9 Fixed and Variable Costs",
    }


# Which lecture each generator's material comes from, so a lecture-filtered
# quiz never asks about content the student has not reached.
GENERATOR_LECTURES = {
    equilibrium_price_question: {5},
    equilibrium_quantity_question: {5},
    disequilibrium_question: {5},
    demand_shock_question: {5},
    comparative_statics_question: {3, 4, 5},
    shift_vs_movement_question: {3, 4},
    positive_normative_question: {2},
    correlation_causation_question: {2},
    marginal_decision_question: {2},
    opportunity_cost_question: {2},
    profit_question: {4},
    cost_structure_question: {4},
}

# Which generators accept a lecture filter of their own (because their
# scenarios span several lectures).
_LECTURE_AWARE = {comparative_statics_question, shift_vs_movement_question}
_TOPIC_AWARE = {shift_vs_movement_question}

# Generators keyed by the topic they serve, so a topic-filtered quiz can draw
# only from the templates that belong to it.
TEMPLATE_GENERATORS = {
    "equilibrium": [equilibrium_price_question, equilibrium_quantity_question],
    "shortage-surplus": [disequilibrium_question],
    "comparative-statics": [comparative_statics_question, demand_shock_question],
    "demand-shifts": [shift_vs_movement_question],
    "supply-shifts": [shift_vs_movement_question],
    "economic-reasoning": [positive_normative_question, correlation_causation_question],
    "marginal-analysis": [marginal_decision_question],
    "opportunity-cost": [opportunity_cost_question],
    "firms-costs": [profit_question, cost_structure_question],
}


def generators_for(
    topics: Optional[List[str]] = None, lectures: Optional[List[int]] = None
) -> List:
    """Return template generators matching the requested topics and lectures.

    Each returned callable takes only an RNG; any topic or lecture narrowing a
    generator supports is bound in here.
    """
    if topics:
        selected = []
        for topic in topics:
            for generator in TEMPLATE_GENERATORS.get(topic, []):
                if generator not in selected:
                    selected.append(generator)
    else:
        selected = []
        for group in TEMPLATE_GENERATORS.values():
            for generator in group:
                if generator not in selected:
                    selected.append(generator)

    bound = []
    for generator in selected:
        if lectures and not (GENERATOR_LECTURES.get(generator, set()) & set(lectures)):
            continue
        kwargs = {}
        if generator in _TOPIC_AWARE and topics:
            kwargs["topics"] = list(topics)
        if generator in _LECTURE_AWARE and lectures:
            kwargs["lectures"] = list(lectures)
        bound.append(partial(generator, **kwargs) if kwargs else generator)
    return bound


# ---------------------------------------------------------------------------
# Foundations (Lectures 1-3). These topics are discussed narratively rather
# than procedurally, so without templates they yield only a handful of
# questions. Each template below is anchored to a specific lecture section.
# ---------------------------------------------------------------------------

# (prompt, correct, distractors, explanation, citation, topic)
ECONOMICS_SCOPE = [
    ("Which statement best reflects how this course defines economics?",
     "The study of how individuals, firms, governments, and societies make choices "
     "under scarcity, and how those choices shape the allocation of resources.",
     ["The study of money, banking, and financial markets.",
      "The study of how businesses maximise their profits.",
      "The study of government budgets and taxation."],
     "The course opens with this definition, and stresses that the key word is "
     "scarcity: economics is about choice under constraint, not about money in "
     "particular.",
     "Lecture 1, §1 What Is Economics?", "what-is-economics"),
    ("A billionaire still has to decide how to spend the hours in a day. Which "
     "economic idea does this illustrate?",
     "Scarcity, because resources such as time are limited relative to wants "
     "regardless of wealth.",
     ["Poverty, because every person faces unmet needs.",
      "Inflation, because the value of time falls over time.",
      "A shortage, because demand for their time exceeds supply."],
     "The lecture is explicit that scarcity does not mean poverty. Scarcity means "
     "resources - time, income, land, labour, attention - are limited relative to "
     "wants, which is true at every level of wealth.",
     "Lecture 1, §1 What Is Economics?", "scarcity-choice"),
    ("Why does the course say it is not about memorising formulas?",
     "Because its aim is to teach how economists organise complex social questions "
     "so they can be reasoned about clearly.",
     ["Because intro economics contains no formulas.",
      "Because formulas are covered in later courses only.",
      "Because economic models are not used in this course."],
     "The first lecture frames the course as training in economic reasoning - "
     "scarcity, incentives, tradeoffs, opportunity cost, models, and evidence - "
     "rather than formula recall.",
     "Lecture 1, Purpose of the First Class", "what-is-economics"),
    ("Which of the following is the best example of a tradeoff?",
     "A town can use a plot of land for a park or for housing, but not both.",
     ["A shop runs out of a popular item on a busy Saturday.",
      "Prices in an economy rise by three percent over a year.",
      "A currency becomes more expensive relative to another."],
     "Scarcity forces choices, and a tradeoff is what you must give up to get "
     "something else. The other options describe a shortage, inflation, and an "
     "exchange-rate movement respectively.",
     "Lecture 2, §1 Scarcity: The Starting Point", "scarcity-choice"),
    ("A shop sells out of umbrellas during a storm. Is this an example of "
     "scarcity in the economic sense?",
     "No - that is a shortage at the going price; scarcity is the permanent "
     "condition that resources are limited relative to wants.",
     ["Yes - scarcity and shortage mean the same thing.",
      "Yes - because consumers cannot get what they want.",
      "No - because umbrellas are not a scarce resource."],
     "Economists distinguish the two. Scarcity is the background condition that "
     "makes economics necessary at all; a shortage is a temporary situation in a "
     "particular market where quantity demanded exceeds quantity supplied at the "
     "current price.",
     "Lecture 2, §1 Scarcity: The Starting Point", "scarcity-choice"),
    ("Why does the course organise itself around the global economy?",
     "Because many important economic choices today cross national borders.",
     ["Because domestic economics has already been solved.",
      "Because international data is easier to obtain than national data.",
      "Because global topics require no economic theory."],
     "Lecture 1 makes the case that households, firms, governments, students, and "
     "central banks all participate in a global economic system, so the most "
     "important issues today involve cross-border connections.",
     "Lecture 1, §4 Why a Global Theme?", "what-is-economics"),
    ("A smartphone's design, operating system, chips, minerals, and assembly come "
     "from different countries. Why does the course use this example?",
     "To show that international economics appears in everyday consumption, "
     "prices, jobs, and technology rather than being remote or abstract.",
     ["To show that smartphones are unusually complicated products.",
      "To argue that countries should produce everything domestically.",
      "To illustrate that trade only matters for luxury goods."],
     "The smartphone embodies trade in goods and services, intellectual property, "
     "foreign investment, exchange rates, labour markets, and policy all at once, "
     "which is why the lecture uses it to make the global economy concrete.",
     "Lecture 1, §5 A Simple Example: The Smartphone", "what-is-economics"),
    ("Which of the following is a question about how resources are allocated?",
     "Should the town use its remaining budget for road repair or for the library?",
     ["What is the population of the town?",
      "How many hours are there in a working week?",
      "What language is spoken in the town?"],
     "Economics studies choices under scarcity and how those choices shape the "
     "allocation of resources. Only the budget question involves choosing between "
     "competing uses of a limited resource.",
     "Lecture 1, §1 What Is Economics?", "what-is-economics"),
    ("A student says \"economics is really just about money\". How does the "
     "course respond?",
     "Economics is a way of thinking about choices, tradeoffs, incentives, "
     "institutions, and evidence, of which money is only one part.",
     ["Money is indeed the only subject matter of economics.",
      "Economics is about business strategy rather than money.",
      "Economics is about predicting stock prices."],
     "The closing section of Lecture 1 makes exactly this point: economics is not "
     "only about money or business, but about how choices are made under scarcity.",
     "Lecture 1, §9 What Students Should Take Away", "what-is-economics"),
    ("Why does the course say economic models are useful even though they "
     "simplify?",
     "A model is a simplified representation designed to clarify one mechanism at "
     "a time.",
     ["Models are useful because they describe reality completely.",
      "Models are useful because they avoid the need for data.",
      "Models are useful because they always predict the future correctly."],
     "Economists simplify deliberately: a model strips away detail so that one "
     "mechanism can be seen clearly, and is judged by whether it clarifies that "
     "mechanism, not by whether it reproduces everything.",
     "Lecture 1, §3 Economics as a Way of Thinking", "what-is-economics"),
    ("Which of the following best describes what scarcity forces?",
     "Choices, because wanting more than the available resources allow means "
     "something must be given up.",
     ["Poverty, because scarce resources mean people go without necessities.",
      "Inflation, because scarce goods rise in price.",
      "Trade deficits, because scarce goods must be imported."],
     "Scarcity is the starting point of the whole course: resources are limited "
     "relative to wants, so choices must be made, and every choice has an "
     "opportunity cost.",
     "Lecture 2, §1 Scarcity: The Starting Point", "scarcity-choice"),
    ("Water available to the Panama Canal became limited during a drought, so "
     "fewer ships could transit. Which idea does this illustrate most directly?",
     "Scarcity, because a limited resource forced a choice about how to allocate "
     "it among competing users.",
     ["Inflation, because transit fees rose.",
      "Normative economics, because the allocation was unfair.",
      "Correlation without causation, because drought and shipping moved "
      "together."],
     "The lecture uses the Panama Canal as a concrete case of scarcity: with less "
     "water available, not every ship could pass, so the canal authority had to "
     "decide how to allocate a limited resource.",
     "Lecture 2, §2 Real-World Example: Water Scarcity and the Panama Canal",
     "scarcity-choice"),
    ("Which pair of ideas does the course link most directly?",
     "Scarcity and opportunity cost, because a choice made under scarcity means "
     "giving up the next-best alternative.",
     ["Scarcity and inflation, because scarce goods always rise in price.",
      "Scarcity and GDP, because scarce economies produce less.",
      "Scarcity and exchange rates, because scarce currencies are expensive."],
     "Scarcity forces choices; the value of the next-best alternative given up by "
     "a choice is its opportunity cost. The two ideas are introduced together for "
     "that reason.",
     "Lecture 2, §3 Opportunity Cost", "scarcity-choice"),
    ("A factory can run its machines to make either bicycles or scooters, but not "
     "both at once. What is the economic name for what it gives up?",
     "The opportunity cost of the choice.",
     ["The accounting cost of the choice.",
      "The sunk cost of the choice.",
      "The fixed cost of the choice."],
     "The value of the next-best alternative forgone - the scooters not made - is "
     "the opportunity cost of making bicycles.",
     "Lecture 2, §3 Opportunity Cost", "scarcity-choice"),
    ("Which of the following is the clearest example of an economic resource "
     "that is scarce?",
     "A student's time during exam week.",
     ["The number of hours the library lists on its website.",
      "The alphabet used to write an essay.",
      "A publicly available formula in a textbook."],
     "A resource is scarce when it is limited relative to the uses people want to "
     "put it to. Time is the standard example: using an hour one way means not "
     "using it another. Information that can be used by everyone at once is not "
     "scarce in this sense.",
     "Lecture 2, §1 Scarcity: The Starting Point", "scarcity-choice"),
    ("A government must decide between funding a new rail line and funding "
     "additional hospital beds. What makes this an economic problem?",
     "Resources are limited relative to the uses they could be put to, so "
     "choosing one means giving up the other.",
     ["The decision involves large sums of money.",
      "The decision is made by a government rather than a household.",
      "The decision will be reported in the news."],
     "What makes a question economic is scarcity and the tradeoff it forces, not "
     "the size of the sums or who is deciding.",
     "Lecture 2, §1 Scarcity: The Starting Point", "scarcity-choice"),
    ("The course previews three connected parts. What is the role of the first, "
     "on economic foundations?",
     "It builds the reasoning toolkit - scarcity, opportunity cost, incentives, "
     "marginal thinking, evidence, and models - used throughout the rest.",
     ["It covers the history of economic thought.",
      "It teaches the mathematics needed for later courses.",
      "It surveys the economies of individual countries."],
     "Lecture 1 sets out the structure of the course, and Lecture 2 then builds "
     "the core toolkit that the market and policy material depends on.",
     "Lecture 1, §7 Preview of the Course", "what-is-economics"),
    ("Which of the following best captures the habits of economic reasoning the "
     "course introduces?",
     "Thinking in terms of scarcity, incentives, tradeoffs, opportunity costs, "
     "models, and evidence.",
     ["Memorising formulas and applying them to exam questions.",
      "Forecasting the stock market from historical prices.",
      "Learning the accounting rules that firms must follow."],
     "The first lecture lists exactly these habits as the core of the course, and "
     "states explicitly that it is not a course about memorising formulas.",
     "Lecture 1, Purpose of the First Class", "what-is-economics"),
]


def economics_scope_question(
    rng: random.Random,
    topics: Optional[List[str]] = None,
    lectures: Optional[List[int]] = None,
) -> Dict:
    """What economics is, what scarcity means, and why the global theme."""
    pool = ECONOMICS_SCOPE
    if topics:
        pool = [row for row in pool if row[5] in topics] or ECONOMICS_SCOPE
    if lectures:
        # These scenarios span Lectures 1 and 2; the citation names which.
        wanted = tuple(f"Lecture {n}," for n in lectures)
        pool = [row for row in pool if row[4].startswith(wanted)] or pool
    prompt, correct, distractors, explanation, citation, topic = rng.choice(pool)
    return {
        "kind": "concept_application",
        "topic": topic,
        "question": prompt,
        "correct": correct,
        "distractors": list(distractors),
        "explanation": explanation,
        "citation": citation,
    }


GLOBALIZATION_CHANNELS = [
    "goods and services", "capital and finance", "people and migration",
    "technology, information, and ideas",
]
NOT_CHANNELS = [
    "national borders and passports", "weather and climate patterns",
    "language and religion", "military alliances",
]


def globalization_question(rng: random.Random) -> Dict:
    """The four cross-border flows the course treats as globalization."""
    if rng.random() < 0.5:
        correct = rng.choice(GLOBALIZATION_CHANNELS)
        distractors = rng.sample(NOT_CHANNELS, 3)
        prompt = (
            "The course treats globalization as a set of cross-border flows. "
            "Which of the following is one of them?"
        )
        explanation = (
            "Lecture 1 lists four channels of economic globalization: goods and "
            "services; capital and finance; people and migration; and technology, "
            f"information, and ideas. \"{correct.capitalize()}\" is one of them."
        )
    else:
        correct = rng.choice(NOT_CHANNELS)
        distractors = rng.sample(GLOBALIZATION_CHANNELS, 3)
        prompt = (
            "The course treats globalization as a set of cross-border flows. "
            "Which of the following is NOT one of them?"
        )
        explanation = (
            "The four channels are goods and services; capital and finance; people "
            f"and migration; and technology, information, and ideas. "
            f"\"{correct.capitalize()}\" is not among them."
        )
    return {
        "kind": "concept_application",
        "topic": "global-economy",
        "question": prompt,
        "correct": correct.capitalize(),
        "distractors": [d.capitalize() for d in distractors],
        "explanation": explanation,
        "citation": "Lecture 1, §4 Why a Global Theme?",
    }


INDICATORS = [
    ("GDP", "The value of final goods and services produced in an economy",
     "How large is the economy?"),
    ("Inflation", "A sustained increase in the overall price level",
     "Why does money buy less over time?"),
    ("An exchange rate", "The price of one currency in terms of another",
     "Why does travelling or importing get cheaper or more expensive?"),
    ("A market", "A setting in which buyers and sellers interact",
     "How are prices determined?"),
]


def indicator_question(rng: random.Random) -> Dict:
    """Match a headline economic indicator to what it measures."""
    target = rng.choice(INDICATORS)
    others = [row for row in INDICATORS if row[0] != target[0]]
    if rng.random() < 0.5:
        prompt = f"What does {target[0].lower()} measure?"
        correct, distractors = target[1], [row[1] for row in others]
        explanation = (
            f"{target[0]} is {target[1][0].lower()}{target[1][1:]}. It answers the "
            f"question: {target[2]}"
        )
    else:
        prompt = f'Which term does the course describe as "{target[1].lower()}"?'
        correct, distractors = target[0], [row[0] for row in others]
        explanation = (
            f"{target[0]} is {target[1][0].lower()}{target[1][1:]} ({target[2]})"
        )
    return {
        "kind": "concept_application",
        "topic": "global-economy",
        "question": prompt,
        "correct": correct,
        "distractors": distractors,
        "explanation": explanation,
        "citation": "Lecture 1, §8 Key Terms from Lecture 1",
    }


DATA_QUESTIONS = [
    "What exactly is being measured?",
    "What is the unit of measurement?",
    "What is the time period?",
    "What is the source?",
    "What interpretation is justified by the data, and what interpretation is not?",
]
NOT_DATA_QUESTIONS = [
    "Does the number support the argument I already wanted to make?",
    "Is the chart visually appealing?",
    "Has the number been reported by more than one newspaper?",
    "Is the number large enough to be interesting?",
    "How many decimal places does the figure have?",
    "Was the figure published recently enough to feel current?",
]

DATA_SOURCES = [
    ("FRED", "an online database maintained by the Federal Reserve Bank of St. Louis "
             "holding hundreds of thousands of economic time series"),
    ("The World Bank's World Development Indicators",
     "a major source of cross-country comparable development data"),
    ("The Bureau of Economic Analysis",
     "the agency that defines GDP as the value of final goods and services produced "
     "in the United States"),
    ("The International Monetary Fund",
     "the body the lecture quotes defining economic globalization as the "
     "increasing integration of economies through cross-border movements of "
     "goods, services, and capital"),
]


DATA_INTERPRETATION = [
    ("A headline reports that national GDP rose by 4% last year.",
     "Output grew, but the figure alone says nothing about how the gains were "
     "distributed.",
     ["Everyone in the country became 4% better off.",
      "Inflation must have been 4% as well.",
      "The country now has a trade surplus."],
     "GDP measures the value of final goods and services produced. It does not "
     "measure distribution, prices, or trade balances, so none of those readings "
     "follow from the growth figure by itself."),
    ("A chart shows unemployment in two countries, one measured monthly and the "
     "other quarterly.",
     "The series are not directly comparable until the time periods are put on "
     "the same basis.",
     ["The country with the lower number has the healthier labour market.",
      "The monthly series is always more accurate.",
      "The difference in frequency has no bearing on the comparison."],
     "One of the five questions to ask of any data is what the time period is. "
     "Comparing series measured over different periods without adjustment is "
     "exactly the interpretation the lecture warns against."),
    ("A report states that average income in a region is $62,000.",
     "Little can be said about a typical household without knowing whether this "
     "is a mean or a median and how incomes are spread.",
     ["A typical household in the region earns $62,000.",
      "Half of households earn more than $62,000.",
      "The region is wealthier than any region with a lower average."],
     "What exactly is being measured is the first question to ask. A mean can sit "
     "far from the typical household when incomes are skewed, so the headline "
     "figure does not by itself describe a typical household."),
]


def data_literacy_question(rng: random.Random) -> Dict:
    """The five questions to ask of data, and the course's data sources."""
    if rng.random() < 0.5:
        correct = rng.choice(DATA_QUESTIONS)
        return {
            "kind": "concept_application",
            "topic": "data-literacy",
            "question": (
                "The course lists five questions to ask whenever you work with "
                "economic data. Which of the following is one of them?"
            ),
            "correct": correct,
            "distractors": rng.sample(NOT_DATA_QUESTIONS, 3),
            "explanation": (
                "The five questions are: what exactly is being measured; what is the "
                "unit of measurement; what is the time period; what is the source; "
                "and what interpretation is justified by the data. The other options "
                "describe motivated reasoning rather than data literacy."
            ),
            "citation": "Lecture 1, §6 Economic Data Literacy",
        }
    if rng.random() < 0.35:
        claim, correct, distractors, explanation = rng.choice(DATA_INTERPRETATION)
        return {
            "kind": "concept_application",
            "topic": "data-literacy",
            "question": f"{claim}\nWhich interpretation is justified by that alone?",
            "correct": correct,
            "distractors": list(distractors),
            "explanation": explanation,
            "citation": "Lecture 1, §6 Economic Data Literacy",
        }
    target = rng.choice(DATA_SOURCES)
    others = [row for row in DATA_SOURCES if row[0] != target[0]]
    distractors = [row[0] for row in others] + ["The International Monetary Fund"]
    return {
        "kind": "concept_application",
        "topic": "data-literacy",
        "question": f"Which data source does the course describe as {target[1]}?",
        "correct": target[0],
        "distractors": distractors[:3],
        "explanation": f"{target[0]} is {target[1]}.",
        "citation": "Lecture 1, §6 Economic Data Literacy",
    }


PPF_SCENARIOS = [
    ("A point that lies exactly on the production possibilities frontier",
     "Resources are being used fully.",
     ["Some resources are unused or used inefficiently.",
      "The combination is not currently feasible.",
      "Opportunity cost has fallen to zero."],
     "A point on the frontier uses available resources fully; a point inside "
     "indicates unused or inefficiently used resources, and a point beyond is not "
     "currently feasible."),
    ("A point that lies inside the production possibilities frontier",
     "Some resources are unused or used inefficiently.",
     ["Resources are being used fully.",
      "The combination is not currently feasible.",
      "The economy is producing more than its resources allow."],
     "A point inside the frontier means the economy could produce more of at least "
     "one output without giving up any of the other, so resources are idle or "
     "poorly allocated."),
    ("A point that lies beyond the production possibilities frontier",
     "The combination is not currently feasible.",
     ["Resources are being used fully.",
      "Some resources are unused or used inefficiently.",
      "Opportunity cost is negative at that point."],
     "A point beyond the frontier cannot be reached with currently available "
     "resources and technology."),
    ("The bowed-out shape of a typical production possibilities frontier",
     "Opportunity cost increases as resources are shifted toward uses they suit "
     "less well.",
     ["Opportunity cost is constant along the frontier.",
      "Opportunity cost falls as more of a good is produced.",
      "Resources are perfectly interchangeable between the two outputs."],
     "The bowed-out shape reflects increasing opportunity cost: resources are not "
     "equally suited to both outputs, so shifting more of them raises the amount "
     "given up per extra unit."),
    ("An economy moves from one point on its production possibilities frontier to "
     "another, producing more of good A",
     "It must produce less of good B, because resources have to be shifted away "
     "from it.",
     ["It can also produce more of good B, because the economy is efficient.",
      "Good B's production is unaffected by the move.",
      "The frontier itself shifts outward."],
     "Moving along the frontier illustrates opportunity cost: with resources and "
     "technology fixed, producing more of one output requires giving up some of "
     "the other."),
    ("A new technology lets an economy produce more of both goods with the same "
     "resources",
     "The frontier itself shifts outward.",
     ["The economy moves along its existing frontier.",
      "The economy moves to a point inside its existing frontier.",
      "Opportunity cost becomes zero."],
     "The frontier describes what is possible given available resources and "
     "technology. When technology improves, the set of feasible combinations grows, "
     "which is shown as an outward shift of the whole frontier."),
]


def ppf_question(rng: random.Random) -> Dict:
    """Read a production possibilities frontier."""
    subject, correct, distractors, explanation = rng.choice(PPF_SCENARIOS)
    return {
        "kind": "concept_application",
        "topic": "models-ppf",
        "question": f"{subject}. What does this tell you?",
        "correct": correct,
        "distractors": list(distractors),
        "explanation": explanation,
        "citation": "Lecture 2, §13 The Production Possibilities Frontier",
    }


def ceteris_paribus_question(rng: random.Random) -> Dict:
    """What the ceteris paribus assumption is for."""
    variants = [
        ("What does the assumption ceteris paribus do in an economic model?",
         "It holds other relevant determinants constant so the effect of one change "
         "can be isolated.",
         ["It claims that the rest of the world genuinely stops changing.",
          "It removes the need to gather evidence.",
          "It guarantees that the model's prediction will be correct."],
         "Ceteris paribus means \"all other relevant things held constant\". The "
         "lecture is explicit that it does not claim the real world freezes; it is "
         "an analytical device for understanding one mechanism at a time."),
        ("Gasoline prices rise while income, weather, population, and transit "
         "options are also changing. How does ceteris paribus reasoning help?",
         "It asks what would happen if only the price changed, so the price effect "
         "can be separated from the others.",
         ["It shows that the other determinants do not matter.",
          "It proves that the price change caused the whole observed change.",
          "It allows the economist to ignore evidence about the other factors."],
         "With several determinants moving at once, the effect of the price change "
         "cannot be read directly. Economists first ask the simplified question - "
         "what if only price changed - and then bring the other factors back in."),
    ]
    prompt, correct, distractors, explanation = rng.choice(variants)
    return {
        "kind": "concept_application",
        "topic": "models-ppf",
        "question": prompt,
        "correct": correct,
        "distractors": list(distractors),
        "explanation": explanation,
        "citation": "Lecture 2, §14 Ceteris Paribus: Holding Other Things Constant",
    }


INCENTIVE_SCENARIOS = [
    ("A city introduces a charge for driving into the centre at peak times.",
     "Fewer drivers enter the centre at peak times, because the cost of doing so "
     "has risen.",
     ["Driving into the centre becomes more attractive.",
      "The number of drivers is unaffected, because people must commute.",
      "Congestion rises because drivers hurry to beat the charge."],
     "An incentive is anything that changes the benefits or costs of an action. "
     "Raising the private cost of peak-time driving reduces the quantity of it, "
     "which is what congestion pricing is designed to do."),
    ("A government raises the tax on cigarettes.",
     "The quantity of cigarettes purchased falls, because the private cost of "
     "smoking has risen.",
     ["Cigarette purchases are unchanged, because smoking is a habit.",
      "Cigarette purchases rise, because the product now seems more valuable.",
      "Only the tax revenue changes; behaviour never responds to price."],
     "Taxes change the costs of an action, and people respond to changed costs. The "
     "lecture is careful to note that responses are not mechanical, but the "
     "direction of the effect is to reduce the quantity purchased."),
    ("An employer raises the wage it offers for a hard-to-fill role.",
     "More people apply, because the benefit of taking the job has risen.",
     ["Fewer people apply, because the job must be unpleasant.",
      "The number of applicants does not depend on the wage.",
      "Applications rise only if the employer also advertises more."],
     "Higher wages raise the benefit of the action, and incentives that raise the "
     "benefit of an action increase how much of it people choose to do."),
    ("A supermarket starts charging for plastic bags that used to be free.",
     "Shoppers bring their own bags more often, because using a store bag now "
     "has a cost.",
     ["Bag use is unchanged, because the charge is small.",
      "Shoppers buy more groceries to justify the bag charge.",
      "The store's revenue determines how many bags shoppers use."],
     "Attaching even a small cost to an action that was free changes behaviour, "
     "because it changes the cost side of the decision."),
    ("A university announces that attendance will no longer count toward the "
     "course grade.",
     "Attendance falls, because one of the benefits of attending has been removed.",
     ["Attendance rises, because students feel trusted.",
      "Attendance is unaffected, because students attend for the content.",
      "Attendance depends only on the difficulty of the material."],
     "Removing a benefit of an action reduces how much of it people choose to do. "
     "The lecture notes that responses are not mechanical, but the direction of "
     "the incentive effect is clear."),
    ("A city pays residents a deposit refund for each returned drinks container.",
     "More containers are returned, because returning one now carries a reward.",
     ["Fewer containers are returned, because the scheme is inconvenient.",
      "Container purchases fall to zero.",
      "Return rates depend only on how environmentally minded residents are."],
     "A refund raises the benefit of returning a container, and people respond to "
     "incentives that raise the benefit of an action."),
    ("A toll road raises its price during rush hour and lowers it at night.",
     "Some drivers shift their trips to off-peak hours, because the relative cost "
     "of travelling at each time has changed.",
     ["Total traffic disappears, because drivers refuse to pay tolls.",
      "Traffic patterns are unaffected, because commuting times are fixed.",
      "Only the toll operator's revenue changes."],
     "Incentives work on the margin between alternatives. Changing the relative "
     "price of peak and off-peak travel moves some trips from one to the other, "
     "which is the logic behind congestion pricing."),
    ("A landlord offers tenants a rent discount for paying early.",
     "More tenants pay early, because early payment now carries a benefit.",
     ["Tenants pay later, to avoid appearing eager.",
      "Payment timing does not respond to price.",
      "The discount changes only the landlord's accounting, not behaviour."],
     "The discount raises the benefit of an action - paying early - so more people "
     "choose it."),
    ("A country introduces a tax credit for households that install insulation.",
     "More households insulate, because the net cost of doing so has fallen.",
     ["Fewer households insulate, because the paperwork is a deterrent.",
      "Insulation rates depend only on the weather.",
      "Only the government's budget changes, not household behaviour."],
     "A credit lowers the cost of an action, and lowering the cost of an action "
     "increases how much of it people choose to do."),
    ("A gym changes from a per-visit fee to an unlimited monthly membership.",
     "Members visit more often, because the cost of one additional visit has "
     "fallen to zero.",
     ["Members visit less often, because they have already paid.",
      "Visit frequency does not respond to the pricing structure.",
      "The gym's total revenue determines how often members attend."],
     "Marginal reasoning applies: under a per-visit fee each visit has a positive "
     "marginal cost, while under a flat membership the marginal cost of one more "
     "visit is zero, so more visits are worth making."),
]


def incentive_question(rng: random.Random) -> Dict:
    """Predict a behavioural response to a change in costs or benefits."""
    scenario, correct, distractors, explanation = rng.choice(INCENTIVE_SCENARIOS)
    return {
        "kind": "concept_application",
        "topic": "incentives",
        "question": f"{scenario}\nWhat does economic reasoning predict?",
        "correct": correct,
        "distractors": list(distractors),
        "explanation": explanation,
        "citation": "Lecture 2, §5 Incentives",
    }


def market_demand_question(rng: random.Random) -> Dict:
    """Add individual demands horizontally to get market demand."""
    price = rng.choice([2, 3, 4, 5, 6])
    quantities = [rng.randint(2, 9) for _ in range(3)]
    total = sum(quantities)
    names = ["Ana", "Ben", "Chen"]
    listing = "; ".join(
        f"{name} would buy {q}" for name, q in zip(names, quantities)
    )
    return {
        "kind": "calc_market_demand",
        "topic": "demand",
        "question": (
            f"A market has only three consumers. At a price of ${price}, {listing}.\n"
            f"What is the market quantity demanded at ${price}?"
        ),
        "correct": str(total),
        "distractors": [
            str(v)
            for v in _unique_numeric_options(
                total,
                [max(quantities), round(total / 3), total + price,
                 total - min(quantities)],
                rng,
            )
        ],
        "explanation": (
            f"Market demand is the horizontal sum of individual demands: at each "
            f"price, add the quantities every consumer would buy. Here "
            f"{' + '.join(str(q) for q in quantities)} = {total}."
        ),
        "citation": "Lecture 3, §8 Individual Demand and Market Demand",
    }


def market_supply_question(rng: random.Random) -> Dict:
    """Add individual firm supplies horizontally to get market supply."""
    price = rng.choice([4, 5, 6, 8, 10])
    quantities = [rng.randint(5, 20) for _ in range(3)]
    total = sum(quantities)
    listing = "; ".join(
        f"Firm {letter} would sell {q}" for letter, q in zip("ABC", quantities)
    )
    return {
        "kind": "calc_market_supply",
        "topic": "supply",
        "question": (
            f"Three firms serve a market. At a price of ${price}, {listing}.\n"
            f"What is the market quantity supplied at ${price}?"
        ),
        "correct": str(total),
        "distractors": [
            str(v)
            for v in _unique_numeric_options(
                total,
                [max(quantities), round(total / 3), total - min(quantities),
                 total + price],
                rng,
            )
        ],
        "explanation": (
            f"Market supply is the horizontal sum of individual firms' supply "
            f"curves: at each price, add the quantities every firm would sell. Here "
            f"{' + '.join(str(q) for q in quantities)} = {total}."
        ),
        "citation": "Lecture 4, §14 Individual Supply and Market Supply",
    }


def law_of_demand_question(rng: random.Random) -> Dict:
    """Apply the law of demand to a small schedule."""
    good = rng.choice(MARKETS)["good"]
    low, high = rng.choice([(2, 4), (3, 6), (5, 8), (4, 7)])
    q_low = rng.randint(30, 60)
    q_high = q_low - rng.randint(8, 20)
    return {
        "kind": "concept_application",
        "topic": "demand",
        "question": (
            f"A demand schedule for {good} shows that at ${low} consumers would buy "
            f"{q_low} units. According to the law of demand, what is the most likely "
            f"quantity demanded at ${high}, holding everything else constant?"
        ),
        "correct": str(q_high),
        "distractors": [
            str(v)
            for v in _unique_numeric_options(
                q_high, [q_low + (q_low - q_high), q_low, q_low * 2], rng
            )
        ],
        "explanation": (
            f"The law of demand says that, holding other relevant factors constant, "
            f"a higher price leads to a lower quantity demanded. Price rises from "
            f"${low} to ${high}, so quantity demanded must fall below {q_low}; "
            f"{q_high} is the only option that does."
        ),
        "citation": "Lecture 3, §3 The Law of Demand",
    }


def willingness_to_pay_question(rng: random.Random) -> Dict:
    """Compare willingness to pay with the market price."""
    wtp = rng.choice([4, 5, 6, 7, 8, 9])
    gap = rng.choice([1, 2, 3])
    buys = rng.random() < 0.5
    price = wtp - gap if buys else wtp + gap
    if buys:
        correct = f"Buy, gaining ${gap} of surplus on the purchase."
        distractors = [
            f"Buy, gaining ${wtp} of surplus on the purchase.",
            "Not buy, because the price is below what the good is worth to them.",
            "It cannot be determined without knowing the consumer's income.",
        ]
        explanation = (
            f"Willingness to pay is the most the consumer would pay rather than go "
            f"without: ${wtp}. The price is ${price}, which is below that, so the "
            f"purchase is worth making and the consumer gains ${wtp} - ${price} = "
            f"${gap}."
        )
    else:
        correct = "Not buy, because the price exceeds their willingness to pay."
        distractors = [
            f"Buy, gaining ${gap} of surplus on the purchase.",
            "Buy, because willingness to pay is always the amount actually paid.",
            "It cannot be determined without knowing the consumer's income.",
        ]
        explanation = (
            f"Willingness to pay is ${wtp}, the most the consumer would pay rather "
            f"than go without. The price is ${price}, which is higher, so buying "
            f"would leave them worse off and they do not buy."
        )
    return {
        "kind": "concept_application",
        "topic": "consumer-choice",
        "question": (
            f"A consumer's willingness to pay for one more cup of coffee is ${wtp}, "
            f"and the price is ${price}.\nWhat should they do?"
        ),
        "correct": correct,
        "distractors": distractors,
        "explanation": explanation,
        "citation": "Lecture 3, §5 Willingness to Pay",
    }


def budget_constraint_question(rng: random.Random) -> Dict:
    """Check whether a bundle is affordable."""
    coffee_price = rng.choice([3, 4, 5])
    meal_price = rng.choice([8, 10, 12])
    budget = coffee_price * rng.randint(2, 4) + meal_price * rng.randint(1, 2)
    coffees = rng.randint(1, 4)
    meals = rng.randint(1, 3)
    cost = coffee_price * coffees + meal_price * meals
    affordable = cost <= budget
    correct = (
        f"Yes - the bundle costs ${cost}, which is within the ${budget} budget."
        if affordable
        else f"No - the bundle costs ${cost}, which exceeds the ${budget} budget."
    )
    distractors = [
        (f"No - the bundle costs ${cost}, which exceeds the ${budget} budget."
         if affordable
         else f"Yes - the bundle costs ${cost}, which is within the ${budget} budget."),
        f"Yes - the bundle costs ${coffee_price * coffees}, counting only the coffees.",
        "It cannot be determined without knowing the consumer's preferences.",
    ]
    return {
        "kind": "calc_budget",
        "topic": "consumer-choice",
        "question": (
            f"A student has ${budget} to spend. Coffee costs ${coffee_price} and a "
            f"meal costs ${meal_price}.\nCan they afford {coffees} coffees and "
            f"{meals} meals?"
        ),
        "correct": correct,
        "distractors": distractors,
        "explanation": (
            f"The budget constraint is {coffee_price}C + {meal_price}M <= {budget}. "
            f"This bundle costs {coffee_price}({coffees}) + {meal_price}({meals}) = "
            f"${cost}, which is "
            f"{'within' if affordable else 'above'} the ${budget} budget, so it is "
            f"{'affordable' if affordable else 'not affordable'}."
        ),
        "citation": "Lecture 3, §7 Budget Constraints and Consumer Choice",
    }


TEMPLATE_GENERATORS["what-is-economics"] = [economics_scope_question]
TEMPLATE_GENERATORS["scarcity-choice"] = [economics_scope_question]
TEMPLATE_GENERATORS["global-economy"] = [globalization_question, indicator_question]
TEMPLATE_GENERATORS["data-literacy"] = [data_literacy_question]
TEMPLATE_GENERATORS["models-ppf"] = [ppf_question, ceteris_paribus_question]
TEMPLATE_GENERATORS["incentives"] = [incentive_question]
TEMPLATE_GENERATORS["demand"] = [market_demand_question, law_of_demand_question]
TEMPLATE_GENERATORS["supply"] = [market_supply_question]
TEMPLATE_GENERATORS["consumer-choice"] = [
    willingness_to_pay_question,
    budget_constraint_question,
]

_TOPIC_AWARE.add(economics_scope_question)
_LECTURE_AWARE.add(economics_scope_question)

GENERATOR_LECTURES.update({
    economics_scope_question: {1, 2},
    globalization_question: {1},
    indicator_question: {1},
    data_literacy_question: {1},
    ppf_question: {2},
    ceteris_paribus_question: {2},
    incentive_question: {2},
    market_demand_question: {3},
    law_of_demand_question: {3},
    willingness_to_pay_question: {3},
    budget_constraint_question: {3},
    market_supply_question: {4},
})
