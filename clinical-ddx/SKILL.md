---
name: clinical-ddx
description: >
  Clinical differential diagnosis and investigation recommendation skill. Use this skill
  whenever a user presents a clinical case, patient symptoms, signs, or lab results and
  wants help with differential diagnosis, investigation planning, or clinical reasoning.
  Trigger on phrases like "what could this be", "differential for", "work up for",
  "investigations for", "patient presenting with", or any case presentation with
  symptoms/signs/vitals. Also trigger when the user pastes clinical notes, ED triage
  summaries, or asks "what's your DDx". Always use this skill for clinical reasoning
  tasks — even partial presentations like "45F with chest pain and diaphoresis". Trigger
  even for single-symptom queries like "dyspnoea approach" or "cause of haematuria".
  When in doubt, use this skill.
---

# Clinical DDx & Investigation Skill

A systematic clinical reasoning skill that generates ranked differential diagnoses and targeted investigation plans by matching patient data against clinical algorithms, evidence-based guidelines, and medical literature.

## Workflow Overview

1. **Parse** the clinical input → extract structured data
2. **Select** the appropriate diagnostic approach algorithm
3. **Generate** a ranked differential using systematic matching
4. **Recommend** investigations with priority levels
5. **Summarize** reasoning; request more data if confidence is low

## Step 1: Parse Clinical Input

Extract and organize available data into this structure:

```
Demographics        : age, sex, relevant background
Presenting complaint: chief symptom(s) + duration + onset (sudden/gradual)
HPI                 : character, severity, radiation, associations,
                      relieving/aggravating factors, time course
PMH                 : relevant conditions, surgeries, hospitalizations
Medications         : current meds + allergies
Social Hx           : smoking, alcohol, occupation, travel, sexual Hx if relevant
Family Hx           : if relevant
ROS                 : pertinent positives AND negatives
Examination         : vitals, relevant positive and negative findings
Investigations      : labs, imaging, ECG, etc. already available
```

If critical fields are missing, note them and proceed with available data. Request missing data at the end if overall confidence is insufficient (see Step 5).

## Step 2: Select Diagnostic Approach Algorithm

Map the chief complaint to a standard approach algorithm:

| Chief Complaint | Algorithm / Framework |
|:---|:---|
| Dyspnoea | Cardiac vs. Pulmonary vs. Other (HEART-LUNGS) |
| Chest pain | ACS / PE / Dissection / Other (life-threats first) |
| Syncope | Cardiac vs. Neurocardiogenic vs. Neurological |
| Altered consciousness | AEIOU-TIPS |
| Cognitive decline | Reversible (DEMENTIA mnemonic) vs. irreversible |
| Acute abdomen | Quadrant-based + hollow vs. solid organ |
| Jaundice | Pre-hepatic / Hepatic / Post-hepatic |
| Haematuria | Upper vs. lower tract; glomerular vs. non-glomerular |
| Anaemia | Kinetic (production/destruction/loss) framework |
| Shock | Distributive / Cardiogenic / Obstructive / Hypovolaemic |
| Hyponatraemia | Volume status → urine Na/osmolality |
| Acid-base disorder | Stepwise: pH → primary → compensation → delta-delta |

If no standard algorithm is immediately applicable, use VINDICATE or SOCRATES as a fallback structure.

Search online for the latest version of the algorithm if web search is available.

## Step 3: Generate Ranked Differential

Apply the selected algorithm to the patient's data.

### Ranking Schema

Rank by **likelihood given this specific presentation**, not population base rate alone.

For each diagnosis assess:
- Feature match score: how many of the patient's features does this diagnosis explain?
- Red flags: does this diagnosis explain any life-threatening features?
- Can't-miss flag: should this be ruled out even if unlikely?

### Output format

#### Differential Diagnosis

| Rank | Diagnosis | Likelihood | Key supporting features | Key against |
|------|-----------|------------|------------------------|-------------|
| 1 | ... | High | ... | ... |
| 2 | ... | Moderate | ... | ... |
| 3 | ... | Moderate | ... | ... |
| 4 | ... | Low | ... | ... |
| — | ⚠️ Must exclude | — | ... | ... |

Always include a "Must exclude" row for diagnoses that are low probability but immediately life-threatening if missed (e.g. aortic dissection, PE, meningitis, ectopic pregnancy).

### Evidence-Matching

Where clinical scoring tools are applicable, compute or estimate the score:

