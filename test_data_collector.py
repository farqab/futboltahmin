from data_collector import fetch_real_matches_for_date


def run_smoke_test(date_str='20260920'):
    """Manually exercise the live ESPN integration; not a unit test."""
    m = fetch_real_matches_for_date(date_str)
    print(f"[OK] {len(m)} mac alindi")
    if not m:
        return
    m0 = m[0]
    print(f"  Ornek: {m0.get('home_name')} vs {m0.get('away_name')}")
    print(f"  H2H: {m0.get('h2h_summary')}")
    print(f"  Momentum: Ev={m0.get('home_momentum')} | Dep={m0.get('away_momentum')}")
    print(f"  Form: Ev={m0.get('home_form')} | Dep={m0.get('away_form')}")
    print(f"  Rotation Riski: Ev={m0.get('home_rotation_risk')} | Dep={m0.get('away_rotation_risk')}")
    print(f"  Ev sahibi ev performansi: {m0.get('home_home_wins')}/{m0.get('home_home_total')} galibiyet")
    print(f"  Dep deplasman performansi: {m0.get('away_away_wins')}/{m0.get('away_away_total')} galibiyet")
    print(f"  Son 5 gol (ev): {m0.get('home_scored_last5')} attı / {m0.get('home_conceded_last5')} yedi")
    print(f"  Son 5 gol (dep): {m0.get('away_scored_last5')} attı / {m0.get('away_conceded_last5')} yedi")
    print(f"  xG destekleniyor mu: {m0.get('xg_supported')}")
    print(f"  Oran (1-X-2): {m0.get('odds')}")


if __name__ == "__main__":
    run_smoke_test()
