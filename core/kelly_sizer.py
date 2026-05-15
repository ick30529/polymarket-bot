def compute_bet_size(
    estimated_prob: float,
    implied_prob: float,
    bankroll: float,
    kelly_fraction: float = 0.25,
    min_bet: float = 2.0,
    max_bet_pct: float = 0.10,
) -> float:
    edge = estimated_prob - implied_prob
    if edge <= 0:
        return 0.0
    net_odds = (1.0 - implied_prob) / implied_prob
    full_kelly = (estimated_prob * net_odds - (1.0 - estimated_prob)) / net_odds
    if full_kelly <= 0:
        return 0.0
    bet = bankroll * full_kelly * kelly_fraction
    max_bet = bankroll * max_bet_pct
    return max(min_bet, min(bet, max_bet))
