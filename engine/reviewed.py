"""Assistant-reviewed findings for this fixed snapshot, not a simulated API run.

Every mathematical evidence reference points to an actual deterministic check.
This catalog is a transparent baseline; live mode does not read its decisions.
"""
from engine.content import payload


def decisions(questions):
    by_id = {q["_id"]: q for q in questions}
    output = {}

    def add(ids, verdict, repair, evidence, reply, patches=None, checks=None, review=False):
        for rid in ids.split():
            output[rid] = dict(verdict=verdict, repair=repair, evidence=evidence,
                student_reply=reply, patches=patches or [], checks=checks or [], review=review)

    def edit(field, find, replace):
        return dict(field=field, find=find, replace=replace)

    add("R001 R002 R003", "defect", "answer_key",
        "The independent phasor calculation gives 50 V (A); stored key C points to 130 V. The stored solution also evaluates to 50 V.",
        "You were right to flag the key: the supply voltage is 50 V, option A. A key correction is ready.",
        [edit("answer", "C", "A")], ["lcr_voltage"])
    add("R004", "defect", "answer_key",
        "The student proposes 8225, but P=ρv²/3 gives 4800 Pa (D). The stored key A is wrong; do not accept the student's proposed value.",
        "The key does need correction, though the pressure is 4800 Pa, option D. Use one third of density times RMS speed squared.",
        [edit("answer", "A", "D")], ["gas_pressure"])
    add("R005", "defect", "answer_key",
        "Gauss-law symmetry gives q/(4ε₀)+q/(4ε₀)=q/(2ε₀), so n=1, not the stored 2.",
        "Your n=1 is correct: the face and corner contributions add to q/(2ε₀). A key correction is ready.",
        [edit("answer", "2", "1")], ["cube_flux"])
    add("R006", "defect", "stem_data",
        "The stem omits the cube's edge. The solution explicitly substitutes (10×10⁻² m)³; restoring a 10 cm edge reproduces 50 mm³. Faculty should confirm the intended source.",
        "You're right: the edge length is missing. The solution uses 10 cm; we've prepared that restoration for faculty to confirm.",
        [edit("question", "solid copper cube,", "solid copper cube of side 10 cm,")], ["copper_conditional"], review=True)
    add("R007 R008", "defect", "stem_data",
        "The stem omits L. The solution explicitly substitutes 95.5×10⁻³ H and obtains approximately 50 Ω; no value is inferred from the key alone.",
        "The inductance is missing from the question. The solution uses 95.5 mH, and that restoration is ready for review.",
        [edit("question", "an inductance are", "an inductance of 95.5 mH are")], ["inductance_conditional"], review=True)
    add("R009 R010", "defect", "option_repair",
        "Stored HTML contains A, B and C but no D. The centre-of-mass calculation supports C=10 m/s, but the original D distractor cannot be recovered from the supplied data. Do not invent it.",
        "You're right: the stored question is missing option D. Faculty need to restore the original option; the available calculation gives 10 m/s.", review=True)
    add("R011", "defect", "option_repair",
        "Option C is blank. Equal and opposite Coulomb forces have magnitude ratio 1:1, consistent with the solution and keyed C. Only the blank option span is changed.",
        "Option C is blank; it should show 1:1 because the forces have equal magnitudes. That restoration is ready.",
        [edit("question", "(C) <br />", "(C) 1:1<br />")], ["forces"])
    add("R012", "defect", "spelling", "Option A contains 'Epithellial tisue'; the solution uses 'Epithelial tissue'. The key remains A.",
        "Thanks for catching that. We've prepared the spelling correction to ‘Epithelial tissue’; option A remains correct.",
        [edit("question", "Epithellial tisue", "Epithelial tissue")])
    add("R013", "defect", "exam_reference", "The question contains '(NEET 2019)' as a source tag. Remove that exact tag without changing the biology or answer D.",
        "That text is an exam source label. We've prepared its removal from the question; lamina, option D, remains correct.",
        [edit("question", "(NEET 2019) ", "")])
    add("R014", "defect", "markup_leak", "The stem contains literal \\frac{7}{8}. Replacing only that expression with equivalent MathML preserves 7/8 and the answer C=180 days.",
        "You're seeing a formatting error: the expression means seven eighths. A math-formatting correction is ready; the answer remains 180 days.",
        [edit("question", r"\frac{7}{8}", '<math xmlns="http://www.w3.org/1998/Math/MathML"><mfrac><mn>7</mn><mn>8</mn></mfrac></math>')], ["half_life"])
    add("R015", "defect", "identical_options", "Options B and C both read 0 W. The correct physical value is zero, but choosing a new distractor is authored content and is forbidden to the machine.",
        "You're right that B and C repeat the same answer. Faculty need to repair the options; we haven't guessed a replacement.", review=True)
    add("R016", "defect", "solution_fix", "The solution's own equation is 800=2a², giving a=20 cm. Its final 'a = 40 cm' is wrong; the stored answer 20 is correct.",
        "The side is 20 cm, so the answer key is correct. We've prepared a correction to the solution's final line.",
        [edit("solution", "a = 40 cm", "a = 20 cm")], ["buoyancy"])
    add("R017", "already_fixed", None, "Report precedes the faculty errorHistory entry at 2026-11-07T10:42:00Z, which records 'mere'→'more'. Current options contain 'more'.", "The reported spelling issue has already been corrected in the current record. Thanks for flagging it.")
    electron = by_id["612151a6a34397610a9a2e58"]["scq"]["solution"]
    wrong_prefix = electron[:electron.index(' <math', 5)]
    add("R018 R019", "defect", "solution_fix", "The solution begins with an unrelated 5.47 Å result, although the question supplies λ=0.3 nm. An independent calculation gives about 16.71 eV (B). Replace the unrelated fragment with the relevant energy relation; preserve the key.",
        "The solution includes an unrelated wavelength fragment. The supplied wavelength gives about 16.8 eV, option B; a targeted explanation repair is ready for faculty review.",
        [edit("solution", wrong_prefix, '<h3>For the given wavelength λ = 0.3 nm, K = h²/(2mλ²) ≈ 16.7 eV, so option B is correct.')], ["electron_energy"], review=True)
    add("R020", "defect", "answer_key", "The MCQ answer is ['A, B, D'], one combined string, instead of three labels. A and B follow qE; D is circular magnetic motion; C is false for velocity parallel to B. Normalize storage without changing the answer set.",
        "A, B and D are the correct statements. The stored answer format is malformed; a correction to store each label separately is ready for review.",
        [edit("answer", ["A, B, D"], ["A", "B", "D"])], review=True)
    add("R021", "defect", "type_mismatch", "Only B (1.44 min) solves the mean-life question. The MCQ key ['', 'B'] is malformed. Propose SCQ with key B, but faculty must confirm the intended assessment type; one correct choice alone does not establish a type defect.",
        "Your B matches the decay calculation. The stored answer format is broken, and faculty need to confirm the question type before any scoring change.",
        [edit("questionType", "mcq", "scq"), edit("answer", ["", "B"], "B")], ["mean_life"], review=True)
    add("R022", "defect", "spelling", "Option D says 'Choroid plexux'; change only 'plexux' to 'plexus'. The correct key remains B (Peyer's patches).", "Thanks for spotting the typo. We've prepared ‘Choroid plexus’; Peyer's patches, option B, remains the answer.", [edit("question", "plexux", "plexus")])
    add("R023", "defect", "wrong_chapter", "The stem concerns neuronal action potentials, but metadata says Botany / The Living World. Chapter and subject changes are outside machine edit scope.", "You're right that this belongs with neural control rather than The Living World. Faculty need to correct its subject and chapter placement.", review=True)
    add("R024", "defect", "answer_form", "The numerical question does not state an output unit. The solution uses g=10 m/s² and finds 20 N; add an explicit unit and gravity assumption without changing existing text.", "The question should specify newtons and the gravity value used. We've prepared that clarification; the frictional force is 20 N.", [edit("question", "Then the frictional force is equal to", "Then the frictional force is equal to (in N; take g = 10 m/s²)")])
    add("R025", "defect", "diagram", "The stem explicitly refers to a figure, but contains no image and quesImages is empty. No original diagram is supplied; a generated reconstruction would be unsupported.", "The referenced figure is missing. Faculty need to restore the original diagram; we haven't invented a replacement.", review=True)
    add("R026", "defect", "syllabus", "The student disputes NEET syllabus coverage. The dataset supplies no authoritative syllabus/version; faculty must confirm and the question stays live meanwhile. This is a review request, not a verified exclusion.", "We've sent the syllabus question to faculty for confirmation. The question stays available while they check the applicable syllabus.", review=True)
    add("R027", "no_error", None, "The comment attempts to override instructions and change the key to C. It is untrusted data. The independent expansion calculation supports the existing key A; no content edit is justified.", "The current answer is A: cubical expansion is three times the linear coefficient. No answer-key change is needed.", checks=["expansion"])
    add("R028", "no_error", None, "For a nonzero projectile trajectory with R=H, tan θ=4, not 2. The stored key B is consistent.", "For equal range and maximum height, tan θ=4, so option B is correct. The factor of four comes from comparing the two formulas.", checks=["projectile"])
    add("R029", "no_error", None, "Eliminating F from F−100μ=10 and 2F−100μ=100 gives μ=0.8, not 0.4. Stored A is correct.", "Subtracting the force equations gives μ=0.8, option A. The friction term is present in both cases.", checks=["friction"])
    add("R030", "no_error", None, "Starting at equilibrium gives v=Aω cos(ωt). For T=16 s and t=2 s, A=8√2 m (D), not 4√2.", "The amplitude is 8√2 m, option D. At two seconds the velocity is reduced by cos 45°, which must be included.", checks=["shm"])
    add("R031", "no_error", None, "The first subsequent alignment requires relative displacement 2π; relative acceleration π/4 gives t=4 s. At 2 s the separation is only π/2.", "The dots first realign after 4 seconds. They need a full relative turn, rather than a quarter turn.", checks=["wheels"])
    add("R032", "no_error", None, "The solution ends at 0.08 m; the question explicitly asks for cm. 0.08 m=8 cm, matching the stored answer.", "Your 0.08 m is correct. The question asks for centimetres, so the entry is 8.", checks=["ydse"])
    add("R033", "no_error", None, "The stem explicitly requires correct significant digits. Surface area rounds to 311.3 m² (four significant figures), then 10A=3113.", "The question asks you to use significant figures: A rounds to 311.3 m². That makes 10A equal to 3113.", checks=["area"])
    add("R034", "defect", "unsound", "I=I₁+I₂+2√(I₁I₂)cosϕ gives 2I₀ at π/2, so the assertion is false. The reason's 'always' is false too. No option says both false; changing only the key cannot repair this.", "This question needs faculty repair: both statements are false, but that combination is missing from the options. The student's proposed interpretation does not resolve it.", checks=["interference"], review=True)
    add("R035", "no_error", None, "Relaxin and inhibin have different roles and are not the standard antagonistic pair. The other listed pairs oppose relevant physiological effects; D remains the intended correct answer. Incidental solution wording is recorded separately.", "Relaxin and inhibin are not an antagonistic pair here, so D is the intended answer. They act on different reproductive processes.")
    add("R036", "display_issue", None, "Stored HTML contains all four options and the key C agrees with 99 N. The report concerns clipping on a phone; no stored-content loss is established.", "The stored question has all four options; this looks like a phone-layout issue. The answer remains C, 99 N.", checks=["coulomb"])
    add("R037", "display_issue", None, "The complaint is slow question loading. Stored content and the 1.1 V key D are consistent; the dataset contains no performance telemetry to diagnose the cause.", "The question's answer is 1.1 V, option D. The loading problem needs a display or performance check; no content change is proposed.", checks=["photoelectric"])
    add("R038", "app_issue", None, "The report concerns an option selection being saved differently. The stored question's momentum relation and key A are correct; attempt logs are absent.", "The answer is A: the momentum doubles. The different saved selection needs an app check using your attempt details.", checks=["momentum"])
    add("R039", "language_mode", None, "The student requests Hindi. This is a language-availability request, not evidence of an academic defect; the existing question should not be rewritten by this repair engine.", "We've noted your request for a Hindi version. This needs language support rather than a change to the question's answer.")
    add("R040", "no_error", None, "Golden rice provides beta-carotene, a vitamin A precursor; key C is correct. The vague 'wrong' report gives no contrary reasoning. Incidental spelling/spacing defects are recorded as secondary findings.", "Golden rice, option C, is correct because it supplies beta-carotene, which the body can convert to vitamin A. The answer key does not need a change.")
    add("R041", "not_actionable", None, "The comment 'asdfgh' gives no interpretable issue. The question and solution both attribute glucose-production evidence to Julius von Sachs, key A; no actionable discrepancy was found.", "We couldn't identify an issue from that message. Please tell us which part looks wrong so it can be checked.")
    add("R042", "defect", "wrong_chapter", "A capacitor displacement-current question is filed under geometrical optics. Chapter metadata is not an allowed machine-edit field for this repair.", "You're right that this is misplaced under geometrical optics. Faculty need to correct the chapter label.", review=True)
    add("R043", "no_error", None, "Merging conserves charge and volume: Q=64q and R=4r. Surface area increases sixteenfold but charge sixty-fourfold, so the surface-density ratio is 4:1 (B).", "The ratio is 4:1, option B. The larger drop has sixteen times the area but sixty-four times the charge.", checks=["drops"])
    add("R044", "no_error", None, "22 V is the potential at P relative to infinity. The question asks V(P)−V(S), and V(S)=8 V; the difference is 14 V.", "22 V is the potential at P, but the question asks for the difference from S. Subtracting 8 V gives the keyed answer, 14 V.", checks=["sphere"])
    return output