- Wells score (PE, DVT)
- HEART score (ACS)
- CURB-65 (pneumonia)
- qSOFA / SOFA (sepsis)
- Glasgow-Blatchford (GI bleed)
- NIHSS (stroke)
- Child-Pugh / MELD (liver)
- KDIGO staging (AKI/CKD)

If web search is available, use PubMed or UpToDate to verify feature prevalence for top diagnoses.

## Step 3b: Partial Match / Rare Case Escalation

**Trigger this sub-step if:**
- No single diagnosis cleanly explains all major features
- The user flags the presentation as atypical or refractory
- Common diagnoses have been excluded and no clear alternative fits
- The symptom combination is unusual or rare

### Rare Disease Search Protocol

1. **PubMed case report search** (if web search available):
   - Query: "[symptom 1] [symptom 2] [symptom 3] rare diagnosis case report"
   - Query: "[symptom cluster] atypical presentation"

2. **Rare disease databases** (if accessible):
   - Orphanet: search by symptom phenotype
   - OMIM: for genetic/inherited conditions
   - NORD: for rare disease descriptions

3. **Atypical presentations of common diseases**:
   - Search: "[common diagnosis] atypical presentation"
   - Example: atypical PE, atypical ACS in women/diabetics, masked TB

### Output Format for Rare/Atypical Cases

```
⚠️ Atypical / Rare Consideration

The following are atypical for common diagnoses OR suggest rare conditions
that could explain the full feature set:

- [Rare condition]: [mechanism linking features] — [source/reference]
- [Atypical presentation of X]: [which features match / which don't]

Suggested further investigations to differentiate: [targeted tests]
```

### Fallback if Web Search Unavailable

Note explicitly that web search is unavailable, then:
- List rare conditions from training knowledge that match the symptom cluster
- Recommend manual PubMed/Orphanet search with the specific symptom combination
- Suggest specialist referral: rheumatology, immunology, genetics, or infectious disease

## Step 4: Recommend Investigations

### Tier 1 — Immediate (bedside / stat, results within 1 hour)
- Point-of-care tests, ECG, CXR, rapid blood glucose
- Stat bloods: FBC, UE, LFT, troponin, D-dimer, blood gas, lactate
- Bedside echo / FAST scan if trained

### Tier 2 — Urgent (results within 4–24 hours)
- CT (with/without contrast; specify modality and indication)
- Cultures (blood, urine, sputum — before antibiotics)
- Specialist labs: TFTs, cortisol, coagulation, specific antibodies

### Tier 3 — Targeted / Elective
- MRI, nuclear medicine, biopsy, endoscopy
- Autoimmune panels, genetic testing, rare disease workup
- Specialist-directed investigations

### Format

**Tier 1 — Immediate:**
- [Test]: [rationale — what it rules in/out]

**Tier 2 — Urgent:**
- [Test]: [rationale]

**Tier 3 — Targeted (if Tier 1/2 non-diagnostic):**
- [Test]: [rationale]

For each investigation, state what a positive or negative result means for the differential.

## Step 5: Confidence Check & Data Request

**High confidence** — ≥2 supporting features per top diagnosis, algorithm cleanly applied, no contradictory findings → proceed without requesting more data.

**Moderate confidence** — some key fields missing but differential is still useful → note gaps, proceed, flag what additional data would most change the ranking.

**Low confidence** — insufficient data for reliable ranking → request specific missing fields before finalizing:

```
⚠️ Additional data needed to finalize the differential:
1. [Most important missing field] — this would [raise/lower] [diagnosis] significantly
2. [Second most important] — this would help differentiate [A] from [B]

Please provide any of the above and I will update the differential.
```

## Output Summary Format

End every response with:

```
---
### Clinical Summary
**Most likely:** [Top diagnosis] — [1-sentence rationale]
**Must exclude:** [Can't-miss diagnosis] — [key investigation to rule out]
**Next step:** [Single highest-priority action]
**Request more data if:** [Specific trigger for re-evaluation]
---
```

## Style Guidelines

- Use clinical shorthand consistent with the user's communication style
- Be direct — avoid hedging that reduces clinical utility
- Flag life-threatening diagnoses prominently (⚠️ prefix)
- For Thai clinical context: note relevant local epidemiology where applicable (e.g. higher melioidosis prevalence, endemic TB, tropical infections)
- Do not provide definitive diagnoses — frame as ranked possibilities for clinical judgment
- Always recommend the treating clinician confirm findings and apply local protocols
