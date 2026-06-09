# Phase5.5 Repair5G.1 Agent-Aware Dual-Channel Dev Report

This is diagnostic-only representation evidence. It does not permit Phase5.5 or Phase6.

## Gates

- build_passed: `True`
- schema_errors: `0`
- missing_rows: `0`
- no_solver_crashes: `True`
- all_costs_finite: `True`
- cost_bounds_respected: `True`
- additive_parity_exact: `False`
- laur_disable_parity_exact: `False`
- laur_force_additive_direct_parity_exact: `False`
- dual_additive_parity_exact: `False`
- dual_c_equiv_additive_parity_exact: `False`
- dual_c_equiv_locked_matches_scalar: `False`
- dual_c_equiv_best_f4_static_matches_scalar: `False`
- critical_smoke_gates_passed: `False`
- phase5p5_allowed: `False`
- phase6_allowed: `False`

## Scope

- maps: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- agents: `[50, 100]`
- instance_ids: `[26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45]`
- row_count: `17040` / `17040`

## Method Stats

| method | rows | better | equal | worse | mean delta ratio vs LTM |
|---|---:|---:|---:|---:|---:|
| `always_additive_defer` | 120 | 1 | 113 | 5 | 0.0006638499938260865 |
| `laur_disable` | 120 | 2 | 114 | 4 | 0.0017236751620512817 |
| `laur_force_additive_direct` | 120 | 2 | 114 | 4 | 9.234320895652073e-05 |
| `repair5f4_best_static_c125_b125_w075_d095_diagnostic_only` | 120 | 34 | 59 | 26 | 3.1148973801721254e-05 |
| `repair5f_candidate_additive_ltm` | 120 | 2 | 112 | 6 | 0.0007430965399122792 |
| `repair5f_static_c100_b100_w075_d090` | 120 | 26 | 60 | 33 | 0.001813925672016939 |
| `repair5g1_agent_additive_lf0p01_min0p5` | 120 | 20 | 58 | 42 | 0.005321145594714272 |
| `repair5g1_agent_additive_lf0p01_min0p75` | 120 | 19 | 62 | 38 | 0.0051376578155861935 |
| `repair5g1_agent_additive_lf0p01_min1` | 120 | 20 | 61 | 39 | 0.005182333100939117 |
| `repair5g1_agent_additive_lf0p025_min0p5` | 120 | 28 | 55 | 37 | 0.0002157020902086876 |
| `repair5g1_agent_additive_lf0p025_min0p75` | 120 | 28 | 54 | 38 | 0.00021759421380700941 |
| `repair5g1_agent_additive_lf0p025_min1` | 120 | 27 | 54 | 39 | 0.0014379225215263073 |
| `repair5g1_agent_additive_lf0p05_min0p5` | 120 | 26 | 56 | 37 | 0.0020674960344035055 |
| `repair5g1_agent_additive_lf0p05_min0p75` | 120 | 27 | 57 | 35 | 0.0012335392427130398 |
| `repair5g1_agent_additive_lf0p05_min1` | 120 | 26 | 55 | 39 | 0.0031470333391327397 |
| `repair5g1_agent_additive_lf0p1_min0p5` | 120 | 26 | 57 | 37 | 0.003235621639513269 |
| `repair5g1_agent_additive_lf0p1_min0p75` | 120 | 27 | 56 | 37 | 0.0030196487755803506 |
| `repair5g1_agent_additive_lf0p1_min1` | 120 | 26 | 59 | 35 | 0.0031793499588260816 |
| `repair5g1_agent_additive_lf0p2_min0p5` | 120 | 30 | 53 | 37 | 0.0036692988511896484 |
| `repair5g1_agent_additive_lf0p2_min0p75` | 120 | 28 | 52 | 39 | 0.004151820826330428 |
| `repair5g1_agent_additive_lf0p2_min1` | 120 | 30 | 53 | 37 | 0.0036692988511896484 |
| `repair5g1_agent_c100_b100_w075_d095_lf0p01_min0p5` | 120 | 18 | 57 | 45 | 0.004530861838964904 |
| `repair5g1_agent_c100_b100_w075_d095_lf0p01_min0p75` | 120 | 19 | 58 | 43 | 0.004080016221408688 |
| `repair5g1_agent_c100_b100_w075_d095_lf0p01_min1` | 120 | 18 | 59 | 43 | 0.004452743531396544 |
| `repair5g1_agent_c100_b100_w075_d095_lf0p025_min0p5` | 120 | 31 | 59 | 30 | 0.0016948551137948643 |
| `repair5g1_agent_c100_b100_w075_d095_lf0p025_min0p75` | 120 | 30 | 59 | 31 | 0.0029435579331965733 |
| `repair5g1_agent_c100_b100_w075_d095_lf0p025_min1` | 120 | 31 | 59 | 30 | 0.0016948551137948643 |
| `repair5g1_agent_c100_b100_w075_d095_lf0p05_min0p5` | 120 | 25 | 59 | 36 | 0.004313700701661009 |
| `repair5g1_agent_c100_b100_w075_d095_lf0p05_min0p75` | 120 | 24 | 59 | 37 | 0.0051799625493728725 |
| `repair5g1_agent_c100_b100_w075_d095_lf0p05_min1` | 120 | 26 | 56 | 38 | 0.003703624140660862 |
| `repair5g1_agent_c100_b100_w075_d095_lf0p1_min0p5` | 120 | 28 | 57 | 35 | 0.0008490623231196509 |
| `repair5g1_agent_c100_b100_w075_d095_lf0p1_min0p75` | 120 | 27 | 55 | 38 | 0.0019066131409130357 |
| `repair5g1_agent_c100_b100_w075_d095_lf0p1_min1` | 120 | 28 | 55 | 37 | 0.000863828624391297 |
| `repair5g1_agent_c100_b100_w075_d095_lf0p2_min0p5` | 120 | 28 | 59 | 33 | 0.002152249825330427 |
| `repair5g1_agent_c100_b100_w075_d095_lf0p2_min0p75` | 120 | 28 | 59 | 33 | 0.0011287502756782532 |
| `repair5g1_agent_c100_b100_w075_d095_lf0p2_min1` | 120 | 28 | 61 | 31 | 0.0011094553991709327 |
| `repair5g1_agent_c100_b125_w075_d100_lf0p01_min0p5` | 120 | 30 | 57 | 33 | 0.0002715840209316215 |
| `repair5g1_agent_c100_b125_w075_d100_lf0p01_min0p75` | 120 | 30 | 57 | 33 | 0.0002715840209316215 |
| `repair5g1_agent_c100_b125_w075_d100_lf0p01_min1` | 120 | 30 | 56 | 34 | 0.0002739252624913769 |
| `repair5g1_agent_c100_b125_w075_d100_lf0p025_min0p5` | 120 | 30 | 57 | 32 | 0.003777920166957254 |
| `repair5g1_agent_c100_b125_w075_d100_lf0p025_min0p75` | 120 | 30 | 57 | 32 | 0.003777920166957254 |
| `repair5g1_agent_c100_b125_w075_d100_lf0p025_min1` | 120 | 32 | 58 | 30 | 0.0022626945843559217 |
| `repair5g1_agent_c100_b125_w075_d100_lf0p05_min0p5` | 120 | 28 | 59 | 33 | 0.0020138780387672314 |
| `repair5g1_agent_c100_b125_w075_d100_lf0p05_min0p75` | 120 | 29 | 61 | 30 | 0.0009740356358220252 |
| `repair5g1_agent_c100_b125_w075_d100_lf0p05_min1` | 120 | 28 | 60 | 32 | 0.001996665405957255 |
| `repair5g1_agent_c100_b125_w075_d100_lf0p1_min0p5` | 120 | 26 | 60 | 34 | 0.003138698496886955 |
| `repair5g1_agent_c100_b125_w075_d100_lf0p1_min0p75` | 120 | 26 | 60 | 34 | 0.003138698496886955 |
| `repair5g1_agent_c100_b125_w075_d100_lf0p1_min1` | 120 | 25 | 61 | 34 | 0.0034791660538965492 |
| `repair5g1_agent_c100_b125_w075_d100_lf0p2_min0p5` | 120 | 33 | 55 | 32 | 0.001851415190880335 |
| `repair5g1_agent_c100_b125_w075_d100_lf0p2_min0p75` | 120 | 34 | 53 | 33 | 0.000966570367678254 |
| `repair5g1_agent_c100_b125_w075_d100_lf0p2_min1` | 120 | 33 | 54 | 33 | 0.0018673756666637861 |
| `repair5g1_agent_c125_b125_w075_d095_lf0p01_min0p5` | 120 | 28 | 58 | 34 | 0.0026448483836810192 |
| `repair5g1_agent_c125_b125_w075_d095_lf0p01_min0p75` | 120 | 27 | 57 | 35 | 0.0026678470652782456 |
| `repair5g1_agent_c125_b125_w075_d095_lf0p01_min1` | 120 | 27 | 56 | 36 | 0.0026912492325175284 |
| `repair5g1_agent_c125_b125_w075_d095_lf0p025_min0p5` | 120 | 31 | 55 | 34 | 0.0020028793384736752 |
| `repair5g1_agent_c125_b125_w075_d095_lf0p025_min0p75` | 120 | 30 | 57 | 32 | 0.0019683469360861983 |
| `repair5g1_agent_c125_b125_w075_d095_lf0p025_min1` | 120 | 31 | 57 | 31 | 0.001861789989620682 |
| `repair5g1_agent_c125_b125_w075_d095_lf0p05_min0p5` | 120 | 32 | 59 | 29 | 0.001742270410275861 |
| `repair5g1_agent_c125_b125_w075_d095_lf0p05_min0p75` | 120 | 30 | 60 | 29 | 0.0027608619190769208 |
| `repair5g1_agent_c125_b125_w075_d095_lf0p05_min1` | 120 | 31 | 60 | 28 | 0.00197585213702564 |
| `repair5g1_agent_c125_b125_w075_d095_lf0p1_min0p5` | 120 | 33 | 59 | 26 | -0.0013367351538728857 |
| `repair5g1_agent_c125_b125_w075_d095_lf0p1_min0p75` | 120 | 33 | 58 | 28 | -0.0005298976422820557 |
| `repair5g1_agent_c125_b125_w075_d095_lf0p1_min1` | 120 | 35 | 57 | 28 | -0.0013597823116982802 |
| `repair5g1_agent_c125_b125_w075_d095_lf0p2_min0p5` | 120 | 35 | 56 | 27 | -0.0007078445980689771 |
| `repair5g1_agent_c125_b125_w075_d095_lf0p2_min0p75` | 120 | 36 | 56 | 27 | -0.0007078445980689771 |
| `repair5g1_agent_c125_b125_w075_d095_lf0p2_min1` | 120 | 36 | 55 | 28 | -0.0007139997684869682 |
| `repair5g1_global_additive_lf0p01_min0p75` | 120 | 19 | 59 | 41 | 0.0034304781954648984 |
| `repair5g1_global_additive_lf0p025_min0p75` | 120 | 33 | 55 | 32 | 0.0020155540742905855 |
| `repair5g1_global_additive_lf0p05_min0p75` | 120 | 29 | 57 | 34 | 0.0020017532421912963 |
| `repair5g1_global_additive_lf0p1_min0p75` | 120 | 25 | 57 | 38 | 0.003273791646452167 |
| `repair5g1_global_c100_b100_w075_d095_lf0p01_min0p75` | 120 | 22 | 56 | 41 | 0.003985296067271924 |
| `repair5g1_global_c100_b100_w075_d095_lf0p025_min0p75` | 120 | 31 | 56 | 33 | 0.0005946309806724055 |
| `repair5g1_global_c100_b100_w075_d095_lf0p05_min0p75` | 120 | 29 | 58 | 33 | 0.0009477632963534427 |
| `repair5g1_global_c100_b100_w075_d095_lf0p1_min0p75` | 120 | 23 | 60 | 37 | 0.004111079998069556 |
| `repair5g1_global_c100_b125_w075_d100_lf0p01_min0p75` | 120 | 29 | 56 | 35 | 0.0020605745373275873 |
| `repair5g1_global_c100_b125_w075_d100_lf0p025_min0p75` | 120 | 27 | 56 | 37 | 0.002471614031991225 |
| `repair5g1_global_c100_b125_w075_d100_lf0p05_min0p75` | 120 | 30 | 55 | 35 | 0.0022631395815258517 |
| `repair5g1_global_c100_b125_w075_d100_lf0p1_min0p75` | 120 | 31 | 60 | 29 | 0.00037429227568964855 |
| `repair5g1_global_c125_b125_w075_d095_lf0p01_min0p75` | 120 | 34 | 53 | 33 | 0.0006379423421217305 |
| `repair5g1_global_c125_b125_w075_d095_lf0p025_min0p75` | 120 | 28 | 56 | 34 | 0.001531792761791302 |
| `repair5g1_global_c125_b125_w075_d095_lf0p05_min0p75` | 120 | 28 | 58 | 34 | 0.0008885652455258489 |
| `repair5g1_global_c125_b125_w075_d095_lf0p1_min0p75` | 120 | 28 | 63 | 29 | 0.0020414186410172303 |
| `repair5g1_random_static_diagnostic` | 120 | 29 | 54 | 37 | 0.001719045029763145 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p05_max0p25` | 120 | 27 | 54 | 39 | 0.0028609675180603367 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p05_max0p5` | 120 | 37 | 55 | 28 | 0.0009032956611965781 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p05_max0p75` | 120 | 37 | 54 | 29 | 0.0009110826927586175 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p1_max0p25` | 120 | 38 | 58 | 24 | -0.0011234881815344868 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p1_max0p5` | 120 | 41 | 49 | 30 | -0.0026021448838879422 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p1_max0p75` | 120 | 43 | 49 | 28 | -0.004360946869547013 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p2_max0p25` | 120 | 29 | 57 | 34 | 0.0007870065483589693 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p2_max0p5` | 120 | 52 | 53 | 15 | -0.0077079518753898416 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p2_max0p75` | 120 | 50 | 44 | 26 | -0.007929312204278265 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p35_max0p25` | 120 | 37 | 56 | 27 | -0.0009268661120431137 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p35_max0p5` | 120 | 48 | 48 | 24 | -0.00613575942311966 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p35_max0p75` | 120 | 63 | 40 | 17 | -0.013149905779432201 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p05_max0p25` | 120 | 35 | 58 | 27 | 0.00027866310941379114 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p05_max0p5` | 120 | 32 | 56 | 32 | 0.0009561530283846038 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p05_max0p75` | 120 | 32 | 55 | 33 | 0.00039484131190515995 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p1_max0p25` | 120 | 36 | 58 | 26 | -0.0017390998173675203 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p1_max0p5` | 120 | 45 | 51 | 24 | -0.0045738271352069 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p1_max0p75` | 120 | 43 | 45 | 32 | -0.0051169978255263295 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p2_max0p25` | 120 | 35 | 56 | 29 | -0.0009222363696239405 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p2_max0p5` | 120 | 52 | 46 | 22 | -0.008704894452051727 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p2_max0p75` | 120 | 57 | 42 | 21 | -0.010387837632398303 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p25` | 120 | 39 | 51 | 30 | -0.0004800171596724249 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p5` | 120 | 49 | 46 | 25 | -0.007922400645637168 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75` | 120 | 64 | 35 | 21 | -0.013736227771605257 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p05_max0p25` | 120 | 33 | 54 | 33 | -0.0002251170495555612 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p05_max0p5` | 120 | 40 | 55 | 25 | -0.0023666628169059884 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p05_max0p75` | 120 | 40 | 54 | 26 | -0.0023870650825689715 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p1_max0p25` | 120 | 36 | 56 | 28 | -0.001593697708551729 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p1_max0p5` | 120 | 43 | 53 | 24 | -0.007072366789991304 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p1_max0p75` | 120 | 48 | 46 | 26 | -0.0026863721548017307 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p25` | 120 | 34 | 57 | 29 | -0.0021444721513304435 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p5` | 120 | 52 | 46 | 22 | -0.004920278463801723 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p75` | 120 | 61 | 40 | 19 | -0.012989982687452996 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p25` | 120 | 37 | 54 | 29 | -0.0005991043379035194 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p5` | 120 | 49 | 51 | 20 | -0.005907960302170944 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75` | 120 | 67 | 37 | 16 | -0.014306860332393171 |
| `repair5g1_wait_additive_wp0p25_wn1` | 120 | 29 | 58 | 33 | 0.0017327857858717918 |
| `repair5g1_wait_additive_wp0p5_wn1` | 120 | 24 | 59 | 37 | 0.0032495307034655103 |
| `repair5g1_wait_additive_wp0p75_wn1p25` | 120 | 25 | 56 | 39 | 0.003708821208448274 |
| `repair5g1_wait_c100_b100_w075_d095_wp0p25_wn1` | 120 | 28 | 58 | 34 | 0.0016607087570341844 |
| `repair5g1_wait_c100_b100_w075_d095_wp0p5_wn1` | 120 | 28 | 56 | 36 | 0.0032562686798434685 |
| `repair5g1_wait_c100_b100_w075_d095_wp0p75_wn1p25` | 120 | 26 | 60 | 33 | 0.0018808572212649483 |
| `repair5g1_wait_c100_b125_w075_d100_wp0p25_wn1` | 120 | 28 | 61 | 31 | 0.0012351197163017144 |
| `repair5g1_wait_c100_b125_w075_d100_wp0p5_wn1` | 120 | 30 | 58 | 32 | 0.0008808565518793092 |
| `repair5g1_wait_c100_b125_w075_d100_wp0p75_wn1p25` | 120 | 23 | 58 | 39 | 0.003468704324327578 |
| `repair5g1_wait_c125_b125_w075_d095_wp0p25_wn1` | 120 | 27 | 58 | 35 | 0.0029042537746782563 |
| `repair5g1_wait_c125_b125_w075_d095_wp0p5_wn1` | 120 | 20 | 62 | 38 | 0.003334018441853435 |
| `repair5g1_wait_c125_b125_w075_d095_wp0p75_wn1p25` | 120 | 25 | 59 | 36 | 0.0014567050521525297 |
| `repair5g_dual_additive_parity` | 120 | 3 | 112 | 5 | 0.0006765652160000009 |
| `repair5g_dual_c_equiv_additive` | 120 | 3 | 116 | 1 | -0.00042539707350427265 |
| `repair5g_dual_c_equiv_c100_b100_w075_d090` | 120 | 27 | 63 | 30 | -0.00011977654297392132 |
| `repair5g_dual_c_equiv_c100_b100_w075_d095` | 120 | 26 | 71 | 23 | -0.0017208903811637957 |
| `repair5g_dual_c_equiv_c100_b100_w075_d100` | 120 | 27 | 65 | 26 | -0.0009970440280000115 |
| `repair5g_dual_c_equiv_c100_b100_w100_d090` | 120 | 27 | 66 | 27 | -0.0008183044900438648 |
| `repair5g_dual_c_equiv_c100_b125_w075_d100` | 120 | 31 | 65 | 24 | -0.0027456139927826157 |
| `repair5g_dual_c_equiv_c125_b125_w075_d095` | 120 | 36 | 62 | 22 | -0.002227996893353449 |
| `repair5g_random_dual_candidate_diagnostic` | 120 | 31 | 57 | 32 | 0.00047062366036521226 |
| `repair5g_shuffled_goal_progress_diagnostic` | 120 | 51 | 49 | 20 | -0.009592052687144071 |
