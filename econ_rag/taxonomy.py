"""Economics topic taxonomy.

One stable slug per topic, with keywords used both for semantic retrieval and
for assigning a primary topic to each chunk at ingest time. The taxonomy is
intentionally subject-level rather than lecture-level, so that a textbook
chapter on demand lands under the same `demand` topic as Lecture 3.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Topic:
    slug: str
    name: str
    description: str
    keywords: List[str]
    # Lecture numbers that currently cover this topic (informational).
    lectures: List[int] = field(default_factory=list)


TOPICS: List[Topic] = [
    Topic(
        "what-is-economics",
        "What Is Economics",
        "The definition and scope of economics, and why it is studied.",
        ["economics definition", "study of choices", "allocation of resources",
         "microeconomics macroeconomics", "why study economics"],
        [1],
    ),
    Topic(
        "scarcity-choice",
        "Scarcity, Choice, and Tradeoffs",
        "Limited resources relative to unlimited wants, and the tradeoffs that follow.",
        ["scarcity", "limited resources", "unlimited wants", "tradeoff",
         "choices under scarcity", "rationing"],
        [1, 2],
    ),
    Topic(
        "opportunity-cost",
        "Opportunity Cost",
        "The value of the next-best alternative forgone.",
        ["opportunity cost", "next-best alternative", "forgone", "explicit cost",
         "implicit cost", "sunk cost", "true cost of a choice"],
        [1, 2],
    ),
    Topic(
        "incentives",
        "Incentives",
        "How changes in costs and benefits change behavior.",
        ["incentive", "respond to incentives", "congestion pricing", "subsidy",
         "penalty", "unintended consequences", "behavior change"],
        [2],
    ),
    Topic(
        "marginal-analysis",
        "Marginal Reasoning",
        "Decisions at the margin: marginal benefit, marginal cost, and the decision rule.",
        ["marginal benefit", "marginal cost", "thinking at the margin",
         "one more unit", "decision rule", "marginal analysis", "diminishing returns"],
        [2, 4],
    ),
    Topic(
        "economic-reasoning",
        "Positive vs Normative, Correlation vs Causation",
        "How economists evaluate claims and evidence.",
        ["positive statement", "normative statement", "correlation", "causation",
         "omitted variable", "reverse causality", "evidence", "value judgment"],
        [2],
    ),
    Topic(
        "models-ppf",
        "Economic Models, Ceteris Paribus, and the PPF",
        "Why economists simplify, and the production possibilities frontier.",
        ["economic model", "simplifying assumption", "ceteris paribus",
         "production possibilities frontier", "PPF", "efficiency", "abstraction"],
        [2],
    ),
    Topic(
        "global-economy",
        "The Global Economy",
        "Trade, GDP, inflation, and exchange rates as course themes.",
        ["global economy", "international trade", "GDP", "inflation",
         "exchange rate", "cross-border", "imports exports", "globalization"],
        [1],
    ),
    Topic(
        "data-literacy",
        "Economic Data Literacy",
        "Finding, organizing, and presenting economic data as evidence.",
        ["economic data", "data literacy", "tables and figures", "excel",
         "data sources", "interpreting statistics", "evidence"],
        [1],
    ),
    Topic(
        "demand",
        "Demand and the Law of Demand",
        "Demand vs quantity demanded, demand schedules, and demand curves.",
        ["demand", "quantity demanded", "law of demand", "demand schedule",
         "demand curve", "downward sloping", "substitution effect", "income effect"],
        [3],
    ),
    Topic(
        "consumer-choice",
        "Willingness to Pay and Consumer Choice",
        "Willingness to pay, budget constraints, and gains from exchange.",
        ["willingness to pay", "budget constraint", "consumer choice",
         "consumer surplus", "voluntary exchange", "reservation price"],
        [3],
    ),
    Topic(
        "demand-shifts",
        "Shifts in Demand",
        "What moves a demand curve versus what moves along it.",
        ["shift in demand", "movement along demand curve", "income",
         "normal good", "inferior good", "substitutes", "complements",
         "preferences", "expectations", "number of buyers"],
        [3],
    ),
    Topic(
        "firms-costs",
        "Firms, Revenue, Costs, and Profit",
        "Why firms exist, and how revenue, economic cost, and profit relate.",
        ["firm", "revenue", "economic cost", "accounting profit",
         "economic profit", "fixed cost", "variable cost", "total cost",
         "entrepreneur", "specialization"],
        [4],
    ),
    Topic(
        "supply",
        "Supply and the Law of Supply",
        "Supply vs quantity supplied, supply schedules, and supply curves.",
        ["supply", "quantity supplied", "law of supply", "supply schedule",
         "supply curve", "upward sloping", "marginal cost and supply"],
        [4],
    ),
    Topic(
        "supply-shifts",
        "Shifts in Supply",
        "What moves a supply curve versus what moves along it.",
        ["shift in supply", "movement along supply curve", "input prices",
         "technology", "taxes and subsidies", "regulation", "expectations",
         "natural conditions", "number of firms"],
        [4],
    ),
    Topic(
        "equilibrium",
        "Market Equilibrium",
        "Where quantity demanded equals quantity supplied, graphically and algebraically.",
        ["market equilibrium", "equilibrium price", "equilibrium quantity",
         "QD = QS", "market clearing", "intersection of supply and demand",
         "solving for equilibrium"],
        [5],
    ),
    Topic(
        "shortage-surplus",
        "Shortages, Surpluses, and Price Adjustment",
        "What happens when price is above or below equilibrium.",
        ["shortage", "surplus", "excess demand", "excess supply",
         "price adjustment", "upward pressure on price", "downward pressure on price"],
        [5],
    ),
    Topic(
        "comparative-statics",
        "Comparative Statics",
        "Predicting how equilibrium changes after a demand or supply shock.",
        ["comparative statics", "market shock", "demand shock", "supply shock",
         "four-step framework", "rightward shift", "leftward shift",
         "effect on equilibrium price and quantity"],
        [5],
    ),
]

BY_SLUG: Dict[str, Topic] = {t.slug: t for t in TOPICS}


# Section-title fragments that map decisively to a topic. Checked (lowercased,
# longest first) before falling back to embedding similarity.
SECTION_HINTS: Dict[str, str] = {
    "what is economics": "what-is-economics",
    "basic economic vocabulary": "what-is-economics",
    "economics as a way of thinking": "what-is-economics",
    "preview of the course": "what-is-economics",
    "what students should take away": "what-is-economics",
    "why a global theme": "global-economy",
    "economic data literacy": "data-literacy",
    "scarcity": "scarcity-choice",
    "water scarcity": "scarcity-choice",
    "opportunity cost": "opportunity-cost",
    "education, earnings": "opportunity-cost",
    "incentives": "incentives",
    "congestion pricing": "incentives",
    "thinking like an economist": "economic-reasoning",
    "marginal thinking": "marginal-analysis",
    "marginal benefits, marginal costs": "marginal-analysis",
    "positive and normative": "economic-reasoning",
    "correlation and causation": "economic-reasoning",
    "why economists build models": "models-ppf",
    "production possibilities frontier": "models-ppf",
    "ceteris paribus": "models-ppf",
    "what makes economic thinking useful": "economic-reasoning",
    "what is a market": "demand",
    "demand and quantity demanded": "demand",
    "law of demand": "demand",
    "why does quantity demanded fall": "demand",
    "demand schedules and demand curves": "demand",
    "willingness to pay": "consumer-choice",
    "voluntary exchange benefits consumers": "consumer-choice",
    "budget constraints": "consumer-choice",
    "individual demand and market demand": "demand",
    "movement along a demand curve": "demand-shifts",
    "shifts in demand": "demand-shifts",
    "income": "demand-shifts",
    "prices of related goods": "demand-shifts",
    "preferences, expectations": "demand-shifts",
    "gasoline demand": "demand-shifts",
    "household spending": "consumer-choice",
    "why do firms exist": "firms-costs",
    "role of firms": "firms-costs",
    "entrepreneurs and firms": "firms-costs",
    "coffee shop running example": "firms-costs",
    "objective of the firm": "firms-costs",
    "revenue": "firms-costs",
    "understanding costs": "firms-costs",
    "fixed and variable costs": "firms-costs",
    "the coffee shop example": "firms-costs",
    "marginal analysis and the firm": "marginal-analysis",
    "why marginal cost often rises": "marginal-analysis",
    "supply and quantity supplied": "supply",
    "the law of supply": "supply",
    "supply schedules and supply curves": "supply",
    "individual supply and market supply": "supply",
    "movements along supply and shifts": "supply-shifts",
    "what shifts supply": "supply-shifts",
    "input prices": "supply-shifts",
    "technology and productivity": "supply-shifts",
    "taxes, subsidies, and regulation": "supply-shifts",
    "natural conditions": "supply-shifts",
    "number of firms": "supply-shifts",
    "coffee supply": "supply-shifts",
    "oil and opec": "supply-shifts",
    "maine lobster": "supply-shifts",
    "markets as coordination": "equilibrium",
    "coordination problem": "equilibrium",
    "market equilibrium": "equilibrium",
    "numerical view of market equilibrium": "equilibrium",
    "market shock appears in the equations": "comparative-statics",
    "what equilibrium does": "equilibrium",
    "why prices matter": "equilibrium",
    "markets are out of balance": "shortage-surplus",
    "shortages": "shortage-surplus",
    "surpluses": "shortage-surplus",
    "logic of price adjustment": "shortage-surplus",
    "visualizing price adjustment": "shortage-surplus",
    "comparative statics": "comparative-statics",
    "four-step framework": "comparative-statics",
    "increased demand for coffee": "comparative-statics",
    "lower production costs": "comparative-statics",
    "negative supply shock": "comparative-statics",
    "reading economic news": "comparative-statics",
}

_SORTED_HINTS = sorted(SECTION_HINTS.items(), key=lambda kv: -len(kv[0]))


def topic_from_section(section_title: Optional[str]) -> Optional[str]:
    """Map a section title to a topic slug, or None if no hint matches."""
    if not section_title:
        return None
    lowered = section_title.lower()
    for fragment, slug in _SORTED_HINTS:
        if fragment in lowered:
            return slug
    return None


def topic_name(slug: Optional[str]) -> str:
    topic = BY_SLUG.get(slug or "")
    return topic.name if topic else "General Economics"


def all_topics() -> List[Dict]:
    """Serializable topic list for the API/UI."""
    return [
        {
            "slug": t.slug,
            "name": t.name,
            "description": t.description,
            "lectures": t.lectures,
        }
        for t in TOPICS
    ]
