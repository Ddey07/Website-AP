---
title: Research
date: 2026-09-29
type: landing

design:
  spacing: "2rem"

sections:
  - block: markdown-wide
    content:
      title: Research
      text: |
        Modern studies of health no longer observe people once. Smartwatches record movement and heart rate every second, smartphones ask about mood and sleep several times a day, glucose monitors and EEG headbands stream physiology, and location tracking connects all of this to weather, light, and greenspace. The result is **intensive, multilevel, multimodal, longitudinal data collected across space and time** — and it rarely fits the assumptions of classical models.

        The CADENCE Lab — **Contextual Analytics of Digital & Environmental data for Neurobehavioral, Circadian & Emotional health** — builds the statistical theory and methods needed to learn from these data. Our unifying framework is the **multivariate stochastic process**: we treat each person's streams of measurements as coupled random processes over time (and space), and develop models that respect their mixed scales (continuous, truncated, ordinal, binary), their dependence structure, and the context in which they were measured. We then use these tools to understand how **mental health, sleep, physical activity, circadian rhythms, and the environment** interact and evolve, and to move toward personalized prediction and early intervention.

  - block: features
    content:
      title: Three pillars
      items:
        - name: Theory & Methods
          icon: variable
          description: |
            Multivariate stochastic processes in space and time; semiparametric Gaussian copulas for mixed-type data; multivariate functional PCA for continuous, truncated, ordinal and binary functional data; dynamic structural equation models; graphical models and graph-constrained analysis; scalable multivariate spatial processes (graphical Gaussian processes, bigraphical Matérn–Whittle processes).
        - name: Digital Health Technologies
          icon: device-phone-mobile
          description: |
            Objective streams from wearables — physical activity ⌚, heart rate ❤️, headband EEG 🎧, continuous glucose monitoring 🩸 — combined with subjective ecological momentary assessment 📱 of mood, energy, sleep and stress. We develop digital phenotypes for mood disorders and methods for real-time, intensive longitudinal mHealth data.
        - name: Environment & Context
          icon: map-pin
          description: |
            Linking health dynamics to where people are: outdoor temperature, daylight, greenspace and the built environment 📍, through location tracking and spatial statistics. Applications range from mood and sleep in mood-disorder subtypes to youth physical activity across social and physical contexts.

  - block: markdown-wide
    content:
      title: Studies & consortia we work with
      text: |
        - **mMARCH — Motor Activity Research Consortium for Health.** An international NIMH-led consortium (PI: Kathleen R. Merikangas, NIMH Intramural Research Program; methodological lead: Vadim Zipunnikov, Johns Hopkins) that harmonizes wrist-accelerometry and ecological momentary assessment data across sites to study motor activity, sleep, circadian rhythms and mood disorders. Debangan Dey served as lead analyst for mMARCH during his postdoctoral fellowship at NIMH (2022–2025), and the lab continues to develop methods and analyses for the consortium — including work published in *JAMA Psychiatry* (2024), *Neurology* (2024), and the *Journal of Affective Disorders* (2025). [R package: mMARCH.AC](https://cran.r-project.org/web/packages/mMARCH.AC/index.html)
        - **SPACES — Social and Physical Activity Contexts in the Environment in Summer.** An NHLBI-funded study (K01HL169818; PI: Tyler Prochnow, Texas A&M School of Public Health) in which youth entering grades 7–9 in Bryan and College Station wear an accelerometer for seven days, complete EMA prompts six times daily, and are GPS-tracked, alongside social-network and mental-health surveys, to understand how the built environment, social networks and physical activity shape each other over the summer. We collaborate on the statistical modeling of these intensive, spatially-referenced data. [Study page](https://www.tprochnow.com/project/summerpa/) · [Protocol (JMIR Res Protoc, 2025)](https://www.researchprotocols.org/2025/1/e68667)
        - **REACH on Curious — Real-time Ecological Assessment of the Context of mental and physical Health.** A large-scale smartphone-based study of daily mental and physical health in context, led by the NIMH Genetic Epidemiology Research Branch with the Child Mind Institute. [Preprint (2025)](https://doi.org/10.21203/rs.3.rs-8171682/v1)

  - block: markdown-wide
    content:
      title: Funding & support
      text: |
        - **[NIH Director's Challenge Innovation Award (2026)](https://oir.nih.gov/sourcebook/awards-fellowships-grant-opportunities/directors-challenge-innovation-award-program/2026-directors-challenge-awards#2026-directors-merikangas)** — *Biologic Rhythms and Environmental Contexts in Human Health: Integrating Epidemiology and Circadian Science*. PI: Kathleen Merikangas (NIMH), in collaboration with NIDDK, NHLBI, NIAAA, NIA, NHGRI, Northwestern University, Nathan Kline Institute, Johns Hopkins, U Colorado, Texas A&M, and UT Southwestern. The project expands the NIH Clinical Center's *Rhythms and Blues* study, combining population research with wearable technology, metabolic measurements and genetics to follow 24-hour rhythms over days and seasons. Debangan Dey (Texas A&M, Consultant) will oversee development of data management and analytic strategies for multilevel data, integrating intensive individual-level data with macro environmental factors.
---
