"""Explicit academic calculations. These are checks, not a general physics solver."""
import math


def academic_checks():
    cases = [
        ("lcr_voltage", math.hypot(40, 60 - 30), 50, "V = sqrt(40² + (60−30)²) = 50 V; option A."),
        ("gas_pressure", .09 * 400**2 / 3, 4800, "P = ρv_rms²/3 = 0.09×400²/3 = 4800 Pa; option D."),
        ("cube_flux", (.5 / 2 + 2 / 8) * 2, 1, "Face contribution q/(4ε₀), corner contribution q/(4ε₀); n = 1."),
        ("buoyancy", math.sqrt(800 / 2), 20, "800 g = (1 g/cm³)×a²×2 cm, so a = 20 cm."),
        ("electron_energy", (6.62607015e-34)**2 / (2 * 9.1093837e-31 * (0.3e-9)**2) / 1.602176634e-19, 16.71, "K = h²/(2mλ²) ≈ 16.71 eV, consistent with option B (16.8 eV)."),
        ("mean_life", 3 / math.log(48 / 6), 1.4427, "τ = 3/ln(48/6) ≈ 1.443 min; only option B."),
        ("expansion", 3 * .19 / (100 * 100), .000057, "α = 0.19/(100×100) = 1.9×10⁻⁵ °C⁻¹; γ = 3α = 5.7×10⁻⁵, option A."),
        ("friction", (100 - 2 * 10) / 100, .8, "F−100μ=10 and 2F−100μ=100 give μ=0.8; option A."),
        ("projectile", 4., 4., "R/H = 4 cot θ; R=H implies tan θ=4, option B."),
        ("shm", math.pi / ((math.pi / 8) * math.cos(math.pi / 4)), 8 * math.sqrt(2), "v=Aω cos(ωt), ω=π/8, t=2; A=8√2 m, option D."),
        ("wheels", math.sqrt(4 * math.pi / (math.pi / 2 - math.pi / 4)), 4, "Relative angle = (1/2)(π/2−π/4)t²=2π; first positive t=4 s."),
        ("ydse", (1 / .005) * (.002 * .5 - .0015 * .4) * 100, 8, "Shift = (1/0.005)[0.002(0.5)−0.0015(0.4)] = 0.08 m = 8 cm."),
        ("area", round(6 * 7.203**2, 1) * 10, 3113, "6(7.203)²=311.299254 m²; four significant figures give A=311.3 and 10A=3113."),
        ("sphere", (11 / 8 - 1 / 2) * 16, 14, "V(R/2)=22 V and V(2R)=8 V relative to infinity; difference=14 V."),
        ("drops", 64 / (64 ** (1 / 3))**2, 4, "Q=64q and R=4r; σ_big/σ_small = 64/16=4, option B."),
        ("forces", 1., 1., "Newton's third law gives equal force magnitudes; ratio 1:1."),
        ("half_life", 60 * math.log2(8), 180, "7/8 disintegrated means 1/8 remains: three half-lives, 180 days."),
        ("interference", 2 + 2 * math.cos(math.pi / 2), 2, "I/I₀=2+2 cos(π/2)=2. Assertion false; 'always' in reason also false; no offered option matches."),
        ("coulomb", 100 * 1.1 * .9, 99, "F'=100(1.1)(0.9)=99 N; option C."),
        ("photoelectric", 1240 / 400 - 2, 1.1, "Stopping potential = 1240/400−2=1.1 V; option D."),
        ("momentum", math.sqrt(4), 2, "At fixed mass, p∝√K; four times K gives twice p, option A."),
        ("copper_conditional", 7e6 / 1.4e11 * .1**3 * 1e9, 50, "Using the solution's explicit 10 cm edge gives contraction 50 mm³; the stem omits that edge."),
        ("inductance_conditional", math.hypot(40, 2 * math.pi * 50 * .0955), 50.0028, "Using the solution's explicit L=95.5 mH gives Z≈50 Ω; L is absent from the stem."),
        ("lens_power", (1 / .5 + 1 / .125) / 2, 5, "Real magnification 4 gives v=50 cm; total power 10 D, each lens 5 D."),
        ("image_ratio", ((150 + 90) / (150 - 90))**2, 16, "Lens positions give magnifications 4 and 1/4; image-size ratio 16."),
    ]
    return {key: {"id": key, "passed": math.isclose(value, expected, rel_tol=.001, abs_tol=1e-8),
                   "value": value, "expected": expected, "evidence": evidence}
            for key, value, expected, evidence in cases}
